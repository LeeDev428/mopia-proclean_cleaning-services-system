#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from core.models import Booking, Customer, Service

# Test creating a booking with notes
try:
    customer = Customer.objects.first()
    service = Service.objects.first()
    
    if customer and service:
        # Create a test booking with notes
        booking = Booking.objects.create(
            customer=customer,
            service=service,
            date='2025-08-20',
            time='10:00:00',
            user_note='Test user note - May aso dito',
            admin_note='Test admin note - We will use your water supply',
            status='pending'
        )
        
        print(f"Created booking ID: {booking.id}")
        print(f"user_note: '{booking.user_note}'")
        print(f"admin_note: '{booking.admin_note}'")
        
        # Verify it was saved
        saved_booking = Booking.objects.get(id=booking.id)
        print(f"\nVerified from database:")
        print(f"user_note: '{saved_booking.user_note}'")
        print(f"admin_note: '{saved_booking.admin_note}'")
        
    else:
        print("No customer or service found in database")
        
except Exception as e:
    print(f"Error: {e}")
