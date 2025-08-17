import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile
from django.db import connection

def check_tables():
    print("Checking database tables...")
    
    # List all tables in the database
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
    
    print("\nAvailable tables in the database:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Check auth_user table
    try:
        users_count = User.objects.count()
        print(f"\nUsers count in auth_user table: {users_count}")
        if users_count > 0:
            print("\nSample users:")
            for user in User.objects.all()[:5]:  # Show up to 5 users
                print(f"- {user.username} (ID: {user.id}, Email: {user.email})")
        else:
            print("No users found in auth_user table.")
    except Exception as e:
        print(f"Error checking auth_user table: {e}")
    
    # Check core_userprofile table
    try:
        profiles_count = UserProfile.objects.count()
        print(f"\nProfiles count in core_userprofile table: {profiles_count}")
        if profiles_count > 0:
            print("\nSample profiles:")
            for profile in UserProfile.objects.all()[:5]:  # Show up to 5 profiles
                print(f"- User ID: {profile.user.id}, Username: {profile.user.username}, Is Admin: {profile.is_admin}")
        else:
            print("No profiles found in core_userprofile table.")
    except Exception as e:
        print(f"Error checking core_userprofile table: {e}")

if __name__ == "__main__":
    check_tables()
