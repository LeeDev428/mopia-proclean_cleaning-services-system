import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.db import connection

def create_notification_table():
    """Create the notification table if it doesn't exist"""
    print("Creating notification table...")
    
    try:
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'core_notification')")
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Create the notification table with all required fields
                cursor.execute("""
                CREATE TABLE core_notification (
                    id SERIAL PRIMARY KEY,
                    message TEXT NOT NULL,
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    booking_id INTEGER REFERENCES core_booking(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES auth_user(id) ON DELETE CASCADE
                )
                """)
                print("✅ Notification table created successfully!")
            else:
                print("✅ Notification table already exists")
                
            # Add some test notifications if none exist
            cursor.execute("SELECT COUNT(*) FROM core_notification")
            notification_count = cursor.fetchone()[0]
            
            if notification_count == 0:
                print("Adding test notifications...")
                # Get first user
                cursor.execute("SELECT id FROM auth_user LIMIT 1")
                user_id = cursor.fetchone()[0]
                
                if user_id:
                    cursor.execute("""
                    INSERT INTO core_notification (message, is_read, created_at, user_id)
                    VALUES 
                        ('Your booking has been confirmed!', FALSE, NOW(), %s),
                        ('Your booking has been completed!', FALSE, NOW(), %s)
                    """, [user_id, user_id])
                    print(f"✅ Test notifications added for user ID {user_id}")
    except Exception as e:
        print(f"❌ Error managing notification table: {e}")

if __name__ == "__main__":
    create_notification_table()
