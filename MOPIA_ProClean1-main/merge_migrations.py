import os
import sys
import subprocess

def run_command(cmd, description):
    """Run a command and return whether it was successful"""
    print(f"Running: {description}...")
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} completed successfully")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with error code {e.returncode}")
        print(f"Error: {e.stderr}")
        return False

def merge_migrations():
    """Merge conflicting migrations and apply them"""
    print("\n🔄 Migration Conflict Resolution Tool 🔄")
    print("======================================")
    
    # Backup migrations folder before proceeding
    print("\n📦 Creating backup of current migrations...")
    migrations_dir = os.path.join('core', 'migrations')
    backup_dir = os.path.join('core', 'migrations_backup')
    
    # Create backup directory if it doesn't exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Backup existing migrations
    for file in os.listdir(migrations_dir):
        if file.endswith('.py') and file != '__init__.py':
            subprocess.run([
                "cp", 
                os.path.join(migrations_dir, file),
                os.path.join(backup_dir, file)
            ], shell=True)
    
    print("✅ Migrations backed up to core/migrations_backup")
    
    # 1. Merge the conflicting migrations
    merge_success = run_command(
        [sys.executable, "manage.py", "makemigrations", "--merge", "--no-input"],
        "Merging conflicting migrations"
    )
    
    if not merge_success:
        return False
    
    # 2. Apply the merged migrations
    migrate_success = run_command(
        [sys.executable, "manage.py", "migrate"],
        "Applying migrations"
    )
    
    return migrate_success

if __name__ == "__main__":
    success = merge_migrations()
    
    if success:
        print("\n✅ Migration conflicts have been successfully resolved!")
        print("Your database schema should now be up to date.")
        
        # Check for created_at column
        print("\nVerifying 'created_at' column in Booking model...")
        try:
            check_result = subprocess.run(
                [sys.executable, "check_created_at_column.py"],
                capture_output=True,
                text=True
            )
            print(check_result.stdout)
        except:
            print("⚠️ Could not verify 'created_at' column. Run check_created_at_column.py manually.")
    else:
        print("\n❌ Migration could not be completed due to errors.")
        print("You may need to resolve conflicts manually:")
        print("1. Remove all migrations except __init__.py from core/migrations/")
        print("2. Run: python manage.py makemigrations core")
        print("3. Run: python manage.py migrate --fake core zero")
        print("4. Run: python manage.py migrate core")
