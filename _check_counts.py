import psycopg2
conn = psycopg2.connect(dbname='yogurt', user='postgres', password='Mypassword@2', host='localhost', port='5432')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")
for t in cur.fetchall():
    tbl = t[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    c = cur.fetchone()[0]
    print(f"{tbl}: {c} rows")
cur.close(); conn.close()
