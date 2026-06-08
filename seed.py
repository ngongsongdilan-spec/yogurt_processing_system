"""
Seed script for yogurt database.
Populates all 26 tables with realistic data for a yogurt processing plant.
Also adds audit_log table + trigger for automatic change tracking.
"""

import os, psycopg2

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'dbname=yogurt user=postgres password=Mypassword@2 host=localhost port=5432'))
conn.autocommit = True
cur = conn.cursor()

# ============================================================
# STEP 1: Create audit_log table and trigger
# ============================================================
cur.execute("""
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id    SERIAL PRIMARY KEY,
    table_name  VARCHAR(100) NOT NULL,
    operation   VARCHAR(10) NOT NULL,
    record_id   INTEGER NOT NULL,
    old_data    JSONB,
    new_data    JSONB,
    changed_by  VARCHAR(100) NOT NULL DEFAULT 'system',
    changed_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_table   ON audit_log (table_name);
CREATE INDEX IF NOT EXISTS idx_audit_time    ON audit_log (changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_op      ON audit_log (operation);
""")

# Create the generic audit trigger function (COALESCE handles missing app.username setting)
cur.execute("""
CREATE OR REPLACE FUNCTION fn_audit_trigger()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $afunc$
DECLARE
    _old_data JSONB;
    _new_data JSONB;
    _record_id INTEGER;
    _username VARCHAR(100);
    _pk_col VARCHAR(100);
BEGIN
    _username := COALESCE(NULLIF(current_setting('app.username', true), ''), 'system');

    SELECT a.attname INTO _pk_col
    FROM pg_index i
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
    WHERE i.indrelid = TG_RELID AND i.indisprimary
    LIMIT 1;

    IF _pk_col IS NULL THEN _pk_col := 'id'; END IF;

    IF TG_OP = 'INSERT' THEN
        EXECUTE format('SELECT ($1.%I)::int', _pk_col) INTO _record_id USING NEW;
        _new_data := to_jsonb(NEW);
        INSERT INTO audit_log (table_name, operation, record_id, new_data, changed_by)
        VALUES (TG_TABLE_NAME, 'INSERT', _record_id, _new_data, _username);

    ELSIF TG_OP = 'UPDATE' THEN
        EXECUTE format('SELECT ($1.%I)::int', _pk_col) INTO _record_id USING OLD;
        _old_data := to_jsonb(OLD);
        _new_data := to_jsonb(NEW);
        INSERT INTO audit_log (table_name, operation, record_id, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, 'UPDATE', _record_id, _old_data, _new_data, _username);

    ELSIF TG_OP = 'DELETE' THEN
        EXECUTE format('SELECT ($1.%I)::int', _pk_col) INTO _record_id USING OLD;
        _old_data := to_jsonb(OLD);
        INSERT INTO audit_log (table_name, operation, record_id, old_data, changed_by)
        VALUES (TG_TABLE_NAME, 'DELETE', _record_id, _old_data, _username);
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$afunc$;
""")

# Attach audit triggers to key tables
for tbl in ['user_account', 'production_batch', 'quality_control', 'inventory',
            'product_inventory', 'stock_transaction', 'purchase_order', 'sales_order']:
    cur.execute(f"""
        DROP TRIGGER IF EXISTS trg_audit_{tbl} ON {tbl};
        CREATE TRIGGER trg_audit_{tbl}
        AFTER INSERT OR UPDATE OR DELETE ON {tbl}
        FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();
    """)

# ============================================================
# STEP 2: Seed reference tables
# ============================================================

# --- role ---
cur.execute("""
INSERT INTO role (role_id, role_name) VALUES
(1, 'admin'), (2, 'manager'), (3, 'operator'), (4, 'inspector'), (5, 'viewer')
ON CONFLICT (role_id) DO NOTHING;
""")

# --- department ---
cur.execute("""
INSERT INTO department (department_id, department_name) VALUES
(1, 'Production'), (2, 'Quality Assurance'), (3, 'Warehouse'),
(4, 'Maintenance'), (5, 'Administration'), (6, 'Sales')
ON CONFLICT (department_id) DO NOTHING;
""")

# --- unit_of_measure ---
cur.execute("""
INSERT INTO unit_of_measure (uom_id, uom_code, uom_name) VALUES
(1, 'L',   'Liters'),
(2, 'KG',  'Kilograms'),
(3, 'G',   'Grams'),
(4, 'ML',  'Milliliters'),
(5, 'UNT', 'Units'),
(6, 'PCS', 'Pieces'),
(7, 'BOX', 'Boxes'),
(8, 'PL',  'Pallets'),
(9, 'T',   'Tonnes'),
(10,'BAG', 'Bags')
ON CONFLICT (uom_id) DO NOTHING;
""")

