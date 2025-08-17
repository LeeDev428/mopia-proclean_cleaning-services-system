import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.db import connection

def check_created_at_column():
    """Check if the created_at column exists in the core_booking table"""
    try:
        with connection.cursor() as cursor:
            # Check if the column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'core_booking' AND column_name = 'created_at'
                )
            """)
            column_exists = cursor.fetchone()[0]
            
            if column_exists:
                print("✅ 'created_at' column exists in core_booking table")
                
                # Count bookings with created_at values
                cursor.execute("SELECT COUNT(*) FROM core_booking WHERE created_at IS NOT NULL")
                count = cursor.fetchone()[0]
                
                # Get total bookings
                cursor.execute("SELECT COUNT(*) FROM core_booking")
                total = cursor.fetchone()[0]
                
                print(f"   {count} out of {total} bookings have 'created_at' values")
                
                if count < total:
                    print("\n⚠️ Some bookings are missing 'created_at' values!")
                    print("   Run the following to fix missing values:")
                    print("   python manage.py shell -c \"from django.utils import timezone; from core.models import Booking; Booking.objects.filter(created_at__isnull=True).update(created_at=timezone.now())\"")
            else:
                print("❌ 'created_at' column does not exist in core_booking table")
                print("   This might indicate that migrations were not applied correctly")
    except Exception as e:
        print(f"❌ Error checking 'created_at' column: {e}")

if __name__ == "__main__":
    check_created_at_column()
