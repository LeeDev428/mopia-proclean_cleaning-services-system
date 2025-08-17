import os
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from django.db import connection
from core.models import Service

def fix_database():
    """Fix missing database tables and add sample data."""
    try:
        with connection.cursor() as cursor:
            # Create Service table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS core_service (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL,
                    price NUMERIC(10, 2) NOT NULL
                )
            """)
            
            # Create Customer table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS core_customer (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    address TEXT NOT NULL
                )
            """)
            
            # Create Booking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS core_booking (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    customer_id INTEGER NOT NULL,
                    service_id INTEGER NOT NULL,
                    FOREIGN KEY (customer_id) REFERENCES core_customer(id),
                    FOREIGN KEY (service_id) REFERENCES core_service(id)
                )
            """)
            
            # Check if column exists first to avoid errors
            cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name='core_booking' AND column_name='created_at'")
            if cursor.fetchone()[0] == 0:
                # Add the column if it doesn't exist
                cursor.execute("ALTER TABLE core_booking ADD COLUMN created_at timestamp with time zone DEFAULT NOW()")
                print("✅ Successfully added created_at column to core_booking table")
            else:
                print("✅ Column already exists, no changes needed")
        
        # Add sample services if the Service table is empty
        if Service.objects.count() == 0:
            Service.objects.bulk_create([
                Service(name='Standard Cleaning', description='Regular cleaning service for homes and small offices.', price=100.00),
                Service(name='Deep Cleaning', description='Thorough cleaning of all areas including hard-to-reach places.', price=200.00),
                Service(name='Office Cleaning', description='Professional cleaning for commercial spaces and offices.', price=150.00),
            ])
        
        print("✅ Database fixed successfully!")
    except Exception as e:
        print(f"❌ Error fixing database: {e}")

if __name__ == "__main__":
    fix_database()
