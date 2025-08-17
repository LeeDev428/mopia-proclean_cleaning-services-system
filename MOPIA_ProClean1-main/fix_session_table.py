import os
import django
import subprocess
import sys
from django.db import connection, DatabaseError, ProgrammingError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

def fix_session_table():
    print("Starting session table fix...")
    
    # First, try to run the migrations for the core Django applications
    try:
        print("Attempting to run migrations for auth and sessions apps...")
        subprocess.run(
            [sys.executable, 'manage.py', 'migrate', 'auth', '--verbosity=2'],
            capture_output=True,
            text=True,
            check=True
        )
        
        print("Running session migrations specifically...")
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate', 'sessions', '--verbosity=2'],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        # Verify table exists after migrations
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public'
                        AND table_name = 'django_session'
                    );
                """)
                table_exists = cursor.fetchone()[0]
                
                if table_exists:
                    print("✅ django_session table created successfully through migrations!")
                    return True
                else:
                    print("Migrations completed but table still not found. Trying SQL approach...")
        except Exception as e:
            print(f"Error checking table existence: {e}")
    
        # If migrations don't work, try creating the table directly with SQL
        try:
            print("Creating session table directly with SQL...")
            with connection.cursor() as cursor:
                # Drop table if it exists but is malformed
                try:
                    cursor.execute("DROP TABLE IF EXISTS django_session CASCADE;")
                except:
                    pass
                
                # Create the session table with standard schema
                cursor.execute("""
                    CREATE TABLE django_session (
                        session_key varchar(40) NOT NULL PRIMARY KEY,
                        session_data text NOT NULL,
                        expire_date timestamp with time zone NOT NULL
                    );
                """)
                
                # Create the index
                cursor.execute("""
                    CREATE INDEX django_session_expire_date_idx 
                    ON django_session (expire_date);
                """)
                
            print("✅ Session table created successfully via direct SQL!")
            return True
            
        except Exception as e:
            print(f"Error creating table with SQL: {e}")
            
    except Exception as e:
        print(f"Error running migrations: {e}")
    
    # If we get here, all attempts failed
    print("\n❌ All attempts to create the session table failed.")
    print("\nTroubleshooting steps:")
    print("1. Check PostgreSQL permissions - ensure your user has CREATE TABLE rights")
    print("2. Verify database connection settings in mopia/settings.py")
    print("3. Try running: python manage.py migrate --run-syncdb")
    print("4. Consider manually running SQL commands in your PostgreSQL client")
    
    print("\nAs a last resort, you could switch to SQLite temporarily:")
    print("""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
    """)
    
    return False

if __name__ == "__main__":
    success = fix_session_table()
    if success:
        print("\n✅ Session table fix completed successfully. Try accessing your application now.")
    else:
        print("\n❌ Session table fix was not successful. Follow the troubleshooting steps above.")
