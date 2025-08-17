import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User

def create_test_notification(username):
    """Create a test notification for a user"""
    try:
        # Find the user
        user = User.objects.get(username=username)
        
        # Check if notification table exists
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'core_notification')")
            if not cursor.fetchone()[0]:
                print("❌ Notification table doesn't exist! Run create_notification_table.py first.")
                return
                
            # Insert a test notification
            cursor.execute("""
                INSERT INTO core_notification (message, is_read, created_at, user_id)
                VALUES (%s, FALSE, NOW(), %s)
            """, ["This is a test notification", user.id])
            
            # Count current notifications
            cursor.execute("""
                SELECT COUNT(*) FROM core_notification 
                WHERE user_id = %s AND is_read = FALSE
            """, [user.id])
            count = cursor.fetchone()[0]
            
        print(f"✅ Test notification created for {username}")
        print(f"   Current unread notifications: {count}")
    except User.DoesNotExist:
        print(f"❌ User '{username}' not found")
    except Exception as e:
        print(f"❌ Error creating notification: {e}")

if __name__ == "__main__":
    username = input("Enter username to create notification for: ")
    create_test_notification(username)
