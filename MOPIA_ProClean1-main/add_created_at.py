import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.db import connection

# Add the column directly with SQL
with connection.cursor() as cursor:
    cursor.execute("ALTER TABLE core_booking ADD COLUMN created_at timestamp with time zone DEFAULT NOW()")
    
print("Successfully added created_at column to core_booking table")
