import psycopg2
conn = psycopg2.connect(dbname='yogurt', user='postgres', password='Mypassword@2', host='localhost', port='5432')
conn.autocommit = True
cur = conn.cursor()

# Disable all audit triggers
cur.execute("SELECT trigger_name, event_object_table FROM information_schema.triggers WHERE trigger_schema='public' AND trigger_name LIKE 'trg_audit_%'")
for r in cur.fetchall():
    cur.execute(f"ALTER TABLE {r[1]} DISABLE TRIGGER {r[0]}")

# Drop audit function
cur.execute("DROP FUNCTION IF EXISTS fn_audit_trigger() CASCADE")

# Truncate all tables
tables = ['audit_log', 'batch_material_consumption', 'customer', 'delivery', 'employee',
          'inventory', 'lot', 'machine', 'maintenance', 'product', 'product_inventory',
          'product_specification', 'production_batch', 'purchase_order', 'purchase_order_line',
          'quality_control', 'raw_material', 'recipe', 'recipe_ingredient', 'sales_order',
          'sales_order_line', 'stock_transaction', 'supplier', 'user_account',
          'role', 'department', 'unit_of_measure']
for t in tables:
    cur.execute(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE")

print("Clean slate ready.")
cur.close()
conn.close()
