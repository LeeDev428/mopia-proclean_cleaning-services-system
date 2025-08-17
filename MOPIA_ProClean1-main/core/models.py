from django.db import models
from django.contrib.auth.models import User

class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    duration = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. '2 hours', '4-6 hours'")
    materials = models.TextField(blank=True, null=True, help_text="Materials and equipment to be used")
    staff_count = models.IntegerField(default=1, help_text="Expected number of staff")
    is_archived = models.BooleanField(default=False)  # New field
    
    def __str__(self):
        return self.name

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='customer')
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=False, null=False)  # Required for customers
    address = models.TextField(blank=False, null=False)  # Required for customers
    
    def __str__(self):
        return self.name
class StaffService(models.Model):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    service = models.ForeignKey('Service', on_delete=models.CASCADE, related_name='staff_members')
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('staff', 'service')
        
    def __str__(self):
        return f"{self.staff.username} - {self.service.name}"
        
    def save(self, *args, **kwargs):
        # If this is marked as primary, unmark other primary services for this staff
        if self.is_primary:
            StaffService.objects.filter(
                staff=self.staff,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

class Booking(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    decline_reason = models.TextField(blank=True, null=True)
    assigned_staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_bookings')
    status_choices = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # New fields for staff functionality
    assigned_staff = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                      null=True, blank=True, 
                                      related_name='assigned_bookings',
                                      limit_choices_to={'is_staff': True})
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.customer.name} - {self.service.name} on {self.date} at {self.time}"
    
    def get_duration(self):
        """Calculate the duration of work in hours"""
        if self.clock_in and self.clock_out:
            duration = self.clock_out - self.clock_in
            hours = duration.total_seconds() / 3600
            return round(hours, 2)
        return None

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:30]}..."

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_admin = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True, default='')  # Default to empty string, not None
    address = models.TextField(blank=True, default='')  # Default to empty string, not None
    is_email_verified = models.BooleanField(default=False)  # New field for email verification
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)  # Token for verification
    token_expiry = models.DateTimeField(null=True, blank=True)  # Token expiration time
    
    def __str__(self):
        return self.user.username
