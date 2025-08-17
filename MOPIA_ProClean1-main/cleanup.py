import os
import shutil

# Make a backup of migrations
migrations_dir = os.path.join('core', 'migrations')
backup_dir = os.path.join('core', 'migrations_backup')

# Create backup directory if it doesn't exist
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

# Backup existing migrations
for file in os.listdir(migrations_dir):
    if file.endswith('.py') and file != '__init__.py':
        shutil.copy(
            os.path.join(migrations_dir, file),
            os.path.join(backup_dir, file)
        )

print("Backup of migrations created in core/migrations_backup")
print("Remember to keep only __init__.py, 0001_initial.py, and the new merged migration file")

# Remove the manual SQL file if it exists
if os.path.exists('add_created_at.py'):
    os.rename('add_created_at.py', 'add_created_at.py.bak')
    print("Renamed add_created_at.py to add_created_at.py.bak")
