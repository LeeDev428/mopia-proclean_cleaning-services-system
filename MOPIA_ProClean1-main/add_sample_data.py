import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from core.models import Service

# Check if services already exist
if Service.objects.count() == 0:
    print("Adding sample services...")
    
    # Create sample services
    services = [
        {
            'name': 'Standard Home Cleaning',
            'description': 'Comprehensive cleaning of your home including dusting, vacuuming, mopping, bathroom and kitchen cleaning.',
            'price': 120.00
        },
        {
            'name': 'Deep Cleaning',
            'description': 'Thorough cleaning of your entire home including hard-to-reach areas, baseboards, cabinet exteriors, and appliances.',
            'price': 200.00
        },
        {
            'name': 'Move-In/Move-Out Cleaning',
            'description': 'Complete cleaning service to prepare a property for new occupants or to clean up after moving out.',
            'price': 250.00
        },
        {
            'name': 'Office Cleaning',
            'description': 'Professional cleaning for commercial office spaces, including desks, common areas, and bathrooms.',
            'price': 180.00
        },
        {
            'name': 'Post-Construction Cleaning',
            'description': 'Clean-up after construction or renovation projects to remove dust, debris, and construction residue.',
            'price': 300.00
        }
    ]
    
    # Save services to database
    for service_data in services:
        Service.objects.create(**service_data)
    
    print(f"Added {len(services)} services to the database!")
else:
    print("Services already exist in the database.")