# --- employee (depends on department) ---
cur.execute("""
INSERT INTO employee (employee_id, employee_name, department_id) VALUES
(1, 'Alex Rivera',   1), (2, 'Maria Chen',   2), (3, 'James Okafor', 3),
(4, 'Priya Sharma',  4), (5, 'David Kim',    5), (6, 'Sarah Jones',  6),
(7, 'Carlos Mendez', 1), (8, 'Aisha Patel',  2), (9, 'Tom Mueller',  3)
ON CONFLICT (employee_id) DO NOTHING;
""")

# --- user_account (depends on employee, role) ---
cur.execute("""
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname='user_account_user_id_seq') THEN CREATE SEQUENCE user_account_user_id_seq; END IF; END $$;
SELECT setval('user_account_user_id_seq', 10, true);
INSERT INTO user_account (user_id, username, password, employee_id, role_id, is_active) VALUES
(1, 'admin',    'admin123',   5, 1, true),
(2, 'alex.r',   'pass123',   1, 3, true),
(3, 'maria.c',  'pass123',   2, 4, true),
(4, 'james.o',  'pass123',   3, 5, true),
(5, 'priya.s',  'pass123',   4, 2, true),
(6, 'david.k',  'pass123',   5, 2, true),
(7, 'sarah.j',  'pass123',   6, 5, true),
(8, 'carlos.m', 'pass123',   7, 3, true),
(9, 'aisha.p',  'pass123',   8, 4, true)
ON CONFLICT (user_id) DO NOTHING;
""")

# --- supplier ---
cur.execute("""
INSERT INTO supplier (supplier_id, supplier_name, supplier_contact, phone, email) VALUES
(1, 'DairyFresh Co.',    'John Dairy',     '555-0101', 'orders@dairyfresh.com'),
(2, 'CultureLab Inc.',   'Dr. Ferment',    '555-0102', 'info@culturelab.com'),
(3, 'PacKing Supplies',  'Bob Boxer',      '555-0103', 'sales@pac king.com'),
(4, 'Stabilizers R Us',  'Gina Gel',       '555-0104', 'contact@stabilizers.com'),
(5, 'FlavorMax Ltd.',    'Cherry Sweet',   '555-0105', 'orders@flavormax.com')
ON CONFLICT (supplier_id) DO NOTHING;
""")

# --- customer ---
cur.execute("""
INSERT INTO customer (customer_id, customer_name, phone, email, address) VALUES
(1, 'GreenGrocer Markets',   '555-0201', 'buy@grocer.com',     '100 Main St, City'),
(2, 'HealthyFoods Chain',    '555-0202', 'order@healthy.com',  '200 Oak Ave, Town'),
(3, 'CornerStore Group',     '555-0203', 'buy@cornerstore.com','50 Pine Rd, Village'),
(4, 'Wholesome Distributors','555-0204', 'info@wholesome.com', '75 River Dr, Metro'),
(5, 'FreshMart Inc.',        '555-0205', 'purchasing@freshmart.com', '300 Market Blvd, City')
ON CONFLICT (customer_id) DO NOTHING;
""")

# --- raw_material (depends on unit_of_measure) ---
cur.execute("""
INSERT INTO raw_material (material_id, material_name, base_uom_id, reorder_level, description) VALUES
(1, 'Fresh Milk',          1, 2000, 'Whole cow milk, chilled'),
(2, 'Skim Milk',           1, 1000, 'Fat-free milk base'),
(3, 'Cream',               1, 500,  'Heavy cream for Greek yogurt'),
(4, 'Yogurt Cultures',     2, 20,   'Freeze-dried starter cultures (S. thermophilus, L. bulgaricus)'),
(5, 'Pectin',              2, 50,   'Natural stabilizer/thickener'),
(6, 'Gelatin',             2, 30,   'Food-grade gelatin for texture'),
(7, 'Sugar',               2, 200,  'Refined white sugar'),
(8, 'Strawberry Puree',    2, 100,  'Concentrated strawberry flavor'),
(9, 'Vanilla Extract',     4, 20,   'Natural vanilla flavoring'),
(10,'Mango Pulp',          2, 80,   'Concentrated mango puree'),
(11,'Blueberry Compote',   2, 60,   'Blueberry fruit preparation'),
(12,'Honey',               1, 40,   'Natural honey sweetener'),
(13,'Vitamin D3',          2, 5,    'Vitamin D3 fortification powder'),
(14,'Probiotic Blend',     2, 10,   'Bifidobacterium, Lactobacillus strains'),
(15,'Packaging Cups 150ml',6, 5000, 'Empty cups for 150ml yogurt'),
(16,'Packaging Cups 500ml',6, 3000, 'Empty cups for 500ml yogurt'),
(17,'Lids 150ml',          6, 5000, 'Foil lids for 150ml cups'),
(18,'Lids 500ml',          6, 3000, 'Foil lids for 500ml cups'),
(19,'Labels',              6, 10000,'Product labels'),
(20,'Cardboard Boxes',     6, 1000, 'Shipping boxes')
ON CONFLICT (material_id) DO NOTHING;
""")

