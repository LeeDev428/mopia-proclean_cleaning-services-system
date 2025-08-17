import os
import django
import psycopg2

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.conf import settings

def create_userprofile_table():
    """Create the UserProfile table directly in PostgreSQL"""
    print("\n🔧 Creating UserProfile Table 🔧")
    print("===============================")
    
    # Get database settings from Django
    db_settings = settings.DATABASES['default']
    db_name = db_settings['NAME']
    db_user = db_settings['USER']
    db_password = db_settings['PASSWORD']
    db_host = db_settings['HOST']
    db_port = db_settings['PORT']
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if the table already exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'core_userprofile'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("UserProfile table already exists. Skipping creation.")
            return True
            
        print("Creating core_userprofile table...")
        
        # First check if auth_user table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'auth_user'
            );
        """)
        
        auth_user_exists = cursor.fetchone()[0]
        
        if not auth_user_exists:
            print("Error: auth_user table doesn't exist! Please run migrations first.")
            return False
            
        # Create the UserProfile table
        cursor.execute("""
            CREATE TABLE core_userprofile (
                id SERIAL PRIMARY KEY,
                is_admin BOOLEAN NOT NULL DEFAULT false,
                phone VARCHAR(20) NULL,
                address TEXT NULL,
                user_id INTEGER NOT NULL UNIQUE,
                CONSTRAINT core_userprofile_user_id_fkey 
                    FOREIGN KEY (user_id) REFERENCES auth_user(id) 
                    ON DELETE CASCADE
            );
        """)
        
        print("✅ core_userprofile table created successfully!")
        
        # Add the migration record
        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('core', '0002_userprofile', NOW())
            ON CONFLICT DO NOTHING;
        """)
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating UserProfile table: {e}")
        return False

if __name__ == "__main__":
    success = create_userprofile_table()
    
    if success:
        print("\n✅ UserProfile table created successfully!")
        print("You should now be able to login and register.")
    else:
        print("\n❌ Failed to create UserProfile table.")
