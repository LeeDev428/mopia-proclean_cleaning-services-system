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
    
    # User and Admin Notes
    user_note = models.TextField(blank=True, null=True, help_text="Customer's note for the service (e.g., 'May aso dito')")
    admin_note = models.TextField(blank=True, null=True, help_text="Admin's note about service requirements (e.g., 'We will use your water supply and electricity')")
    
    # Payment fields
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Payment reference number from GCash, PayMaya, etc.")
    downpayment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="40% downpayment amount")
    payment_method = models.CharField(max_length=50, blank=True, null=True, help_text="Payment method used (GCash, PayMaya, etc.)")
    is_downpayment_confirmed = models.BooleanField(default=False, help_text="Whether admin has verified the downpayment")
    is_full_payment_confirmed = models.BooleanField(default=False, help_text="Whether full payment has been confirmed by staff")
    
    # Photo fields for before and after service
    before_photo = models.ImageField(upload_to='photos/before/', blank=True, null=True, help_text="Photo taken before service starts")
    after_photo = models.ImageField(upload_to='photos/after/', blank=True, null=True, help_text="Photo taken after service completion")
    
    def __str__(self):
        return f"{self.customer.name} - {self.service.name} on {self.date} at {self.time}"
    
    def get_downpayment_amount(self):
        """Calculate 40% downpayment of service price"""
        return self.service.price * 0.4 if self.service else 0
    
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

class Feedback(models.Model):
    RATING_CHOICES = [
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='feedback')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='feedbacks')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='feedbacks')
    assigned_staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_feedbacks')
    
    # Rating fields
    overall_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Overall service rating")
    quality_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Quality of cleaning")
    punctuality_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Punctuality and timeliness")
    staff_behavior_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Staff behavior and professionalism")
    value_for_money_rating = models.IntegerField(choices=RATING_CHOICES, help_text="Value for money")
    
    # Text feedback
    positive_feedback = models.TextField(blank=True, null=True, help_text="What did you like about our service?")
    improvement_feedback = models.TextField(blank=True, null=True, help_text="What can we improve?")
    additional_comments = models.TextField(blank=True, null=True, help_text="Any additional comments")
    
    # Recommendation
    would_recommend = models.BooleanField(help_text="Would you recommend our service to others?")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False, help_text="Feature this feedback on website")
    admin_response = models.TextField(blank=True, null=True, help_text="Admin response to feedback")
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Feedback for {self.service.name} by {self.customer.name} - {self.overall_rating}/5"
    
    @property
    def average_rating(self):
        """Calculate average rating across all rating categories"""
        ratings = [
            self.overall_rating,
            self.quality_rating,
            self.punctuality_rating,
            self.staff_behavior_rating,
            self.value_for_money_rating
        ]
        return round(sum(ratings) / len(ratings), 1)
    
    @property
    def rating_category(self):
        """Get rating category based on average rating"""
        avg = self.average_rating
        if avg >= 4.5:
            return "Excellent"
        elif avg >= 4.0:
            return "Very Good"
        elif avg >= 3.5:
            return "Good"
        elif avg >= 3.0:
            return "Average"
        elif avg >= 2.0:
            return "Poor"
        else:
            return "Very Poor"
    
    @classmethod
    def get_service_analytics(cls, service_id=None):
        """Get analytics for service feedback"""
        queryset = cls.objects.all()
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        
        if not queryset.exists():
            return None
        
        total_feedbacks = queryset.count()
        avg_overall = queryset.aggregate(models.Avg('overall_rating'))['overall_rating__avg']
        avg_quality = queryset.aggregate(models.Avg('quality_rating'))['quality_rating__avg']
        avg_punctuality = queryset.aggregate(models.Avg('punctuality_rating'))['punctuality_rating__avg']
        avg_staff = queryset.aggregate(models.Avg('staff_behavior_rating'))['staff_behavior_rating__avg']
        avg_value = queryset.aggregate(models.Avg('value_for_money_rating'))['value_for_money_rating__avg']
        
        recommendations = queryset.filter(would_recommend=True).count()
        recommendation_rate = (recommendations / total_feedbacks) * 100 if total_feedbacks > 0 else 0
        
        # Rating distribution
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[i] = queryset.filter(overall_rating=i).count()
        
        return {
            'total_feedbacks': total_feedbacks,
            'average_ratings': {
                'overall': round(avg_overall, 1) if avg_overall else 0,
                'quality': round(avg_quality, 1) if avg_quality else 0,
                'punctuality': round(avg_punctuality, 1) if avg_punctuality else 0,
                'staff_behavior': round(avg_staff, 1) if avg_staff else 0,
                'value_for_money': round(avg_value, 1) if avg_value else 0,
            },
            'recommendation_rate': round(recommendation_rate, 1),
            'rating_distribution': rating_distribution,
        }


# Inventory Management Models
class InventoryCategory(models.Model):
    CATEGORY_CHOICES = [
        ('cleaning_agents', 'Cleaning Agents'),
        ('tools', 'Tools'),
        ('equipment', 'Equipment'),
    ]
    
    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Inventory Categories"
    
    def __str__(self):
        return self.get_name_display()


class InventoryItem(models.Model):
    category = models.ForeignKey(InventoryCategory, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=20, help_text="e.g., pieces, liters, kg")
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_disposable = models.BooleanField(default=False, help_text="True for cleaning agents, False for tools/equipment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('category', 'name')
    
    def __str__(self):
        return f"{self.name} ({self.category.get_name_display()})"
    
    @property
    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock
    
    @property
    def stock_value(self):
        return self.current_stock * self.unit_cost


class BookingInventory(models.Model):
    """Items allocated/used for a specific booking"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='inventory_usage')
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity_allocated = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_used = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity_returned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_returned = models.BooleanField(default=False, help_text="For non-disposable items only")
    notes = models.TextField(blank=True, null=True)
    allocated_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(blank=True, null=True)
    returned_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Booking #{self.booking.id} - {self.item.name} ({self.quantity_allocated} {self.item.unit})"
    
    @property
    def quantity_lost_or_damaged(self):
        """Calculate items that were not returned (for non-disposables)"""
        if self.item.is_disposable:
            return 0
        return self.quantity_allocated - self.quantity_returned
    
    def save(self, *args, **kwargs):
        # Auto-update inventory stock when items are used
        if self.pk:  # If updating existing record
            old_record = BookingInventory.objects.get(pk=self.pk)
            stock_change = old_record.quantity_used - self.quantity_used
        else:  # If creating new record
            stock_change = -self.quantity_used
        
        # Update inventory stock
        if stock_change != 0:
            self.item.current_stock += stock_change
            self.item.save()
        
        super().save(*args, **kwargs)


class InventoryTransaction(models.Model):
    """Track all inventory movements (stock in, stock out, adjustments)"""
    TRANSACTION_TYPES = [
        ('stock_in', 'Stock In'),
        ('stock_out', 'Stock Out'),
        ('adjustment', 'Stock Adjustment'),
        ('booking_use', 'Used in Booking'),
        ('booking_return', 'Returned from Booking'),
    ]
    
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.item.name} ({self.quantity} {self.item.unit})"
