import psycopg2

# Try different connection options
connection_params = [
    {"dbname": "mopia_db", "user": "postgres", "password": "leetorres0428", "host": "localhost"},
    {"dbname": "mopia_db", "user": "postgres", "password": "leetorres0428", "host": "127.0.0.1"},
    {"dbname": "postgres", "user": "postgres", "password": "leetorres0428", "host": "localhost"},
]

for params in connection_params:
    try:
        print(f"Trying to connect with: {params}")
        conn = psycopg2.connect(**params)
        print("✅ Connection successful!")
        
        # Try to create the database if connecting to postgres worked
        if params["dbname"] == "postgres":
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute("DROP DATABASE IF EXISTS mopia_db;")
            cursor.execute("CREATE DATABASE mopia_db;")
            print("Created database mopia_db")
            
        conn.close()
        break
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()

print("Test complete")
