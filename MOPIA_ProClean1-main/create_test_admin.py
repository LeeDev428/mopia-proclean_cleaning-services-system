import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile

def create_test_admin():
    # Check if admin user already exists
    if User.objects.filter(username='admin').exists():
        print("Admin user already exists.")
        # Make sure user has admin privileges
        admin_user = User.objects.get(username='admin')
        if hasattr(admin_user, 'profile'):
            admin_user.profile.is_admin = True
            admin_user.profile.save()
            print("Ensured admin privileges are set.")
        return
    
    # Create an admin user
    try:
        user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        user.first_name = 'Admin'
        user.last_name = 'User'
        user.is_staff = True  # Can access admin site
        user.is_superuser = True  # Has all permissions
        user.save()
        
        # Make sure the user has a profile with admin flag
        if not hasattr(user, 'profile'):
            profile = UserProfile.objects.create(
                user=user,
                is_admin=True,
                phone='123-456-7890',
                address='123 Admin Street'
            )
        else:
            user.profile.is_admin = True
            user.profile.phone = '123-456-7890'
            user.profile.address = '123 Admin Street'
            user.profile.save()
        
        print(f"Admin user created successfully: {user.username}")
        print(f"Profile created: {hasattr(user, 'profile')}")
    except Exception as e:
        print(f"Error creating admin user: {e}")

if __name__ == "__main__":
    create_test_admin()
