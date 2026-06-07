import psycopg2

def introspect():
    conn = psycopg2.connect(
        dbname="yogurt",
        user="postgres",
        password="Mypassword@2",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    tables = cursor.fetchall()
    print("Tables:", tables)

    for table in tables:
        t_name = table[0]
        cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{t_name}';")
        print(f"--- {t_name} columns ---")
        for col in cursor.fetchall():
            print(col)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    introspect()
