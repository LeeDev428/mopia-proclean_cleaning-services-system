import os
import django
import psycopg2

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.conf import settings

def create_service_table():
    """Create the Service table directly in PostgreSQL"""
    print("\n🔧 Creating Service Table 🔧")
    print("===========================")
    
    # Get database settings from Django
    db_settings = settings.DATABASES['default']
    db_name = db_settings['NAME']
    db_user = db_settings['USER']
    db_password = db_settings['PASSWORD']
    db_host = db_settings['HOST']
    db_port = db_settings['PORT']
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if the table already exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'core_service'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("Service table already exists. Skipping creation.")
            return True
            
        print("Creating core_service table...")
        
        # Create the Service table
        cursor.execute("""
            CREATE TABLE core_service (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                price NUMERIC(10, 2) NOT NULL
            );
        """)
        
        print("✅ core_service table created successfully!")
        
        # Add some sample services
        cursor.execute("""
            INSERT INTO core_service (name, description, price) VALUES
            ('Standard Home Cleaning', 'Comprehensive cleaning of your home including dusting, vacuuming, mopping, bathroom and kitchen cleaning.', 120.00),
            ('Deep Cleaning', 'Thorough cleaning of your entire home including hard-to-reach areas, baseboards, cabinet exteriors, and appliances.', 200.00),
            ('Office Cleaning', 'Professional cleaning for commercial office spaces, including desks, common areas, and bathrooms.', 180.00);
        """)
        
        print("✅ Sample services added!")
        
        # Add the migration record
        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES ('core', '0001_initial', NOW())
            ON CONFLICT DO NOTHING;
        """)
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating Service table: {e}")
        return False

if __name__ == "__main__":
    success = create_service_table()
    
    if success:
        print("\n✅ Service table created successfully!")
        print("You should now be able to see and book services.")
    else:
        print("\n❌ Failed to create Service table.")
