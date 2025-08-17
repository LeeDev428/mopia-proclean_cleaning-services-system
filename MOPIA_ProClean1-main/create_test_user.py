import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile

def create_test_user():
    # Check if test user already exists
    if User.objects.filter(username='testuser').exists():
        print("Test user already exists.")
        return
    
    # Create a test user
    try:
        user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='password123'
        )
        user.first_name = 'Test'
        user.last_name = 'User'
        user.save()
        
        # Make sure the user has a profile
        if not hasattr(user, 'profile'):
            profile = UserProfile.objects.create(
                user=user,
                is_admin=False,
                phone='123-456-7890',
                address='123 Test Street'
            )
        else:
            user.profile.is_admin = False
            user.profile.phone = '123-456-7890'
            user.profile.address = '123 Test Street'
            user.profile.save()
        
        print(f"Test user created successfully: {user.username}")
        print(f"Profile created: {hasattr(user, 'profile')}")
    except Exception as e:
        print(f"Error creating test user: {e}")

if __name__ == "__main__":
    create_test_user()