# --- product ---
cur.execute("""
INSERT INTO product (product_id, product_name, product_type, selling_price, expiry_period, is_active) VALUES
(1, 'Plain Yogurt 1L',       'Stirred',   3.50, 21, true),
(2, 'Greek Yogurt 500ml',    'Greek',     4.25, 28, true),
(3, 'Strawberry Yogurt 150ml','Fruit',    1.50, 21, true),
(4, 'Mango Lassi 150ml',     'Drink',     1.75, 14, true),
(5, 'Vanilla Yogurt 500ml',  'Stirred',   3.00, 21, true),
(6, 'Blueberry Yogurt 150ml','Fruit',     1.50, 21, true),
(7, 'Greek Yogurt Honey 500ml','Greek',   4.75, 28, true),
(8, 'Probiotic Plus 150ml',  'Stirred',   2.25, 21, true),
(9, 'Organic Plain 1L',      'Organic',   4.50, 18, true),
(10,'Whipped Yogurt Dessert 500ml','Dessert', 3.75, 14, true)
ON CONFLICT (product_id) DO NOTHING;
""")

# --- product_specification (depends on product) ---
cur.execute("""
INSERT INTO product_specification (spec_id, product_id, version_no, fat_content, sugar_level, expiry_days, storage_temperature, description) VALUES
(1, 1,  'A1', 3.2,  4.5, 21, 4.0, 'Standard plain stirred yogurt'),
(2, 2,  'B1', 8.5,  3.8, 28, 4.0, 'Thick Greek-style, strained'),
(3, 3,  'C1', 2.5, 11.0, 21, 4.0, 'Strawberry fruit yogurt, kids pack'),
(4, 4,  'D1', 2.0, 12.0, 14, 4.0, 'Mango lassi drinkable yogurt'),
(5, 5,  'E1', 3.0,  9.0, 21, 4.0, 'Vanilla stirred yogurt'),
(6, 6,  'F1', 2.5, 10.5, 21, 4.0, 'Blueberry fruit yogurt'),
(7, 7,  'G1', 9.0,  8.5, 28, 4.0, 'Greek yogurt with honey swirl'),
(8, 8,  'H1', 2.8,  5.5, 21, 4.0, 'Probiotic-enriched low sugar'),
(9, 9,  'I1', 3.5,  4.0, 18, 4.0, 'Certified organic whole milk'),
(10,10, 'J1', 4.0, 10.0, 14, 4.0, 'Light whipped yogurt dessert')
ON CONFLICT (spec_id) DO NOTHING;
""")

# --- recipe (depends on product) ---
cur.execute("""
INSERT INTO recipe (recipe_id, product_id, recipe_name, description, version_no, effective_date) VALUES
(1, 1, 'Plain Base 1L',     'Standard stirred yogurt recipe', 'R1', '2025-01-01'),
(2, 2, 'Greek 500ml',       'Greek yogurt strained recipe',   'R1', '2025-01-01'),
(3, 3, 'Strawberry 150ml',  'Fruit on bottom recipe',         'R1', '2025-01-15'),
(4, 4, 'Mango Lassi',       'Drinkable yogurt with mango',    'R1', '2025-02-01'),
(5, 5, 'Vanilla 500ml',     'Vanilla stirred yogurt',         'R1', '2025-01-10'),
(6, 6, 'Blueberry 150ml',   'Blueberry fruit yogurt',         'R1', '2025-01-15'),
(7, 7, 'Greek Honey 500ml', 'Greek yogurt honey swirl',       'R1', '2025-02-01'),
(8, 8, 'Probiotic 150ml',   'Probiotic enriched formula',     'R1', '2025-03-01'),
(9, 9, 'Organic Plain 1L',  'Organic certified recipe',       'R1', '2025-01-01'),
(10,10,'Whipped Dessert',   'Whipped dessert recipe',         'R1', '2025-03-15')
ON CONFLICT (recipe_id) DO NOTHING;
""")

