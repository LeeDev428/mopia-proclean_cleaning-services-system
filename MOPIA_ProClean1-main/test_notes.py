#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mopia.settings')
django.setup()

from core.models import Booking

# Check if note fields exist
print("Booking model fields:")
for field in Booking._meta.fields:
    print(f"- {field.name}: {field.__class__.__name__}")

# Check current data
bookings = Booking.objects.all()
print(f"\nTotal bookings: {bookings.count()}")

if bookings.exists():
    for booking in bookings[:3]:  # Show first 3 bookings
        print(f"\nBooking ID: {booking.id}")
        print(f"Customer: {booking.customer.name}")
        print(f"Service: {booking.service.name}")
        print(f"user_note: '{booking.user_note}' (type: {type(booking.user_note)})")
        print(f"admin_note: '{booking.admin_note}' (type: {type(booking.admin_note)})")
