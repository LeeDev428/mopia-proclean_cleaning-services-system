import os
import django
import psycopg2
from django.db import connection

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.conf import settings

def fix_userprofile_schema():
    """Fix the UserProfile schema synchronization issue"""
    print("\n🔧 Fixing UserProfile Schema Synchronization 🔧")
    print("===============================================")
    
    # Get database settings from Django
    db_settings = settings.DATABASES['default']
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=db_settings['NAME'],
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            host=db_settings['HOST'],
            port=db_settings['PORT']
        )
        
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL database successfully")
        
        # Check if core_userprofile table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'core_userprofile'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("❌ core_userprofile table does not exist")
            print("Creating core_userprofile table...")
            
            # Create the table with all required fields
            cursor.execute("""
                CREATE TABLE core_userprofile (
                    id SERIAL PRIMARY KEY,
                    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                    phone VARCHAR(20) NOT NULL DEFAULT '',
                    address TEXT NOT NULL DEFAULT '',
                    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    email_verification_token VARCHAR(100),
                    token_expiry TIMESTAMP WITH TIME ZONE,
                    user_id INTEGER NOT NULL UNIQUE,
                    FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
                );
            """)
            
            print("✅ core_userprofile table created successfully!")
        else:
            print("✅ core_userprofile table already exists")
            
            # Check if is_email_verified column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'core_userprofile'
                    AND column_name = 'is_email_verified'
                );
            """)
            
            column_exists = cursor.fetchone()[0]
            
            if not column_exists:
                print("Adding missing is_email_verified column...")
                cursor.execute("""
                    ALTER TABLE core_userprofile 
                    ADD COLUMN is_email_verified BOOLEAN NOT NULL DEFAULT FALSE;
                """)
                print("✅ is_email_verified column added successfully!")
            else:
                print("✅ is_email_verified column already exists")
            
            # Check if email_verification_token column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'core_userprofile'
                    AND column_name = 'email_verification_token'
                );
            """)
            
            token_column_exists = cursor.fetchone()[0]
            
            if not token_column_exists:
                print("Adding missing email_verification_token column...")
                cursor.execute("""
                    ALTER TABLE core_userprofile 
                    ADD COLUMN email_verification_token VARCHAR(100);
                """)
                print("✅ email_verification_token column added successfully!")
            else:
                print("✅ email_verification_token column already exists")
            
            # Check if token_expiry column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'core_userprofile'
                    AND column_name = 'token_expiry'
                );
            """)
            
            expiry_column_exists = cursor.fetchone()[0]
            
            if not expiry_column_exists:
                print("Adding missing token_expiry column...")
                cursor.execute("""
                    ALTER TABLE core_userprofile 
                    ADD COLUMN token_expiry TIMESTAMP WITH TIME ZONE;
                """)
                print("✅ token_expiry column added successfully!")
            else:
                print("✅ token_expiry column already exists")
        
        # List all columns in the table for verification
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'core_userprofile'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("\n📋 Current core_userprofile table structure:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]}) - Nullable: {col[2]} - Default: {col[3]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ UserProfile schema fix completed successfully!")
        print("Now try running the Django server and test user registration.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error fixing schema: {e}")
        return False

if __name__ == "__main__":
    success = fix_userprofile_schema()
    
    if success:
        print("\n🎉 Schema fix completed! You can now:")
        print("1. Run: python manage.py runserver")
        print("2. Test user registration")
    else:
        print("\n💥 Schema fix failed. Please check your PostgreSQL connection.")