# --- recipe_ingredient (depends on recipe, raw_material, unit_of_measure) ---
cur.execute("""
INSERT INTO recipe_ingredient (recipe_ingredient_id, recipe_id, material_id, uom_id, quantity) VALUES
-- Recipe 1: Plain Yogurt 1L
(1, 1, 1,  1, 0.950), (2, 1, 4, 2, 0.010), (3, 1, 13, 2, 0.010),
-- Recipe 2: Greek Yogurt 500ml
(4, 2, 1,  1, 1.200), (5, 2, 3, 1, 0.200), (6, 2, 4, 2, 0.010),
-- Recipe 3: Strawberry 150ml
(7, 3, 1,  1, 0.100), (8, 3, 8, 2, 0.025), (9, 3, 7, 2, 0.010), (10, 3, 4, 2, 0.010),
-- Recipe 4: Mango Lassi
(11,4, 1,  1, 0.100), (12,4, 10, 2, 0.030), (13,4, 7, 2, 0.010), (14,4, 4, 2, 0.010),
-- Recipe 5: Vanilla 500ml
(15,5, 2,  1, 0.450), (16,5, 9, 4, 0.010), (17,5, 7, 2, 0.015), (18,5, 4, 2, 0.010),
-- Recipe 6: Blueberry 150ml
(19,6, 1,  1, 0.100), (20,6, 11, 2, 0.025), (21,6, 7, 2, 0.010), (22,6, 4, 2, 0.010),
-- Recipe 7: Greek Honey 500ml
(23,7, 1,  1, 0.800), (24,7, 3, 1, 0.300), (25,7, 12, 1, 0.040), (26,7, 4, 2, 0.010),
-- Recipe 8: Probiotic 150ml
(27,8, 2,  1, 0.120), (28,8, 14, 2, 0.010), (29,8, 4, 2, 0.010), (30,8, 13, 2, 0.010),
-- Recipe 9: Organic Plain 1L
(31,9, 1,  1, 0.950), (32,9, 4, 2, 0.010), (33,9, 13, 2, 0.010),
-- Recipe 10: Whipped Dessert
(34,10,2, 1, 0.350), (35,10,3, 1, 0.100), (36,10,7, 2, 0.020), (37,10,5, 2, 0.010), (38,10,4, 2, 0.010)
ON CONFLICT (recipe_ingredient_id) DO NOTHING;
""")

# --- machine ---
cur.execute("""
INSERT INTO machine (machine_id, machine_name, machine_type, location, status, purchase_date) VALUES
(1, 'MIXER-01',  'Mixer',     'Hall A', 'Operational', '2023-01-15'),
(2, 'MIXER-02',  'Mixer',     'Hall A', 'Operational', '2023-06-20'),
(3, 'PASTEURIZER-01', 'Pasteurizer', 'Hall A', 'Operational', '2022-11-01'),
(4, 'INCUBATOR-A','Incubator','Hall B', 'Operational', '2023-03-10'),
(5, 'INCUBATOR-B','Incubator','Hall B', 'Under Maintenance', '2023-03-10'),
(6, 'COOLER-01',  'Cooler',   'Hall B', 'Operational', '2022-12-01'),
(7, 'FILLER-01',  'Filler',   'Hall C', 'Operational', '2024-01-10'),
(8, 'FILLER-02',  'Filler',   'Hall C', 'Operational', '2024-01-10'),
(9, 'LABELER-01', 'Labeler',  'Hall C', 'Operational', '2024-02-15'),
(10,'SEALER-01',  'Sealer',   'Hall C', 'Operational', '2024-02-15'),
(11,'STORAGE-01', 'Cold Room','Warehouse','Operational','2022-06-01'),
(12,'STORAGE-02', 'Freezer',  'Warehouse','Operational','2022-06-01')
ON CONFLICT (machine_id) DO NOTHING;
""")

# --- lot (depends on raw_material) ---
cur.execute("""
INSERT INTO lot (lot_id, material_id, batch_no, manufacture_date, expiry_date, quantity_received) VALUES
(1, 1,  'MIL-2025-001', '2025-05-01', '2025-05-07', 10000),
(2, 1,  'MIL-2025-002', '2025-05-05', '2025-05-11', 8000),
(3, 3,  'CRM-2025-001', '2025-05-01', '2025-05-14', 2000),
(4, 4,  'CUL-2025-001', '2025-04-01', '2026-04-01', 100),
(5, 7,  'SUG-2025-001', '2025-03-01', '2026-03-01', 1000),
(6, 8,  'STR-2025-001', '2025-04-15', '2025-10-15', 500),
(7, 10, 'MAN-2025-001', '2025-04-01', '2025-10-01', 300),
(8, 12, 'HON-2025-001', '2025-03-01', '2026-03-01', 200),
(9, 15, 'CUP-150-001',  '2025-01-01', '2026-01-01', 20000),
(10,16,'CUP-500-001',   '2025-01-01', '2026-01-01', 10000)
ON CONFLICT (lot_id) DO NOTHING;
""")

