import psycopg2
conn = psycopg2.connect(dbname='yogurt', user='postgres', password='Mypassword@2', host='localhost', port='5432')
cur = conn.cursor()
cur.execute("SELECT column_name, is_generated, generation_expression FROM information_schema.columns WHERE table_name='sales_order_line' AND is_generated != 'NEVER'")
for r in cur.fetchall():
    print(f"{r[0]}: generated={r[1]}, expr={r[2]}")
cur.close()
conn.close()
