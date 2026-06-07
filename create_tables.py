import psycopg2

DB_CONFIG = {
    "dbname": "yogurt_factory",
    "user": "postgres",
    "password": "Mypassword@2",
    "host": "localhost",
    "port": "5432",
}


def create_schema():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()

    sql = """
    -- ============================================================
    -- SCHEMA: Yogurt Processing System
    -- Tables: user_account, inventory, product_inventory,
    --         quality_control, production_batch, machines
    -- Trigger: trg_lock_completed_batches
    -- ============================================================

    -- 1. USER ACCOUNT
    CREATE TABLE IF NOT EXISTS user_account (
        id          SERIAL PRIMARY KEY,
        username    VARCHAR(100) UNIQUE NOT NULL,
        password    VARCHAR(255) NOT NULL,
        role        VARCHAR(50) DEFAULT 'operator',
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 2. INVENTORY (raw materials)
    CREATE TABLE IF NOT EXISTS inventory (
        id          SERIAL PRIMARY KEY,
        item_name   VARCHAR(255) NOT NULL,
        quantity    INTEGER NOT NULL,
        unit        VARCHAR(50) NOT NULL
    );

    -- 3. PRODUCT INVENTORY (finished goods)
    CREATE TABLE IF NOT EXISTS product_inventory (
        id            SERIAL PRIMARY KEY,
        product_name  VARCHAR(255) NOT NULL,
        quantity      INTEGER NOT NULL,
        unit          VARCHAR(50) NOT NULL,
        batch_id      VARCHAR(100)
    );

    -- 4. QUALITY CONTROL
    CREATE TABLE IF NOT EXISTS quality_control (
        id            SERIAL PRIMARY KEY,
        batch_id      VARCHAR(100) NOT NULL,
        inspector     VARCHAR(100) NOT NULL,
        status        VARCHAR(50) NOT NULL,
        remarks       TEXT,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 5. PRODUCTION BATCH (with completion-lock trigger)
    CREATE TABLE IF NOT EXISTS production_batch (
        id          SERIAL PRIMARY KEY,
        batch_id    VARCHAR(100) UNIQUE NOT NULL,
        status      VARCHAR(50) NOT NULL DEFAULT 'Active',
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 6. MACHINES
    CREATE TABLE IF NOT EXISTS machines (
        id            SERIAL PRIMARY KEY,
        machine_id    VARCHAR(50) UNIQUE NOT NULL,
        status        VARCHAR(50) NOT NULL,
        current_batch VARCHAR(100)
    );

    -- ============================================================
    -- SEED DATA (only if tables are empty)
    -- ============================================================

    -- User: admin / admin123
    INSERT INTO user_account (username, password, role)
    SELECT 'admin', 'admin123', 'manager'
    WHERE NOT EXISTS (SELECT 1 FROM user_account WHERE username = 'admin');

    -- Raw materials
    INSERT INTO inventory (item_name, quantity, unit)
    SELECT 'Milk', 5000, 'Liters'
    WHERE NOT EXISTS (SELECT 1 FROM inventory);

    INSERT INTO inventory (item_name, quantity, unit)
    SELECT 'Cultures', 200, 'Packs'
    WHERE NOT EXISTS (SELECT 1 FROM inventory WHERE item_name = 'Cultures');

    INSERT INTO inventory (item_name, quantity, unit)
    SELECT 'Stabilizer', 150, 'Kg'
    WHERE NOT EXISTS (SELECT 1 FROM inventory WHERE item_name = 'Stabilizer');

    -- Finished goods
    INSERT INTO product_inventory (product_name, quantity, unit, batch_id)
    SELECT 'Plain Yogurt 1L', 1200, 'Units', 'BATCH-003'
    WHERE NOT EXISTS (SELECT 1 FROM product_inventory);

    INSERT INTO product_inventory (product_name, quantity, unit, batch_id)
    SELECT 'Greek Yogurt 500ml', 800, 'Units', 'BATCH-004'
    WHERE NOT EXISTS (SELECT 1 FROM product_inventory WHERE product_name = 'Greek Yogurt 500ml');

    INSERT INTO product_inventory (product_name, quantity, unit, batch_id)
    SELECT 'Strawberry Yogurt 200ml', 2000, 'Units', 'BATCH-005'
    WHERE NOT EXISTS (SELECT 1 FROM product_inventory WHERE product_name = 'Strawberry Yogurt 200ml');

    -- Production batches (one Active, one Completed for trigger demo)
    INSERT INTO production_batch (batch_id, status)
    SELECT 'BATCH-001', 'Active'
    WHERE NOT EXISTS (SELECT 1 FROM production_batch WHERE batch_id = 'BATCH-001');

    INSERT INTO production_batch (batch_id, status)
    SELECT 'BATCH-002', 'Completed'
    WHERE NOT EXISTS (SELECT 1 FROM production_batch WHERE batch_id = 'BATCH-002');

    -- Machines
    INSERT INTO machines (machine_id, status, current_batch)
    SELECT 'MIXER-01', 'ACTIVE', 'BATCH-001'
    WHERE NOT EXISTS (SELECT 1 FROM machines);

    INSERT INTO machines (machine_id, status, current_batch)
    SELECT 'INCUBATOR-A', 'IDLE', NULL
    WHERE NOT EXISTS (SELECT 1 FROM machines WHERE machine_id = 'INCUBATOR-A');

    INSERT INTO machines (machine_id, status, current_batch)
    SELECT 'FILLER-01', 'ACTIVE', 'BATCH-002'
    WHERE NOT EXISTS (SELECT 1 FROM machines WHERE machine_id = 'FILLER-01');

    -- Sample QC records
    INSERT INTO quality_control (batch_id, inspector, status, remarks)
    SELECT 'BATCH-001', 'Inspector-A', 'Pass', 'All standards met.'
    WHERE NOT EXISTS (SELECT 1 FROM quality_control);

    -- ============================================================
    -- TRIGGER: Lock completed batches from modification
    -- ============================================================
    CREATE OR REPLACE FUNCTION fn_lock_completed_batches()
    RETURNS TRIGGER AS $$
    BEGIN
        IF OLD.status = 'Completed' THEN
            RAISE EXCEPTION 'SECURITY LOCK ENGAGED: Cannot modify a completed production batch!';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trg_lock_completed_batches ON production_batch;
    CREATE TRIGGER trg_lock_completed_batches
        BEFORE UPDATE ON production_batch
        FOR EACH ROW
        EXECUTE FUNCTION fn_lock_completed_batches();

    -- ============================================================
    -- INDEXES for performance
    -- ============================================================
    CREATE INDEX IF NOT EXISTS idx_production_batch_status ON production_batch (status);
    CREATE INDEX IF NOT EXISTS idx_quality_control_batch  ON quality_control (batch_id);
    CREATE INDEX IF NOT EXISTS idx_inventory_item         ON inventory (item_name);
    """

    try:
        cursor.execute(sql)
        print("Schema created and seeded successfully!")
    except Exception as e:
        print("Error:", e)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_schema()
