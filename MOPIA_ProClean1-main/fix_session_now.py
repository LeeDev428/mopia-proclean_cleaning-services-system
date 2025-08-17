import psycopg2
import sys
import os
import django
import subprocess

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.conf import settings
from django.db import connections

def run_migrations():
    """Run Django migrations to create all required tables"""
    print("\n📋 Attempting to run Django migrations...")
    try:
        # First run makemigrations to ensure all models are tracked
        print("Creating migrations...")
        subprocess.run([sys.executable, 'manage.py', 'makemigrations'], check=True)
        
        # Run migrations for auth app first
        print("\nMigrating auth app...")
        subprocess.run([sys.executable, 'manage.py', 'migrate', 'auth'], check=True)
        
        # Run migrations for the contenttypes app (often a dependency)
        print("\nMigrating contenttypes app...")
        subprocess.run([sys.executable, 'manage.py', 'migrate', 'contenttypes'], check=True)
        
        # Run migrations for sessions app
        print("\nMigrating sessions app...")
        subprocess.run([sys.executable, 'manage.py', 'migrate', 'sessions'], check=True)
        
        # Run all remaining migrations
        print("\nRunning all remaining migrations...")
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--run-syncdb'], check=True)
        
        print("\n✅ Migrations completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Migration failed: {e}")
        return False

def create_core_tables_directly():
    """Create essential Django tables using direct SQL commands"""
    print("\n📊 Attempting to create tables directly with SQL...")
    
    # Get database settings from Django
    db_settings = settings.DATABASES['default']
    db_name = db_settings['NAME']
    db_user = db_settings['USER']
    db_password = db_settings['PASSWORD']
    db_host = db_settings['HOST']
    db_port = db_settings['PORT']
    
    print(f"Connecting to PostgreSQL database: {db_name}")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        
        # Set autocommit mode
        conn.autocommit = True
        
        # Create a cursor
        cursor = conn.cursor()
        
        print("Successfully connected to PostgreSQL")
        
        # Check for essential tables
        tables_to_check = ["django_session", "auth_user", "django_content_type"]
        missing_tables = []
        
        for table in tables_to_check:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                );
            """)
            
            if not cursor.fetchone()[0]:
                missing_tables.append(table)
        
        if not missing_tables:
            print("All essential Django tables already exist.")
            return True
            
        print(f"Missing tables: {', '.join(missing_tables)}")
        
        # Create auth_user table if it doesn't exist
        if "auth_user" in missing_tables:
            print("\nCreating auth_user table...")
            cursor.execute("""
                CREATE TABLE auth_user (
                    id SERIAL PRIMARY KEY,
                    password VARCHAR(128) NOT NULL,
                    last_login TIMESTAMP WITH TIME ZONE NULL,
                    is_superuser BOOLEAN NOT NULL,
                    username VARCHAR(150) NOT NULL UNIQUE,
                    first_name VARCHAR(150) NOT NULL,
                    last_name VARCHAR(150) NOT NULL,
                    email VARCHAR(254) NOT NULL,
                    is_staff BOOLEAN NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    date_joined TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
            print("✅ auth_user table created!")
            
        # Create django_content_type table if it doesn't exist
        if "django_content_type" in missing_tables:
            print("\nCreating django_content_type table...")
            cursor.execute("""
                CREATE TABLE django_content_type (
                    id SERIAL PRIMARY KEY,
                    app_label VARCHAR(100) NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    CONSTRAINT django_content_type_app_label_model_key UNIQUE (app_label, model)
                );
            """)
            print("✅ django_content_type table created!")
            
        # Create django_session table if it doesn't exist
        if "django_session" in missing_tables:
            print("\nCreating django_session table...")
            cursor.execute("""
                CREATE TABLE django_session (
                    session_key VARCHAR(40) NOT NULL PRIMARY KEY,
                    session_data TEXT NOT NULL,
                    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
                );
                CREATE INDEX django_session_expire_date_idx ON django_session (expire_date);
            """)
            print("✅ django_session table created!")
            
        # Close cursor and connection
        cursor.close()
        conn.close()
        
        print("\n✅ All essential tables created successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        return False

def create_fresh_database():
    """Drop and recreate the database from scratch"""
    # Get database settings from Django
    db_settings = settings.DATABASES['default']
    db_name = db_settings['NAME']
    db_user = db_settings['USER']
    db_password = db_settings['PASSWORD']
    db_host = db_settings['HOST']
    db_port = db_settings['PORT']
    
    print("\n⚠️ Attempting to recreate database from scratch...")
    print("This will DELETE ALL DATA and create a fresh database!")
    
    try:
        # Connect to PostgreSQL default database
        conn = psycopg2.connect(
            dbname="postgres",
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check for existing connections to the database
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
            AND pid <> pg_backend_pid();
        """)
        
        # Drop and recreate the database
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        cursor.execute(f"CREATE DATABASE {db_name}")
        
        cursor.close()
        conn.close()
        
        print(f"✅ Database '{db_name}' recreated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error recreating database: {e}")
        return False

def fix_database():
    """Complete database fix workflow"""
    print("🔧 Django Database Fix 🔧")
    print("========================")
    
    # Check database connection first
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✓ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        print("Attempting to recreate the database...")
        if not create_fresh_database():
            return False
    
    # Try running migrations first (preferred method)
    if run_migrations():
        return True
        
    # If migrations fail, try creating essential tables directly
    if create_core_tables_directly():
        print("\nBasic tables created. Now running migrations to complete setup...")
        return run_migrations()
        
    # If all else fails, try recreating the database and then migrating
    print("\n⚠️ All attempts failed. Trying database recreation as last resort...")
    if create_fresh_database() and run_migrations():
        return True
        
    return False

if __name__ == "__main__":
    print("\n🔄 Starting Django Database Fix Tool 🔄")
    print("=====================================")
    
    if fix_database():
        print("\n✅ Database fix completed!")
        print("You can now restart your Django server and try again.")
    else:
        print("\n❌ Failed to fix database.")
        print("Please check your PostgreSQL connection settings and ensure you have permission to create databases.")
        print("You might need to manually create the database or contact your database administrator.")
