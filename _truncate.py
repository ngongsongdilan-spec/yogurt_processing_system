import psycopg2
conn = psycopg2.connect(dbname='yogurt', user='postgres', password='Mypassword@2', host='localhost', port='5432')
conn.autocommit = True
cur = conn.cursor()

# Temporarily disable audit triggers, truncate, re-run seed
cur.execute("""
DO $$ DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT trigger_name, event_object_table FROM information_schema.triggers WHERE trigger_schema='public' AND trigger_name LIKE 'trg_audit_%') LOOP
        EXECUTE format('ALTER TABLE %I DISABLE TRIGGER %I', r.event_object_table, r.trigger_name);
    END LOOP;
END $$;
""")

# Truncate all tables except audit_log
tables = [
    'batch_material_consumption', 'customer', 'delivery', 'employee',
    'inventory', 'lot', 'machine', 'maintenance', 'product',
    'product_inventory', 'product_specification', 'production_batch',
    'purchase_order', 'purchase_order_line', 'quality_control',
    'raw_material', 'recipe', 'recipe_ingredient', 'sales_order',
    'sales_order_line', 'stock_transaction', 'supplier', 'user_account',
    'role', 'department', 'unit_of_measure'
]
for t in tables:
    cur.execute(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE")

print("All tables truncated. Ready for fresh seed.")
cur.close()
conn.close()
