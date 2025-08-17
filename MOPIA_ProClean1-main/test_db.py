import psycopg2

try:
    connection = psycopg2.connect(
        dbname="mopia_db",
        user="postgres",
        password="leetorres0428",
        host="localhost",
        port="5432"
    )
    print("Connection successful!")
    connection.close()
except Exception as e:
    print(f"Connection failed: {e}")