# --- inventory (depends on raw_material, lot, unit_of_measure) ---
cur.execute("""
INSERT INTO inventory (inventory_id, material_id, lot_id, quantity_on_hand, reserved_qty, uom_id) VALUES
(1, 1, 1,  5000.00,  500.00, 1),
(2, 1, 2,  6000.00,  300.00, 1),
(3, 3, 3,  1500.00,  200.00, 1),
(4, 4, 4,  80.00,     5.00,  2),
(5, 7, 5,  800.00,    50.00, 2),
(6, 8, 6,  400.00,    30.00, 2),
(7, 10,7,  250.00,    20.00, 2),
(8, 12,8,  150.00,    10.00, 1),
(9, 15,9,  15000.00, 2000.00, 6),
(10,16,10, 8000.00,  1000.00, 6)
ON CONFLICT (inventory_id) DO NOTHING;
""")

# --- purchase_order (depends on supplier) ---
cur.execute("""
INSERT INTO purchase_order (poid, supplier_id, order_date, status, total_amount) VALUES
(1, 1, '2025-04-01', 'Completed', 15000.00),
(2, 1, '2025-04-15', 'Completed', 12000.00),
(3, 2, '2025-03-01', 'Completed', 5000.00),
(4, 4, '2025-04-20', 'Pending',  3500.00),
(5, 5, '2025-05-01', 'Pending',  4200.00),
(6, 3, '2025-04-25', 'Completed', 8000.00)
ON CONFLICT (poid) DO NOTHING;
""")

# --- purchase_order_line (depends on purchase_order, raw_material, unit_of_measure) ---
cur.execute("""
INSERT INTO purchase_order_line (po_line_id, poid, material_id, uom_id, order_qty, unit_price) VALUES
(1, 1, 1,  1, 10000, 1.00),(2, 1, 3,  1, 2000, 2.50),
(3, 2, 1,  1, 8000,  1.05),(4, 2, 15, 6, 10000, 0.15),
(5, 3, 4,  2, 100,   30.00),(6, 3, 14, 2, 50, 40.00),
(7, 4, 5,  2, 200,   12.50),(8, 4, 6,  2, 100, 10.00),
(9, 5, 8,  2, 300,   10.00),(10,5, 10, 2, 120, 10.00),
(11,6, 15, 6, 10000, 0.12),(12,6, 16, 6, 5000, 0.20),
(13,6, 20, 6, 2000,  1.50)
ON CONFLICT (po_line_id) DO NOTHING;
""")

# --- production_batch (depends on product, recipe, user_account) ---
cur.execute("""
INSERT INTO production_batch (batch_id, product_id, recipe_id, batch_date, planned_qty, actual_qty, status, created_by) VALUES
(1, 1, 1, '2025-05-01', 2000, 1950, 'Completed', 1),
(2, 1, 1, '2025-05-03', 1500, 1480, 'Completed', 2),
(3, 2, 2, '2025-05-02', 1000, 980,  'Completed', 1),
(4, 3, 3, '2025-05-04', 5000, 4920, 'Completed', 2),
(5, 4, 4, '2025-05-05', 3000, 2980, 'Completed', 8),
(6, 5, 5, '2025-05-06', 1500, 1490, 'Completed', 8),
(7, 1, 1, '2025-05-08', 2000, 2000, 'InProgress', 1),
(8, 2, 2, '2025-05-08', 1200, NULL,  'InProgress', 2),
(9, 3, 3, '2025-05-09', 4000, NULL,  'Planned',   8),
(10,6, 6, '2025-05-09', 3000, NULL,  'Planned',   2),
(11,7, 7, '2025-05-10', 800,  NULL,  'Planned',   1),
(12,8, 8, '2025-05-10', 2000, NULL,  'Planned',   8),
(13,10,10,'2025-05-07', 1000, 990,   'Completed', 1),
(14,9, 9, '2025-05-06', 500,  495,   'Completed', 2)
ON CONFLICT (batch_id) DO NOTHING;
""")

