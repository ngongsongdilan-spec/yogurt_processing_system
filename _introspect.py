import psycopg2

conn = psycopg2.connect(
    dbname='yogurt', user='postgres', password='Mypassword@2',
    host='localhost', port='5432'
)
cur = conn.cursor()

print("=== TABLES ===")
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")
for r in cur.fetchall():
    print(f"  {r[0]}")

print("\n=== COLUMNS PER TABLE ===")
cur.execute("SELECT table_name, column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name, ordinal_position")
for r in cur.fetchall():
    print(f"  {r[0]}.{r[1]}  ({r[2]}, nullable={r[3]}, default={r[4]})")

print("\n=== TRIGGERS ===")
cur.execute("SELECT trigger_name, event_manipulation, event_object_table, action_statement FROM information_schema.triggers WHERE trigger_schema='public' ORDER BY trigger_name")
for r in cur.fetchall():
    print(f"  TRIGGER {r[0]} ON {r[2]} ({r[1]})")
    print(f"    {r[3][:300]}")

print("\n=== FUNCTIONS ===")
cur.execute("SELECT proname, prosrc FROM pg_proc WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') AND prokind = 'f' ORDER BY proname")
for r in cur.fetchall():
    print(f"  FUNCTION {r[0]}:  {r[1][:400]}")

print("\n=== INDEXES ===")
cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY indexname")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1][:250]}")

print("\n=== CONSTRAINTS ===")
cur.execute("SELECT conname, contype, relname FROM pg_constraint c JOIN pg_class r ON r.oid = c.conrelid WHERE contype IN ('p','f','u','c') AND r.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') ORDER BY conname")
type_map = {'p': 'PK', 'f': 'FK', 'u': 'UNIQUE', 'c': 'CHECK'}
for r in cur.fetchall():
    print(f"  {r[0]} ({type_map.get(r[1], r[1])}) ON {r[2]}")

print("\n=== DATA COUNTS ===")
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        c = cur.fetchone()[0]
        print(f"  {t}: {c} rows")
    except Exception as e:
        print(f"  {t}: ERROR - {e}")

print("\n=== SAMPLE DATA FROM EACH TABLE ===")
for t in tables:
    try:
        cur.execute(f"SELECT * FROM {t} LIMIT 3")
        cols = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        print(f"\n  {t} ({', '.join(cols)}):")
        for row in rows:
            print(f"    {row}")
    except Exception as e:
        print(f"\n  {t}: ERROR - {e}")

cur.close()
conn.close()
