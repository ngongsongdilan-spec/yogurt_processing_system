import psycopg2

conn = psycopg2.connect(
    dbname='yogurt', user='postgres', password='Mypassword@2',
    host='localhost', port='5432'
)
conn.autocommit = True
cur = conn.cursor()

# Drop old triggers first
for tbl in ['user_account', 'production_batch', 'quality_control', 'inventory',
            'product_inventory', 'stock_transaction', 'purchase_order', 'sales_order']:
    cur.execute(f"DROP TRIGGER IF EXISTS trg_audit_{tbl} ON {tbl}")

# Drop old function
cur.execute("DROP FUNCTION IF EXISTS fn_audit_trigger() CASCADE")

# Create fixed function using dollar-quoting with unique tag
cur.execute("""
CREATE OR REPLACE FUNCTION fn_audit_trigger()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $audit_func$
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

    IF _pk_col IS NULL THEN
        _pk_col := 'id';
    END IF;

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
$audit_func$;
""")

# Re-attach audit triggers
for tbl in ['user_account', 'production_batch', 'quality_control', 'inventory',
            'product_inventory', 'stock_transaction', 'purchase_order', 'sales_order']:
    cur.execute(f"""
        CREATE TRIGGER trg_audit_{tbl}
        AFTER INSERT OR UPDATE OR DELETE ON {tbl}
        FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();
    """)

print("Audit trigger function fixed and re-attached.")
cur.close()
conn.close()