# --- batch_material_consumption (depends on production_batch, lot, raw_material, uom) ---
cur.execute("""
INSERT INTO batch_material_consumption (consumption_id, batch_id, lot_id, material_id, uom_id, quantity_used) VALUES
(1, 1, 1, 1, 1, 1900),(2, 1, 4, 4, 2, 20),(3, 2, 2, 1, 1, 1450),(4, 2, 4, 4, 2, 15),
(5, 3, 1, 1, 1, 1200),(6, 3, 3, 3, 1, 200),(7, 3, 4, 4, 2, 8),
(8, 4, 2, 1, 1, 500),(9, 4, 6, 8, 2, 125),(10,4, 5, 7, 2, 40),(11,4, 4, 4, 2, 10),
(12,5, 2, 1, 1, 300),(13,5, 7, 10,2, 90),(14,5, 5, 7, 2, 30),(15,5, 4, 4, 2, 6),
(16,6, 2, 2, 1, 700),(17,6, 4, 4, 2, 7),(18,6, 5, 7, 2, 22),(19,6, 8, 12,1, 7.5),
(20,7, 2, 1, 1, 1950),(21,7, 4, 4, 2, 20),(22,13,2, 2, 1, 350),(23,13,3, 3, 1, 100),(24,13,5, 5, 2, 5),(25,13,5, 7, 2, 20),
(26,14,1, 1, 1, 490),(27,14,4, 4, 2, 5)
ON CONFLICT (consumption_id) DO NOTHING;
""")

# --- quality_control (depends on production_batch, employee) ---
cur.execute("""
INSERT INTO quality_control (qcid, batch_id, inspector_id, inspection_date, status, remarks) VALUES
(1, 1, 2, '2025-05-01', 'Pass',    'All parameters within spec.'),
(2, 2, 2, '2025-05-03', 'Pass',    'pH 4.5, fat 3.2%, solids 12.1%'),
(3, 3, 8, '2025-05-02', 'Pass',    'Greek texture verified, fat 8.5%'),
(4, 4, 8, '2025-05-04', 'Pass',    'Strawberry flavor profile correct, sugar 11%'),
(5, 5, 2, '2025-05-05', 'Pass',    'Mango lassi, viscosity within range'),
(6, 6, 8, '2025-05-06', 'Pass',    'Vanilla flavor consistent, no off-notes'),
(7, 7, 2, '2025-05-08', 'Pass',    'Standard batch, QC approved'),
(8, 13,8, '2025-05-07', 'Fail',    'Over-whipped, texture too airy. Rework required.'),
(9, 13,2, '2025-05-07', 'Pass',    'After rework: texture corrected, approved.'),
(10,14,2, '2025-05-06', 'Pass',    'Organic certification verified, all clear.')
ON CONFLICT (qcid) DO NOTHING;
""")

# --- maintenance (depends on machine, employee) ---
cur.execute("""
INSERT INTO maintenance (maintenance_id, machine_id, maintenance_type, description, scheduled_date, performed_date, performed_by, cost, next_due_date) VALUES
(1, 1, 'Preventive',  'Monthly lubrication and belt check',    '2025-04-01', '2025-04-01', 4, 350.00, '2025-05-01'),
(2, 3, 'Preventive',  'Pasteurizer plate inspection',          '2025-04-05', '2025-04-06', 4, 800.00, '2025-05-05'),
(3, 4, 'Preventive',  'Incubator temp calibration',            '2025-04-10', '2025-04-10', 4, 200.00, '2025-05-10'),
(4, 5, 'Corrective',  'Incubator-B temperature sensor failed', '2025-04-15', '2025-04-16', 4, 1200.00, '2025-05-15'),
(5, 7, 'Preventive',  'Filler nozzle replacement',             '2025-04-20', '2025-04-20', 4, 500.00, '2025-05-20'),
(6, 2, 'Preventive',  'Mixer blade wear check',                '2025-05-01', NULL, NULL, NULL, '2025-06-01'),
(7, 8, 'Preventive',  'Filler-02 calibration',                 '2025-05-05', NULL, NULL, NULL, '2025-06-05'),
(8, 11,'Preventive',  'Cold room door seal check',             '2025-04-25', '2025-04-25', 4, 150.00, '2025-05-25')
ON CONFLICT (maintenance_id) DO NOTHING;
""")

# --- product_inventory (depends on product, production_batch, unit_of_measure) ---
cur.execute("""
INSERT INTO product_inventory (product_inventory_id, product_id, batch_id, quantity_on_hand, reserved_qty, uom_id, expiry_date) VALUES
(1,  1, 1, 800.00, 200.00, 5, '2025-05-22'),
(2,  1, 2, 500.00, 100.00, 5, '2025-05-24'),
(3,  2, 3, 400.00, 100.00, 5, '2025-05-30'),
(4,  3, 4, 3000.00,500.00, 5, '2025-05-25'),
(5,  4, 5, 1500.00,300.00, 5, '2025-05-19'),
(6,  5, 6, 600.00, 150.00, 5, '2025-05-27'),
(7,  1, 7, 2000.00, 0.00,  5, '2025-05-29'),
(8,  10,13, 700.00, 100.00, 5, '2025-05-21'),
(9,  9, 14, 300.00,  50.00, 5, '2025-05-24')
ON CONFLICT (product_inventory_id) DO NOTHING;
""")

