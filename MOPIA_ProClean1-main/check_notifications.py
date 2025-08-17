import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User

def check_notifications():
    """Check notifications in the database and display their status"""
    try:
        with connection.cursor() as cursor:
            # Check if notification table exists
            cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'core_notification')")
            if not cursor.fetchone()[0]:
                print("❌ Notification table doesn't exist!")
                return
                
            # Count total notifications
            cursor.execute("SELECT COUNT(*) FROM core_notification")
            total_count = cursor.fetchone()[0]
            
            # Count unread notifications
            cursor.execute("SELECT COUNT(*) FROM core_notification WHERE is_read = FALSE")
            unread_count = cursor.fetchone()[0]
            
            print(f"✅ Notification table exists")
            print(f"   Total notifications: {total_count}")
            print(f"   Unread notifications: {unread_count}")
            
            # Get all users with notifications
            cursor.execute("""
                SELECT u.username, u.id, COUNT(*) 
                FROM auth_user u
                JOIN core_notification n ON u.id = n.user_id
                WHERE n.is_read = FALSE
                GROUP BY u.username, u.id
            """)
            
            user_notifications = cursor.fetchall()
            if user_notifications:
                print("\nUsers with unread notifications:")
                for username, user_id, count in user_notifications:
                    print(f"   {username}: {count} unread notifications")
                    
                    # Show notification details for first user
                    if user_id:
                        cursor.execute("""
                            SELECT id, message, created_at, booking_id 
                            FROM core_notification 
                            WHERE user_id = %s AND is_read = FALSE
                            LIMIT 3
                        """, [user_id])
                        
                        print(f"   Sample notifications for {username}:")
                        for row in cursor.fetchall():
                            notification_id, message, created_at, booking_id = row
                            print(f"      - ID: {notification_id}, Message: {message}, Created: {created_at}")
            else:
                print("\nNo users have unread notifications")
                
    except Exception as e:
        print(f"❌ Error checking notifications: {e}")

if __name__ == "__main__":
    check_notifications()
