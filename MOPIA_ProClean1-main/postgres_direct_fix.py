import os
import django
import psycopg2
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

def create_session_table():
    """Directly create the session table in PostgreSQL using psycopg2."""
    print("Starting PostgreSQL direct session table creation...")
    
    # Get database credentials from Django settings
    db_settings = settings.DATABASES['default']
    
    # Connect to PostgreSQL
    try:
        conn = psycopg2.connect(
            dbname=db_settings['NAME'],
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            host=db_settings['HOST'],
            port=db_settings['PORT']
        )
        conn.autocommit = True  # Important for schema changes
        print("✅ Connected to PostgreSQL database successfully")
        
        # Create cursor
        cursor = conn.cursor()
        
        # First, we'll try to drop the session table if it exists with any issues
        try:
            print("Dropping existing django_session table if it exists...")
            cursor.execute("DROP TABLE IF EXISTS django_session CASCADE;")
        except Exception as e:
            print(f"Note: Could not drop table (this is often normal): {e}")
        
        # Now create the table with the exact schema Django expects
        print("Creating django_session table...")
        cursor.execute("""
        CREATE TABLE django_session (
            session_key varchar(40) NOT NULL PRIMARY KEY,
            session_data text NOT NULL,
            expire_date timestamp with time zone NOT NULL
        );
        """)
        
        # Create the index that Django expects
        print("Creating index on django_session...")
        cursor.execute("""
        CREATE INDEX django_session_expire_date_idx ON django_session (expire_date);
        """)
        
        # Check if the table was created successfully
        cursor.execute("SELECT COUNT(*) FROM django_session;")
        result = cursor.fetchone()
        print(f"✅ Table created successfully! Current row count: {result[0]}")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"❌ Error creating session table: {e}")
        return False

if __name__ == "__main__":
    if create_session_table():
        print("\n✅ SUCCESS: Django session table created directly in PostgreSQL.")
        print("Try accessing your Django application now.")
    else:
        print("\n❌ ERROR: Failed to create Django session table.")
        print("Make sure your PostgreSQL credentials are correct and you have the psycopg2 package installed.")