# --- sales_order (depends on customer) ---
cur.execute("""
INSERT INTO sales_order (sales_id, customer_id, sale_date, status, total_amount) VALUES
(1, 1, '2025-05-02', 'Delivered', 5250.00),
(2, 2, '2025-05-03', 'Delivered', 3400.00),
(3, 3, '2025-05-05', 'Processing', 2800.00),
(4, 4, '2025-05-06', 'Pending',    6000.00),
(5, 5, '2025-05-07', 'Processing', 4500.00),
(6, 1, '2025-05-08', 'Pending',    3500.00)
ON CONFLICT (sales_id) DO NOTHING;
""")

# --- sales_order_line (depends on sales_order, product, unit_of_measure) ---
cur.execute("""
INSERT INTO sales_order_line (sales_line_id, sales_id, product_id, uom_id, quantity, unit_price) VALUES
(1, 1, 1, 5, 500, 3.50),(2, 1, 3, 5, 2000, 1.50),(3, 1, 5, 5, 200, 3.00),
(4, 2, 2, 5, 400, 4.25),(5, 2, 8, 5, 600, 2.25),(6, 2, 4, 5, 200, 1.75),
(7, 3, 3, 5, 1000, 1.50),(8, 3, 6, 5, 800, 1.50),(9, 3, 10,5, 200, 3.75),
(10,4, 1, 5, 1000, 3.50),(11,4, 2, 5, 500, 4.25),(12,4, 9, 5, 100, 4.50),
(13,5, 3, 5, 2000, 1.50),(14,5, 7, 5, 300, 4.75),
(15,6, 5, 5, 500, 3.00),(16,6, 8, 5, 600, 2.25),(17,6, 6, 5, 400, 1.50)
ON CONFLICT (sales_line_id) DO NOTHING;
""")

# --- delivery (depends on sales_order, employee) ---
cur.execute("""
INSERT INTO delivery (delivery_id, sales_id, delivery_date, delivery_address, delivery_status, delivered_by) VALUES
(1, 1, '2025-05-03', '100 Main St, City',  'Delivered', 3),
(2, 2, '2025-05-04', '200 Oak Ave, Town',  'Delivered', 3),
(3, 3, '2025-05-06', '50 Pine Rd, Village', 'In Transit', 9),
(4, 5, '2025-05-08', '300 Market Blvd, City','Scheduled', NULL)
ON CONFLICT (delivery_id) DO NOTHING;
""")

# --- stock_transaction (depends on material, product, lot, batch) ---
cur.execute("""
INSERT INTO stock_transaction (transaction_id, transaction_date, transaction_type, material_id, product_id, lot_id, batch_id, quantity, reference_type, reference_id) VALUES
(1,  '2025-05-01 08:00', 'Inbound',     1, NULL, 1, NULL,  10000, 'PO', 1),
(2,  '2025-05-01 09:00', 'Consumption', 1, NULL, 1, 1,     1900,  'Batch', 1),
(3,  '2025-05-01 14:00', 'Inbound',     NULL, 1,  NULL, 1, 1950,  'Batch', 1),
(4,  '2025-05-02 08:00', 'Consumption', 1, NULL, 1, 3,     1200,  'Batch', 3),
(5,  '2025-05-02 08:00', 'Consumption', 3, NULL, 3, 3,     200,   'Batch', 3),
(6,  '2025-05-02 15:00', 'Inbound',     NULL, 2,  NULL, 3, 980,   'Batch', 3),
(7,  '2025-05-03 08:00', 'Consumption', 1, NULL, 2, 2,     1450,  'Batch', 2),
(8,  '2025-05-03 16:00', 'Inbound',     NULL, 1,  NULL, 2, 1480,  'Batch', 2),
(9,  '2025-05-04 08:00', 'Consumption', 1, NULL, 2, 4,     500,   'Batch', 4),
(10, '2025-05-04 08:00', 'Consumption', 8, NULL, 6, 4,     125,   'Batch', 4),
(11, '2025-05-04 08:00', 'Consumption', 7, NULL, 5, 4,     40,    'Batch', 4),
(12, '2025-05-04 16:00', 'Inbound',     NULL, 3,  NULL, 4, 4920,  'Batch', 4),
(13, '2025-05-05 10:00', 'Outbound',    NULL, 1,  NULL, 1, 500,   'SO', 1),
(14, '2025-05-05 10:00', 'Outbound',    NULL, 3,  NULL, 4, 2000,  'SO', 1),
(15, '2025-05-06 10:00', 'Outbound',    NULL, 2,  NULL, 3, 400,   'SO', 2),
(16, '2025-05-06 16:00', 'Inbound',     NULL, 10, NULL, 13,990,   'Batch', 13),
(17, '2025-05-07 08:00', 'Consumption', 2, NULL, 2, 13,     350,  'Batch', 13),
(18, '2025-05-07 08:00', 'Consumption', 3, NULL, 3, 13,     100,  'Batch', 13),
(19, '2025-05-08 08:00', 'Consumption', 1, NULL, 2, 7,     1950,  'Batch', 7),
(20, '2025-05-08 16:00', 'Inbound',     NULL, 1,  NULL, 7, 2000,  'Batch', 7)
ON CONFLICT (transaction_id) DO NOTHING;
""")

