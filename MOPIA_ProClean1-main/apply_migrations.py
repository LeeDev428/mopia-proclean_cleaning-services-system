import os
import django
import subprocess
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

def apply_migrations():
    print("Applying all migrations...")
    try:
        # First check for missing migrations
        print("Checking for missing migrations...")
        subprocess.run(
            [sys.executable, 'manage.py', 'makemigrations'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Run migrations using subprocess to ensure proper execution
        print("Running migrations for all apps...")
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate', '--run-syncdb'],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        # Specifically ensure django_session table exists
        print("Ensuring session table exists...")
        result = subprocess.run(
            [sys.executable, 'manage.py', 'migrate', 'sessions'],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        print("Migrations successfully applied!")
        
        # Create a superuser if it doesn't exist
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            print("\nCreating a superuser...")
            subprocess.run([sys.executable, 'manage.py', 'createsuperuser'])
    except subprocess.CalledProcessError as e:
        print(f"Error applying migrations: {e}")
        print(f"Error output: {e.stderr}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    apply_migrations()
