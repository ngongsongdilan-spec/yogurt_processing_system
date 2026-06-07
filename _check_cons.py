import psycopg2
conn = psycopg2.connect(dbname='yogurt', user='postgres', password='Mypassword@2', host='localhost', port='5432')
cur = conn.cursor()
cur.execute("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE contype='c' ORDER BY conname")
for r in cur.fetchall():
    print(f"{r[0]}: {r[1]}")
cur.close()
conn.close()