# ============================================================
# STEP 3: Reset sequences to max values
# ============================================================
cur.execute("""
CREATE OR REPLACE FUNCTION fn_ensure_and_set_seq(seq_name TEXT, tbl_name TEXT, col_name TEXT)
RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = seq_name) THEN
        EXECUTE format('CREATE SEQUENCE %I', seq_name);
    END IF;
    EXECUTE format('SELECT setval(%L, COALESCE((SELECT MAX(%I) FROM %I), 1))', seq_name, col_name, tbl_name);
END;
$$ LANGUAGE plpgsql;

SELECT fn_ensure_and_set_seq('user_account_user_id_seq', 'user_account', 'user_id');
SELECT fn_ensure_and_set_seq('batch_material_consumption_consumption_id_seq', 'batch_material_consumption', 'consumption_id');
SELECT fn_ensure_and_set_seq('customer_customer_id_seq', 'customer', 'customer_id');
SELECT fn_ensure_and_set_seq('delivery_delivery_id_seq', 'delivery', 'delivery_id');
SELECT fn_ensure_and_set_seq('department_department_id_seq', 'department', 'department_id');
SELECT fn_ensure_and_set_seq('employee_employee_id_seq', 'employee', 'employee_id');
SELECT fn_ensure_and_set_seq('inventory_inventory_id_seq', 'inventory', 'inventory_id');
SELECT fn_ensure_and_set_seq('lot_lot_id_seq', 'lot', 'lot_id');
SELECT fn_ensure_and_set_seq('machine_machine_id_seq', 'machine', 'machine_id');
SELECT fn_ensure_and_set_seq('maintenance_maintenance_id_seq', 'maintenance', 'maintenance_id');
SELECT fn_ensure_and_set_seq('product_product_id_seq', 'product', 'product_id');
SELECT fn_ensure_and_set_seq('product_inventory_product_inventory_id_seq', 'product_inventory', 'product_inventory_id');
SELECT fn_ensure_and_set_seq('product_specification_spec_id_seq', 'product_specification', 'spec_id');
SELECT fn_ensure_and_set_seq('production_batch_batch_id_seq', 'production_batch', 'batch_id');
SELECT fn_ensure_and_set_seq('purchase_order_poid_seq', 'purchase_order', 'poid');
SELECT fn_ensure_and_set_seq('purchase_order_line_po_line_id_seq', 'purchase_order_line', 'po_line_id');
SELECT fn_ensure_and_set_seq('quality_control_qcid_seq', 'quality_control', 'qcid');
SELECT fn_ensure_and_set_seq('raw_material_material_id_seq', 'raw_material', 'material_id');
SELECT fn_ensure_and_set_seq('recipe_recipe_id_seq', 'recipe', 'recipe_id');
SELECT fn_ensure_and_set_seq('recipe_ingredient_recipe_ingredient_id_seq', 'recipe_ingredient', 'recipe_ingredient_id');
SELECT fn_ensure_and_set_seq('role_role_id_seq', 'role', 'role_id');
SELECT fn_ensure_and_set_seq('sales_order_sales_id_seq', 'sales_order', 'sales_id');
SELECT fn_ensure_and_set_seq('sales_order_line_sales_line_id_seq', 'sales_order_line', 'sales_line_id');
SELECT fn_ensure_and_set_seq('stock_transaction_transaction_id_seq', 'stock_transaction', 'transaction_id');
SELECT fn_ensure_and_set_seq('supplier_supplier_id_seq', 'supplier', 'supplier_id');
SELECT fn_ensure_and_set_seq('unit_of_measure_uom_id_seq', 'unit_of_measure', 'uom_id');
""")

print("Database seeded successfully!")
print("Added:", 27, "tables with full data + audit_log + triggers")

cur.close()
conn.close()
