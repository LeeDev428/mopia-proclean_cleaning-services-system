import os
import django
import psycopg2
import sys
import subprocess

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.conf import settings
from django.db import connection

def fix_django_migrations_table():
    """Create or fix the django_migrations table to mark key migrations as applied"""
    print("\n🔄 Fixing Django migrations history...")
    
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
        
        # Check if django_migrations table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'django_migrations'
            );
        """)
        
        migrations_table_exists = cursor.fetchone()[0]
        
        # Create migrations table if it doesn't exist
        if not migrations_table_exists:
            print("Creating django_migrations table...")
            cursor.execute("""
                CREATE TABLE django_migrations (
                    id SERIAL PRIMARY KEY,
                    app VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    applied TIMESTAMP WITH TIME ZONE NOT NULL
                );
            """)
        
        # Check if the sessions migration is already recorded
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM django_migrations 
                WHERE app = 'sessions' AND name = '0001_initial'
            );
        """)
        
        sessions_migration_exists = cursor.fetchone()[0]
        
        # Insert sessions migration if it doesn't exist
        if not sessions_migration_exists:
            print("Recording sessions migration in history...")
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied)
                VALUES ('sessions', '0001_initial', NOW());
            """)
            print("✅ Sessions migration marked as applied!")
        
        # Check for other key migrations
        key_migrations = [
            ('auth', '0001_initial'),
            ('auth', '0002_alter_permission_name_max_length'),
            ('contenttypes', '0001_initial'),
            ('contenttypes', '0002_remove_content_type_name')
        ]
        
        for app, name in key_migrations:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM django_migrations 
                    WHERE app = '{app}' AND name = '{name}'
                );
            """)
            
            migration_exists = cursor.fetchone()[0]
            
            if not migration_exists:
                print(f"Recording {app}.{name} migration in history...")
                cursor.execute(f"""
                    INSERT INTO django_migrations (app, name, applied)
                    VALUES ('{app}', '{name}', NOW());
                """)
                print(f"✅ {app}.{name} migration marked as applied!")
        
        cursor.close()
        conn.close()
        
        print("✅ Migration history fixed!")
        return True
    
    except Exception as e:
        print(f"❌ Error fixing migration history: {e}")
        return False

def verify_essential_tables():
    """Check if all essential tables exist and are structured correctly"""
    print("\n🔍 Verifying essential tables...")
    
    essential_tables = [
        "django_session",
        "auth_user",
        "django_content_type",
        "django_migrations"
    ]
    
    missing_tables = []
    
    try:
        with connection.cursor() as cursor:
            for table in essential_tables:
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
                print("✅ All essential tables exist!")
                return True
            else:
                print(f"❌ Missing tables: {', '.join(missing_tables)}")
                return False
    
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")
        return False

def run_fake_migrations():
    """Run migrations with --fake flag to mark them as applied without creating tables"""
    print("\n🔄 Running fake migrations...")
    
    try:
        # Run migrations with --fake flag
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate', '--fake'],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        print("✅ Fake migrations completed successfully!")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running fake migrations: {e}")
        print(e.stdout)
        print(e.stderr)
        return False

def run_sync_db():
    """Run syncdb to ensure all models have tables without running migrations"""
    print("\n🔄 Running syncdb...")
    
    try:
        # Use migrate --run-syncdb to create tables for models without migrations
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate', '--run-syncdb'],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        print("✅ Syncdb completed successfully!")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running syncdb: {e}")
        print(e.stdout)
        print(e.stderr)
        return False

def fix_migrations():
    """Complete fix for PostgreSQL migration issues"""
    print("\n🔧 PostgreSQL Migration Fix Tool 🔧")
    print("=================================")
    
    # First verify tables
    tables_ok = verify_essential_tables()
    
    # Fix migration history
    history_fixed = fix_django_migrations_table()
    
    # Run fake migrations
    if history_fixed:
        fake_ok = run_fake_migrations()
    else:
        fake_ok = False
    
    # As a final step, run syncdb
    if fake_ok:
        sync_ok = run_sync_db()
    else:
        sync_ok = False
    
    # Final check
    final_check = verify_essential_tables()
    
    return final_check

if __name__ == "__main__":
    success = fix_migrations()
    
    if success:
        print("\n✅ PostgreSQL migration fix completed successfully!")
        print("Your Django app should now work correctly.")
        print("Run your server with: python manage.py runserver")
    else:
        print("\n⚠️ Some issues were fixed, but additional problems might remain.")
        print("Try running your Django app and see if it works.")
