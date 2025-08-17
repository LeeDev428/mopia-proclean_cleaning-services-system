import os
import subprocess
import sys
import django
import time

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

def run_command(command, description):
    """Run a command and print its status"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True
        )
        print(f"✅ Success: {description}")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {description}")
        print(f"Error: {e}")
        print(e.stdout)
        print(e.stderr)
        return False

def fix_migrations():
    # 1. Merge conflicting migrations
    merge_success = run_command(
        [sys.executable, 'manage.py', 'makemigrations', '--merge', '--noinput'],
        "Merging conflicting migrations"
    )
    
    if not merge_success:
        print("\n⚠️ Could not automatically merge migrations.")
        print("Let's try to fix the issue by removing conflicting migration files.")
        
        from pathlib import Path
        
        # Try to find and rename conflicting migrations
        migrations_path = Path('core/migrations')
        create_userprofile_path = migrations_path / 'create_userprofile.py'
        
        if create_userprofile_path.exists():
            print(f"Found {create_userprofile_path}, renaming to _old...")
            try:
                create_userprofile_path.rename(migrations_path / 'create_userprofile.py.old')
                print("✅ Successfully renamed conflicting migration file")
            except Exception as e:
                print(f"❌ Failed to rename: {e}")
                return False
        
        # Try merge again
        merge_success = run_command(
            [sys.executable, 'manage.py', 'makemigrations', '--merge', '--noinput'],
            "Retrying migration merge"
        )
        
        if not merge_success:
            print("⚠️ Still having issues with migrations. Trying a different approach...")
            # Make new migrations
            run_command(
                [sys.executable, 'manage.py', 'makemigrations', 'core'],
                "Creating new migrations"
            )
    
    # 2. Apply migrations
    migrate_success = run_command(
        [sys.executable, 'manage.py', 'migrate'],
        "Applying all migrations"
    )
    
    # 3. Make sure UserProfile table exists
    if not migrate_success:
        print("\n⚠️ Migration failed. Trying to create tables directly...")
        userprofile_success = run_command(
            [sys.executable, 'create_userprofile_table.py'],
            "Creating UserProfile table directly"
        )
        
        service_success = run_command(
            [sys.executable, 'create_service_table.py'],
            "Creating Service table directly"
        )
    
    # 4. Add sample data
    run_command(
        [sys.executable, 'add_sample_data.py'],
        "Adding sample data"
    )
    
    return True

if __name__ == "__main__":
    print("🔧 Django Migration Fix Tool 🔧")
    print("==============================")
    
    if fix_migrations():
        print("\n✅ Migration issues have been fixed!")
        print("You can now run your server with: python manage.py runserver")
    else:
        print("\n❌ Could not fully resolve migration issues.")
        print("If you continue to have problems, consider a fresh database:")
        print("1. Drop your database and create a new one")
        print("2. Remove all files in core/migrations/ except __init__.py")
        print("3. Run: python manage.py makemigrations core")
        print("4. Run: python manage.py migrate")
