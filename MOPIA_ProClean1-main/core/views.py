from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.utils import OperationalError, ProgrammingError, IntegrityError
from django.db import connection  # Add this import for database connection
from django.db.models import Count, Sum, Q, Avg  # Add analytics imports
from .models import Service, Customer, Booking, UserProfile, Notification
from .forms import RegistrationForm, LoginForm
from django.contrib.auth.models import User  # Add this import at the top with other imports
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from decimal import Decimal  # Add this import for decimal calculations
import json
import secrets
# import datetime
from django.core.mail import send_mail
from django.utils import timezone
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.models import User
from .models import StaffService, Service
from datetime import datetime, timedelta
from django.db import transaction  # Add this import at the top

def check_table_exists(model_class):
    """Check if a database table exists for a given model"""
    try:
        # Try a simple query that will fail if the table doesn't exist
        model_class.objects.first()
        return True
    except (ProgrammingError, OperationalError):
        return False

def home(request):
    # Add session error handling to prevent crashes
    try:
        # Check if we're in a session error state
        session_error = False
        try:
            # Try to access the session
            request.session.accessed
        except (OperationalError, ProgrammingError):
            # Session table issues
            session_error = True
        
        # Set a context variable with auth status
        auth_status = False if session_error else request.user.is_authenticated
        
        return render(request, 'home.html', {'auth_status': auth_status})
    except Exception as e:
        # Fall back to a basic render if there are still issues
        return render(request, 'home.html', {'auth_status': False})

def services(request):
    # Check if Service table exists
    if not check_table_exists(Service):
        messages.error(
            request, 
            "Database setup incomplete: Service table missing. Please run the following command: "
            "python fix_migrations.py"
        )
        # Return a simplified version of the services page without database queries
        return render(request, 'services.html', {'services': [], 'db_ready': False})
    
    try:
        services_list = Service.objects.all()
        return render(request, 'services.html', {'services': services_list, 'db_ready': True})
    except Exception as e:
        messages.error(request, f"Database error: {str(e)}. Please run migrations.")
        return render(request, 'services.html', {'services': [], 'db_ready': False})

def booking(request):
    # Check if Service table exists
    if not check_table_exists(Service):
        # Create a minimal set of services directly if table doesn't exist
        try:
            # This is a last resort to provide some functionality even without the table
            # It won't persist but will help temporarily
            mock_services = [
                {'id': 1, 'name': 'Standard Cleaning', 'price': 120.00},
                {'id': 2, 'name': 'Deep Cleaning', 'price': 200.00},
                {'id': 3, 'name': 'Office Cleaning', 'price': 180.00}
            ]
            return render(request, 'booking.html', {'services': mock_services, 'db_ready': True})
        except Exception:
            # If even that fails, show the page without services
            messages.error(request, "Unable to load services. Please try again later.")
            return render(request, 'booking.html', {'services': [], 'db_ready': False})
    
    try:
        services = Service.objects.all()
        return render(request, 'booking.html', {'services': services, 'db_ready': True})
    except Exception as e:
        messages.error(request, "Unable to load services. Please try again later.")
        return render(request, 'booking.html', {'services': [], 'db_ready': False})

def contact(request):
    return render(request, 'contact.html')

@require_POST
def booking_submit(request):
    """Submit a booking and associate it with the current user if authenticated"""
    # Get all required fields
    service_id = request.POST.get('service')
    date = request.POST.get('date')
    time = request.POST.get('time')
    name = request.POST.get('name')
    email = request.POST.get('email')
    phone = request.POST.get('phone')
    address = request.POST.get('address')
    user_note = request.POST.get('user_note', '')  # Get user note (optional)
    
    # Get payment fields
    payment_method = request.POST.get('payment_method')
    reference_number = request.POST.get('reference_number')
    
    # Validate all required fields are present
    if not all([service_id, date, time, name, email, phone, address, payment_method, reference_number]):
        if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded' or 'multipart/form-data' in request.headers.get('Content-Type', ''):
            # AJAX request - return JSON error
            return JsonResponse({'success': False, 'error': 'All fields including payment information are required.'}, status=400)
        else:
            messages.error(request, "All fields including payment information are required.")
            return redirect('booking')
    
    try:
        # Get service to calculate downpayment
        service = Service.objects.get(id=service_id)
        downpayment_amount = service.price * Decimal('0.4')  # Calculate 40% downpayment using Decimal
        
        # Create or update customer
        customer, created = Customer.objects.get_or_create(
            email=email,
            defaults={
                'name': name,
                'phone': phone,
                'address': address,
                'user': request.user if request.user.is_authenticated else None
            }
        )
        
        if not created:
            customer.name = name
            customer.phone = phone
            customer.address = address
            customer.save()
            
        # Create the booking with user note and payment information
        booking = Booking.objects.create(
            customer=customer,
            service=service,
            date=date,
            time=time,
            user_note=user_note,  # Save user note
            payment_method=payment_method,  # Save payment method
            reference_number=reference_number,  # Save reference number
            downpayment_amount=downpayment_amount,  # Save calculated downpayment
            is_downpayment_confirmed=False,  # Requires admin verification
            status='pending'  # Still pending until payment is verified
        )
        
        # AUTO-ASSIGN STAFF based on service expertise
        # First try to find staff with this as primary service
        primary_staff_service = StaffService.objects.filter(
            service=service,
            is_primary=True
        ).select_related('staff').first()
        
        if primary_staff_service:
            # Assign to staff who has this as primary service
            booking.assigned_staff = primary_staff_service.staff
            booking.save()
            print(f"Booking #{booking.id} auto-assigned to primary staff: {primary_staff_service.staff.get_full_name()}")
        else:
            # No primary staff, try any qualified staff
            any_qualified_staff_service = StaffService.objects.filter(
                service=service
            ).select_related('staff').first()
            
            if any_qualified_staff_service:
                booking.assigned_staff = any_qualified_staff_service.staff
                booking.save()
                print(f"Booking #{booking.id} auto-assigned to qualified staff: {any_qualified_staff_service.staff.get_full_name()}")
            else:
                print(f"No qualified staff found for service {service.name} (ID: {service.id})")
        
        # Create notification for user if authenticated
        if request.user.is_authenticated:
            try:
                notification = Notification.objects.create(
                    user=request.user,
                    booking=booking,
                    message=f"Your booking for {service.name} has been submitted and is pending confirmation.",
                    is_read=False
                )
            except Exception as e:
                print(f"Error creating notification: {str(e)}")
        
        # Check if this is an AJAX request (from user dashboard)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'multipart/form-data' in request.headers.get('Content-Type', ''):
            return JsonResponse({
                'success': True, 
                'booking_id': booking.id,
                'message': 'Your booking has been submitted successfully!'
            })
        else:
            messages.success(request, "Your booking has been submitted successfully!")
            return redirect('booking_confirmation', booking_id=booking.id)
    
    except Exception as e:
        error_msg = f"Error processing booking: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'multipart/form-data' in request.headers.get('Content-Type', ''):
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
        else:
            messages.error(request, error_msg)
            return redirect('booking')

def booking_confirmation(request, booking_id):
    booking = Booking.objects.get(id=booking_id)
    return render(request, 'booking_confirmation.html', {'booking': booking})

def available_slots(request):
    # This would be replaced with actual availability data
    # In a real app, you'd query your bookings and determine available slots
    events = [
        {
            'title': 'Available',
            'start': '2023-10-01T10:00:00',
            'end': '2023-10-01T16:00:00',
            'color': '#28a745'
        },
        {
            'title': 'Available',
            'start': '2023-10-03T09:00:00',
            'end': '2023-10-03T17:00:00',
            'color': '#28a745'
        }
    ]
    return JsonResponse(events, safe=False)

def user_login(request):
    # Check for UserProfile table existence first to avoid errors later
    try:
        # Try a simple query to test if the table exists
        UserProfile.objects.first()
    except (ProgrammingError, OperationalError):
        # UserProfile table doesn't exist
        messages.error(
            request, 
            "Database setup incomplete: UserProfile table missing. Please run migrations."
        )
        # Continue with login but won't try to access profiles
        
    if request.user.is_authenticated:
        # Check if the user has a profile safely
        try:
            is_admin = hasattr(request.user, 'profile') and request.user.profile.is_admin
            if is_admin:
                return redirect('admin_dashboard')
            elif request.user.is_staff:  # Check if user is staff
                return redirect('staff_dashboard')
            else:
                return redirect('user_dashboard')
        except (ProgrammingError, OperationalError):
            # If there's a database error with profile, just go to home
            messages.error(request, "Database error: UserProfile table not found.")
            return redirect('home')
        
    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Check if email is verified
                try:
                    profile = UserProfile.objects.get(user=user)
                    if not profile.is_email_verified:
                        messages.error(request, "Please verify your email before logging in.")
                        return render(request, 'login.html', {
                            'form': form, 
                            'needs_verification': True,
                            'user_email': user.email
                        })
                except (UserProfile.DoesNotExist, OperationalError, ProgrammingError):
                    # If profile doesn't exist, allow login (handle migration cases)
                    pass
                    
                # Continue with normal login if verified
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                
                # Redirect based on user type - safely check for profile
                try:
                    is_admin = hasattr(user, 'profile') and user.profile.is_admin
                    if is_admin:
                        return redirect('admin_dashboard')
                    elif user.is_staff:  # Check if user is staff
                        return redirect('staff_dashboard')
                    else:
                        return redirect('user_dashboard')
                except (ProgrammingError, OperationalError):
                    # If there's a database error, just go to home
                    return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})

def user_register(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
        
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Set user to inactive initially until email is verified
                user = form.save(commit=False)
                user.email = form.cleaned_data['email']
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.is_active = False  # Deactivate until verification
                user.save()
                
                # Get profile data
                phone = form.cleaned_data.get('phone', '')
                address = form.cleaned_data.get('address', '')
                
                # Try to create profile, but handle case where table doesn't exist
                try:
                    # Generate verification token and expiry time (24 hours from now)
                    token = secrets.token_urlsafe(32)
                    expiry = timezone.now() + timedelta(hours=24)
                    
                    # Use get_or_create to avoid duplicate profiles
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'is_admin': False,
                            'phone': phone,
                            'address': address,
                            'is_email_verified': False,
                            'email_verification_token': token,
                            'token_expiry': expiry
                        }
                    )
                    
                    # If the profile already existed but wasn't created now, update it
                    if not created:
                        profile.phone = phone
                        profile.address = address
                        profile.is_email_verified = False
                        profile.email_verification_token = token
                        profile.token_expiry = expiry
                        profile.save()
                        
                    # Send verification email
                    send_verification_email(request, user, token)
                        
                except IntegrityError:
                    # Profile already exists (likely created by signal)
                    try:
                        profile = UserProfile.objects.get(user=user)
                        profile.phone = phone
                        profile.address = address
                        profile.is_email_verified = False
                        profile.email_verification_token = secrets.token_urlsafe(32)
                        profile.token_expiry = timezone.now() + timedelta(hours=24)
                        profile.save()
                        
                        # Send verification email
                        send_verification_email(request, user, profile.email_verification_token)
                        
                    except Exception as e:
                        print(f"Error updating profile: {str(e)}")
                        
                except (ProgrammingError, OperationalError) as e:
                    # If profile table doesn't exist, just continue without it
                    messages.warning(request, "User created, but profile could not be saved due to database maintenance.")
                    
                messages.success(request, f"Account created for {user.username}. Please check your email to verify your account.")
                return redirect('verify_email_sent')
            except Exception as e:
                messages.error(request, f"Error creating user: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegistrationForm()
    
    return render(request, 'register.html', {'form': form})

def send_verification_email(request, user, token):
    """Send an email with verification link to the user"""
    verification_link = request.build_absolute_uri(
        reverse('verify_email', kwargs={'token': token})
    )
    
    subject = 'Verify your email for Mopia Cleaning Services'
    html_message = render_to_string('email/verify_email.html', {
        'user': user,
        'verification_link': verification_link,
    })
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            'noreply@mopiacleaning.com',  # From email
            [user.email],  # To email
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")

def verify_email(request, token):
    """Verify email using the token"""
    try:
        # Find profile with matching token
        profile = UserProfile.objects.get(email_verification_token=token)
        
        # Check if token has expired
        if profile.token_expiry and profile.token_expiry < timezone.now():
            messages.error(request, "Verification link has expired. Please request a new one.")
            return redirect('login')
            
        # Update verification status
        profile.is_email_verified = True
        profile.email_verification_token = None  # Clear token after use
        profile.token_expiry = None
        profile.save()
        
        # Activate the user
        user = profile.user
        user.is_active = True
        user.save()
        
        messages.success(request, "Email verified successfully! You can now log in.")
        return redirect('login')
        
    except UserProfile.DoesNotExist:
        messages.error(request, "Invalid verification link.")
        return redirect('login')
    except Exception as e:
        messages.error(request, f"Error verifying email: {str(e)}")
        return redirect('login')

def verify_email_sent(request):
    """Show a page confirming verification email was sent"""
    return render(request, 'verify_email_sent.html')

def resend_verification(request):
    """Resend verification email"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            profile = UserProfile.objects.get(user=user)
            
            # Generate new token and expiry
            token = secrets.token_urlsafe(32)
            expiry = timezone.now() + timedelta(hours=24)
            
            profile.email_verification_token = token
            profile.token_expiry = expiry
            profile.save()
            
            # Send new verification email
            send_verification_email(request, user, token)
            
            messages.success(request, "Verification email sent. Please check your inbox.")
            
        except (User.DoesNotExist, UserProfile.DoesNotExist):
            # Don't reveal if email exists for security
            messages.success(request, "If your email is registered, a verification link will be sent.")
            
        except Exception as e:
            messages.error(request, f"Error sending verification email: {str(e)}")
            
    return redirect('login')

def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

@login_required
def user_dashboard(request):
    """User dashboard view"""
    from django.db import connection
    
    # Check if necessary tables exist
    booking_table_exists = check_table_exists(Booking)
    profile_table_exists = check_table_exists(UserProfile)
    
    # Check if notification table exists
    notification_table_exists = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'core_notification')")
            notification_table_exists = cursor.fetchone()[0]
    except Exception:
        notification_table_exists = False
    
    # Store the migration status in session for admin use only
    if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_admin):
        if not booking_table_exists or not profile_table_exists or not notification_table_exists:
            messages.warning(
                request, 
                "Some database tables are missing. Please run: python create_notification_table.py"
            )
    
    # Safely check if user is admin only if profile table exists
    if profile_table_exists:
        try:
            is_admin = hasattr(request.user, 'profile') and request.user.profile.is_admin
            if is_admin:
                return redirect('admin_dashboard')
        except (ProgrammingError, OperationalError):
            # Fallback if query fails
            pass
    
    # Get user's bookings only if booking table exists
    bookings = []
    notifications = []
    notifications_count = 0
    
    if booking_table_exists:
        try:
            # Get bookings ordered by date and time
            bookings = Booking.objects.filter(customer__email=request.user.email).order_by('-date', '-time')
            
            # Get notifications with more reliable approach
            try:
                with connection.cursor() as cursor:
                    # Check if table exists
                    cursor.execute("SELECT to_regclass('public.core_notification')")
                    table_exists = cursor.fetchone()[0]
                    
                    if table_exists:
                        # Count unread notifications
                        cursor.execute("""
                            SELECT COUNT(*) 
                            FROM core_notification 
                            WHERE user_id = %s AND is_read = FALSE
                        """, [request.user.id])
                        notifications_count = cursor.fetchone()[0]
                        
                        # Get all notifications
                        cursor.execute("""
                            SELECT n.id, n.message, n.created_at, n.is_read, n.booking_id, 
                                   COALESCE(s.name, 'Service') as service_name
                            FROM core_notification n
                            LEFT JOIN core_booking b ON n.booking_id = b.id
                            LEFT JOIN core_service s ON b.service_id = s.id
                            WHERE n.user_id = %s
                            ORDER BY n.created_at DESC
                            LIMIT 10
                        """, [request.user.id])
                        
                        for row in cursor.fetchall():
                            notifications.append({
                                'id': row[0],
                                'message': row[1],
                                'created_at': row[2],
                                'is_read': row[3],
                                'service_name': row[5]
                            })
                
                # Log debug info
                print(f"Dashboard load: User {request.user.id} has {notifications_count} unread notifications")
                
            except Exception as e:
                print(f"Error loading notifications in dashboard: {str(e)}")
                # Continue with empty notifications rather than failing
            
        except Exception as e:
            print(f"Error in dashboard: {str(e)}")
            # Don't show technical errors to regular users
            if request.user.is_superuser:
                messages.warning(request, f"Could not load your bookings: {str(e)}")
    
    # Get all services to populate the dropdown
    services = Service.objects.all()
                
    return render(request, 'user_dashboard.html', {
        'bookings': bookings,
        'user': request.user,
        'services': services,
        'notifications': notifications,
        'notifications_count': notifications_count,
        'db_ready': booking_table_exists and profile_table_exists
    })

@login_required
def admin_dashboard(request):
    """Admin dashboard overview with comprehensive analytics."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
        
    try:
        # Check if created_at column exists
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='core_booking' AND column_name='created_at')")
            created_at_exists = cursor.fetchone()[0]
        
        # Get current date and time
        now = timezone.now()
        
        # Basic stats
        total_bookings = Booking.objects.all().count()
        pending_bookings = Booking.objects.filter(status='pending').count()
        completed_bookings = Booking.objects.filter(status='completed').count()
        
        # Time-based analytics
        # This Year
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        if created_at_exists:
            bookings_this_year = Booking.objects.filter(created_at__gte=year_start).count()
        else:
            bookings_this_year = Booking.objects.filter(date__gte=year_start.date()).count()
        
        # This Month
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if created_at_exists:
            bookings_this_month = Booking.objects.filter(created_at__gte=month_start).count()
        else:
            bookings_this_month = Booking.objects.filter(date__gte=month_start.date()).count()
        
        # This Week
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        if created_at_exists:
            bookings_this_week = Booking.objects.filter(created_at__gte=week_start).count()
        else:
            bookings_this_week = Booking.objects.filter(date__gte=week_start.date()).count()
        
        # Monthly breakdown for the current year
        monthly_bookings = []
        for month in range(1, 13):
            month_start = now.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
            if month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month + 1)
            
            if created_at_exists:
                month_count = Booking.objects.filter(
                    created_at__gte=month_start, 
                    created_at__lt=month_end
                ).count()
            else:
                month_count = Booking.objects.filter(
                    date__gte=month_start.date(), 
                    date__lt=month_end.date()
                ).count()
            monthly_bookings.append(month_count)
        
        # Quarterly breakdown
        quarterly_bookings = []
        for quarter in range(4):
            q_start_month = quarter * 3 + 1
            quarter_start = now.replace(month=q_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            if quarter == 3:  # Q4
                quarter_end = quarter_start.replace(year=quarter_start.year + 1, month=1)
            else:
                quarter_end = quarter_start.replace(month=q_start_month + 3)
            
            if created_at_exists:
                quarter_count = Booking.objects.filter(
                    created_at__gte=quarter_start,
                    created_at__lt=quarter_end
                ).count()
            else:
                quarter_count = Booking.objects.filter(
                    date__gte=quarter_start.date(),
                    date__lt=quarter_end.date()
                ).count()
            quarterly_bookings.append(quarter_count)
        
        # Service popularity analytics
        service_bookings = Booking.objects.values('service__name').annotate(
            booking_count=Count('id')
        ).order_by('-booking_count')
        
        # Location analytics - Using address field instead of city/barangay
        # Extract location data from address field
        location_bookings = Booking.objects.values('customer__address').annotate(
            booking_count=Count('id')
        ).order_by('-booking_count')
        
        # For city analytics, we'll group by customer for now since city field doesn't exist
        customer_bookings = Booking.objects.values('customer__name', 'customer__address').annotate(
            booking_count=Count('id')
        ).order_by('-booking_count')
        
        # Staff performance analytics
        staff_bookings = Booking.objects.filter(assigned_staff__isnull=False).values(
            'assigned_staff__first_name', 'assigned_staff__last_name', 'assigned_staff__username'
        ).annotate(
            booking_count=Count('id')
        ).order_by('-booking_count')
        
        # Revenue analytics (if service has price field)
        try:
            monthly_revenue = Booking.objects.filter(
                status='completed',
                **({
                    'created_at__month': now.month, 
                    'created_at__year': now.year
                } if created_at_exists else {
                    'date__month': now.month, 
                    'date__year': now.year
                })
            ).aggregate(total=Sum('service__price'))['total'] or 0
        except:
            monthly_revenue = 0
        
        # Get recent bookings for display
        if created_at_exists:
            bookings = Booking.objects.filter(status='pending').order_by('-created_at')
        else:
            bookings = Booking.objects.filter(status='pending').order_by('-date', '-time')
        
        # Pagination for recent bookings
        paginator = Paginator(bookings, 10)  # Show 10 bookings per page
        page_number = request.GET.get('page')
        recent_bookings = paginator.get_page(page_number)
            
        customers = Customer.objects.all()
        services = Service.objects.all()

        return render(request, 'admin/admin_dashboard.html', {
            'recent_bookings': recent_bookings,
            'customers': customers,
            'services': services,
            'total_bookings': total_bookings,
            'pending_bookings': pending_bookings,
            'completed_bookings': completed_bookings,
            'created_at_exists': created_at_exists,
            # Analytics data
            'bookings_this_year': bookings_this_year,
            'bookings_this_month': bookings_this_month,
            'bookings_this_week': bookings_this_week,
            'monthly_bookings': monthly_bookings,
            'quarterly_bookings': quarterly_bookings,
            'service_bookings': service_bookings,
            'location_bookings': location_bookings,
            'customer_bookings': customer_bookings,
            'staff_bookings': staff_bookings,
            'monthly_revenue': monthly_revenue,
        })
    except Exception as e:
        # Print error for debugging
        print(f"Dashboard Error: {str(e)}")
        messages.error(request, f"Database error: {str(e)}. Please run migrations to update the database schema.")
        
        return render(request, 'admin/admin_dashboard.html', {
            'bookings': [],
            'recent_bookings': [],
            'customers': [],
            'services': [],
            'total_bookings': 0,
            'pending_bookings': 0,
            'completed_bookings': 0,
            'created_at_exists': False,
            # Empty analytics data for error case
            'bookings_this_year': 0,
            'bookings_this_month': 0,
            'bookings_this_week': 0,
            'monthly_bookings': [0] * 12,
            'quarterly_bookings': [0] * 4,
            'service_bookings': [],
            'location_bookings': [],
            'customer_bookings': [],
            'staff_bookings': [],
            'monthly_revenue': 0,
        })

@login_required
def admin_bookings(request):
    """Admin bookings management page."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    try:
        # Check if created_at column exists
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='core_booking' AND column_name='created_at')")
            created_at_exists = cursor.fetchone()[0]
            
        # Get bookings with appropriate ordering
        if created_at_exists:
            bookings = Booking.objects.all().order_by('-created_at')
        else:
            bookings = Booking.objects.all().order_by('-date', '-time')
            
        # Pagination
        paginator = Paginator(bookings, 10)  # Show 10 bookings per page
        page_number = request.GET.get('page')
        paginated_bookings = paginator.get_page(page_number)
        
        return render(request, 'admin/bookings.html', {
            'bookings': paginated_bookings,
            'created_at_exists': created_at_exists
        })
    except Exception as e:
        messages.error(request, f"Database error: {str(e)}")
        return render(request, 'admin/bookings.html', {'bookings': [], 'created_at_exists': False})

@login_required
def admin_services(request):
    """Admin services management page."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    services = Service.objects.all()
    return render(request, 'admin/services.html', {'services': services})

@login_required
def admin_customers(request):
    """Admin customers management page."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    customers = Customer.objects.all()
    return render(request, 'admin/customers.html', {'customers': customers})

@login_required
def admin_settings(request):
    """Admin settings page."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
        
    return render(request, 'admin/settings.html')

from django.contrib.auth.hashers import check_password

@login_required
def admin_service_save(request):
    """Save or update a service."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('home')
        
    if request.method == 'POST':
        service_id = request.POST.get('service_id', '')
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        
        # Get the new fields
        duration = request.POST.get('duration', '')
        materials = request.POST.get('materials', '')
        staff_count = request.POST.get('staff_count', 1)
        
        try:
            if service_id:  # Update existing service
                service = Service.objects.get(id=service_id)
                service.name = name
                service.description = description
                service.price = price
                
                # Add new fields
                service.duration = duration
                service.materials = materials
                service.staff_count = staff_count
                
                service.save()
                messages.success(request, f"Service '{name}' updated successfully.")
            else:  # Create new service
                Service.objects.create(
                    name=name,
                    description=description,
                    price=price,
                    duration=duration,
                    materials=materials,
                    staff_count=staff_count
                )
                messages.success(request, f"Service '{name}' created successfully.")
        except Exception as e:
            messages.error(request, f"Error saving service: {str(e)}")
    
    return redirect('admin_services')
@login_required
def admin_services(request):
    """Admin services management page."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Include archived services in the queryset
    services = Service.objects.all().order_by('-id')
    
    context = {
        'services': services,
    }
    return render(request, 'admin/services.html', context)
    
@login_required
def admin_service_archive(request):
    """Archive or restore a service."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('home')
        
    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        action = request.POST.get('action', 'archive')  # Default to archive
        
        try:
            service = Service.objects.get(id=service_id)
            
            if action == 'archive':
                service.is_archived = True
                service.save()
                messages.success(request, f"Service '{service.name}' has been archived.")
            elif action == 'restore':
                service.is_archived = False
                service.save()
                messages.success(request, f"Service '{service.name}' has been restored.")
                
        except Service.DoesNotExist:
            messages.error(request, "Service not found.")
    
    return redirect('admin_services')

@login_required
def admin_service_delete(request):
    """Delete a service."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('home')
        
    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        
        try:
            service = Service.objects.get(id=service_id)
            service_name = service.name
            service.delete()
            messages.success(request, f"Service '{service_name}' deleted successfully.")
        except Service.DoesNotExist:
            messages.error(request, "Service not found.")
        except Exception as e:
            messages.error(request, f"Error deleting service: {str(e)}")
            
    return redirect('admin_services')

@login_required
def settings_page(request):
    """View for managing settings."""
    return render(request, 'admin/settings.html')

@login_required
def services_page(request):
    """View for managing services."""
    services = Service.objects.filter(is_archived=False)
    return render(request, 'admin/services.html', {'services': services})

@login_required
def bookings_page(request):
    """View for managing bookings."""
    try:
        # Change order to not use created_at
        bookings = Booking.objects.all().order_by('-date', '-time')
        return render(request, 'admin/bookings.html', {'bookings': bookings})
    except Exception as e:
        messages.error(request, f"Database error: {str(e)}")
        return render(request, 'admin/bookings.html', {'bookings': []})

@login_required
def customers_page(request):
    """View for managing customers."""
    customers = Customer.objects.all()
    return render(request, 'admin/customers.html', {'customers': customers})

from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def profile(request):
    return render(request, 'profile.html')

@login_required
def profile_update(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.profile.phone = request.POST.get('phone')
        user.profile.address = request.POST.get('address')
        user.save()
        user.profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return redirect('profile')

def api_services(request):
    """API endpoint to get all services as JSON."""
    try:
        services = list(Service.objects.all().values('id', 'name', 'price', 'description'))
        return JsonResponse(services, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Add new view for updating booking status
@transaction.atomic
def update_booking_status(request):
    """Update booking status (confirm or reject)."""
    # Your existing code...
    
    booking_id = request.POST.get('booking_id')
    new_status = request.POST.get('status')
    admin_note = request.POST.get('admin_note', '')  # Get admin note if provided
    decline_reason = request.POST.get('decline_reason', '')  # Get decline reason if provided
    
    try:
        booking = Booking.objects.select_for_update().get(id=booking_id)
        old_status = booking.status
        booking.status = new_status
        
        # Update admin note if provided (usually when confirming bookings)
        if admin_note.strip():
            booking.admin_note = admin_note.strip()
        
        # Update decline reason if provided (when cancelling/declining bookings)
        if decline_reason.strip():
            booking.decline_reason = decline_reason.strip()
        
        # If status is being changed to confirmed and no staff is assigned yet, auto-assign staff
        if new_status == 'confirmed' and not booking.assigned_staff:
            # Try to find staff with this as primary service
            primary_staff_service = StaffService.objects.filter(
                service=booking.service,
                is_primary=True
            ).select_related('staff').first()
            
            if primary_staff_service:
                booking.assigned_staff = primary_staff_service.staff
                print(f"Booking #{booking.id} auto-assigned to primary staff during confirmation")
            else:
                # No primary staff, try any qualified staff
                any_qualified_staff_service = StaffService.objects.filter(
                    service=booking.service
                ).select_related('staff').first()
                
                if any_qualified_staff_service:
                    booking.assigned_staff = any_qualified_staff_service.staff
                    print(f"Booking #{booking.id} auto-assigned to qualified staff during confirmation")
        
        booking.save()
        
        # Rest of your code for creating notifications, etc.
        
        # Create notification for the customer - INSIDE TRANSACTION
        customer_email = booking.customer.email
        
        def create_notification():
            try:
                if User.objects.filter(email=customer_email).exists():
                    user = User.objects.get(email=customer_email)
                    
                    # Customize message based on status
                    if new_status == 'confirmed':
                        message = f"Your booking has been confirmed."
                    elif new_status == 'cancelled':
                        # Include the decline reason in the notification message if it exists
                        if decline_reason:
                            message = f"Your booking has been declined. Reason: {decline_reason}"
                        else:
                            message = f"Your booking has been declined."
                    else:
                        message = f"Your booking status has been updated to {new_status}."
                    
                    # Create notification
                    notification = Notification.objects.create(
                        user=user,
                        booking=booking,
                        message=message,
                        is_read=False
                    )
                    
                    print(f"Notification created: {notification.id} for user {user.id} (email: {user.email})")
            except Exception as e:
                print(f"Error creating notification: {str(e)}")
        
        # This ensures notification is created AFTER transaction is committed
        transaction.on_commit(create_notification)
        
        messages.success(request, f"Booking #{booking_id} status updated to {new_status}")
        return redirect('admin_bookings')
    
    except Booking.DoesNotExist:
        messages.error(request, f"Booking #{booking_id} not found")
        return redirect('admin_bookings')
    
    except Exception as e:
        messages.error(request, f"Error updating booking: {str(e)}")
        return redirect('admin_bookings')

@login_required
def update_admin_note(request):
    """Update admin note for a booking."""
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        admin_note = request.POST.get('admin_note', '').strip()
        
        try:
            booking = Booking.objects.get(id=booking_id)
            booking.admin_note = admin_note
            booking.save()
            
            if admin_note:
                messages.success(request, f"Service note added for booking #{booking_id}")
            else:
                messages.success(request, f"Service note removed from booking #{booking_id}")
                
            return redirect('admin_dashboard')
            
        except Booking.DoesNotExist:
            messages.error(request, f"Booking #{booking_id} not found")
            return redirect('admin_dashboard')
            
        except Exception as e:
            messages.error(request, f"Error updating note: {str(e)}")
            return redirect('admin_dashboard')
    
    return redirect('admin_dashboard')

@login_required
def check_notifications(request):
    """API endpoint to check for new notifications without reloading the page"""
    import json
    import traceback
    
    try:
        # Use direct SQL query for reliability
        from django.db import connection
        
        # Debug info in response
        debug_info = {
            "user_id": request.user.id,
            "username": request.user.username,
            "method": "SQL Query"
        }
        
        with connection.cursor() as cursor:
            # Check if notification table exists
            cursor.execute("SELECT to_regclass('public.core_notification')")
            notification_table_exists = cursor.fetchone()[0]
            
            if not notification_table_exists:
                return JsonResponse({
                    'count': 0, 
                    'notifications': [],
                    'debug': debug_info
                })
            
            # Count unread notifications
            cursor.execute("""
                SELECT COUNT(*) 
                FROM core_notification 
                WHERE user_id = %s AND is_read = FALSE
            """, [request.user.id])
            count = cursor.fetchone()[0]
            debug_info["unread_count"] = count
            
            # Get latest notifications
            cursor.execute("""
                SELECT id, message, created_at, booking_id
                FROM core_notification 
                WHERE user_id = %s AND is_read = FALSE
                ORDER BY created_at DESC
                LIMIT 10
            """, [request.user.id])
            
            notification_list = []
            for row in cursor.fetchall():
                notification_id, message, created_at, booking_id = row
                
                # Get service name if possible
                service_name = "Service"
                if booking_id:
                    try:
                        cursor.execute("""
                            SELECT s.name 
                            FROM core_service s
                            JOIN core_booking b ON b.service_id = s.id
                            WHERE b.id = %s
                        """, [booking_id])
                        result = cursor.fetchone()
                        if result:
                            service_name = result[0]
                    except:
                        pass
                
                notification_list.append({
                    'id': notification_id,
                    'message': message,
                    'created_at': created_at.isoformat() if created_at else None,
                    'service_name': service_name
                })
            
            debug_info["notifications_fetched"] = len(notification_list)
            
            # Print debug info
            print(f"Notification check for user {request.user.id}: found {count} unread notifications")
            
            return JsonResponse({
                'count': count,
                'notifications': notification_list,
                'debug': debug_info
            })
            
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error checking notifications: {str(e)}\n{error_trace}")
        return JsonResponse({
            'error': str(e), 
            'count': 0, 
            'notifications': [],
            'trace': error_trace
        }, status=500)
    
@login_required
@require_POST
def mark_notifications_read(request):
    """Mark all notifications as read for the current user."""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'mark_all_read':
            # Check if notification table exists
            with connection.cursor() as cursor:
                cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'core_notification')")
                notification_table_exists = cursor.fetchone()[0]
                
                if notification_table_exists:
                    # This SQL query updates all notifications for the current user to is_read = TRUE
                    cursor.execute("""
                        UPDATE core_notification 
                        SET is_read = TRUE 
                        WHERE user_id = %s AND is_read = FALSE
                    """, [request.user.id])
                    
                    # Get count of updated rows
                    updated_count = cursor.rowcount
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Marked {updated_count} notifications as read',
                        'updated_count': updated_count
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Notification table does not exist'
                    }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid action'
            }, status=400)
    except Exception as e:
        print(f"Error marking notifications as read: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    
@login_required
def staff_dashboard(request):
    """Staff dashboard page."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access the staff dashboard.")
        return redirect('home')
    
    # Get today's date
    today = timezone.now().date()
    
    # Get today's bookings assigned to this staff
    todays_bookings = Booking.objects.filter(
        date=today,
        assigned_staff=request.user,  # Filter by the logged-in staff member
        status__in=['confirmed', 'pending']
    ).order_by('time')
    
    # Get upcoming bookings
    upcoming_bookings = Booking.objects.filter(
        date__gt=today,
        assigned_staff=request.user,  # Filter by the logged-in staff member
        status__in=['confirmed', 'pending']
    ).order_by('date', 'time')[:10]
    
    # Get all assignments for this staff
    all_assignments = Booking.objects.filter(
        assigned_staff=request.user  # Filter by the logged-in staff member
    ).order_by('-date', '-time')[:20]
    
    # Get services assigned to this staff member
    assigned_services = StaffService.objects.filter(
        staff=request.user  # Filter by the logged-in staff member
    ).select_related('service')
    
    # Counts for dashboard stats
    today_bookings = todays_bookings.count()
    assigned_bookings = Booking.objects.filter(
        assigned_staff=request.user,
        status__in=['confirmed', 'pending']
    ).count()
    completed_bookings = Booking.objects.filter(
        assigned_staff=request.user,
        status='completed'
    ).count()
    
    context = {
        'todays_bookings': todays_bookings,
        'upcoming_bookings': upcoming_bookings,
        'all_assignments': all_assignments,
        'today_bookings': today_bookings,
        'assigned_bookings': assigned_bookings,
        'completed_bookings': completed_bookings,
        'assigned_services': assigned_services,  # Add this to the context
    }
    
    return render(request, 'staff/staff_dashboard.html', context)

@login_required
def staff_bookings(request):
    """API endpoint for fetching all bookings with pagination for staff dashboard."""
    search = request.GET.get('search', '')
    page = request.GET.get('page', 1)
    my_services_only = request.GET.get('my_services_only', 'false').lower() == 'true'
    
    # Get all bookings
    bookings = Booking.objects.all().order_by('-date', '-time')
    
    # Filter by my services if requested
    if my_services_only:
        staff_services = StaffService.objects.filter(staff=request.user).values_list('service__id', flat=True)
        bookings = bookings.filter(service__id__in=staff_services)
    
    # Apply search if provided
    if search:
        bookings = bookings.filter(
            Q(customer__name__icontains=search) |
            Q(service__name__icontains=search) |
            Q(customer__email__icontains=search) |
            Q(customer__phone__icontains=search) |
            Q(id__icontains=search)
        )
    
    # Paginate results
    paginator = Paginator(bookings, 10)
    
    try:
        bookings_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        bookings_page = paginator.page(1)
    
    # Format the response
    results = []
    for booking in bookings_page:
        # Get all staff members assigned to this service type
        qualified_staff = StaffService.objects.filter(service=booking.service).select_related('staff')
        
        qualified_staff_names = [staff.staff.get_full_name() for staff in qualified_staff]
        qualified_staff_ids = [staff.staff.id for staff in qualified_staff]
        
        # Check if current user is qualified
        is_qualified = request.user.id in qualified_staff_ids
        
        results.append({
            'id': booking.id,
            'customer_name': booking.customer.name,
            'customer_email': booking.customer.email,
            'customer_phone': booking.customer.phone,
            'customer_address': booking.customer.address,
            'service_name': booking.service.name,
            'service_id': booking.service.id,
            'date': booking.date.strftime('%Y-%m-%d'),
            'time': booking.time.strftime('%H:%M:%S'),
            'status': booking.status,
            'price': booking.service.price,
            'duration': f"{booking.service.duration} hours" if hasattr(booking.service, 'duration') else "2 hours",
            'assigned_staff': booking.assigned_staff.id if booking.assigned_staff else None,
            'staff_name': booking.assigned_staff.get_full_name() if booking.assigned_staff else None,
            'clock_in': booking.clock_in.strftime('%H:%M:%S') if booking.clock_in else None,
            'clock_out': booking.clock_out.strftime('%H:%M:%S') if booking.clock_out else None,
            'qualified_staff': qualified_staff_names,
            'qualified_staff_ids': qualified_staff_ids,
            'is_current_user_qualified': is_qualified,
        })
    
    response_data = {
        'results': results,
        'current_page': bookings_page.number,
        'total_pages': paginator.num_pages,
        'total': paginator.count,
        'start_index': bookings_page.start_index(),
        'end_index': bookings_page.end_index(),
    }
    
    return JsonResponse(response_data)

@login_required
def staff_assign_booking(request):
    """Assign a booking to the current staff member."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('staff_dashboard')
    
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        
        try:
            booking = Booking.objects.get(id=booking_id)
            
            # Check if the booking is already assigned
            if booking.assigned_staff:
                messages.error(request, f"Booking #{booking_id} is already assigned to {booking.assigned_staff.get_full_name()}")
                return redirect('staff_dashboard')
            
            # Check if staff has the required skills
            staff_services = StaffService.objects.filter(staff=request.user).values_list('service__id', flat=True)
            
            if booking.service.id not in staff_services:
                messages.error(request, "You don't have the skills required for this service.")
                return redirect('staff_dashboard')
            
            # Assign booking to current staff
            booking.assigned_staff = request.user
            booking.save()
            
            messages.success(request, f"Booking #{booking_id} has been assigned to you.")
            
        except Booking.DoesNotExist:
            messages.error(request, "Booking not found.")
    
    # Return to the bookings section
    return redirect('staff_dashboard')

# Add this URL pattern to your urls.py
# path('staff/assign_booking/', views.staff_assign_booking, name='staff_assign_booking'),

@login_required
def staff_clock_in(request, booking_id):
    """Staff clocks in for a booking."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('home')
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if staff is assigned to this booking
    if booking.assigned_staff != request.user:
        messages.error(request, "You are not assigned to this booking.")
        return redirect('staff_dashboard')
    
    # Check if already clocked in
    if booking.clock_in:
        messages.warning(request, f"You have already clocked in at {booking.clock_in.strftime('%H:%M:%S')}")
        return redirect('staff_dashboard')
    
    # Clock in
    booking.clock_in = timezone.now()
    booking.save()
    
    messages.success(request, f"Successfully clocked in for booking #{booking.id}")
    return redirect('staff_dashboard')

@login_required
def staff_clock_out(request, booking_id):
    """Staff clocks out from a booking."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('home')
    
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if staff is assigned to this booking
    if booking.assigned_staff != request.user:
        messages.error(request, "You are not assigned to this booking.")
        return redirect('staff_dashboard')
    
    # Check if clocked in
    if not booking.clock_in:
        messages.error(request, "You need to clock in before clocking out.")
        return redirect('staff_dashboard')
    
    # Check if already clocked out
    if booking.clock_out:
        messages.warning(request, f"You have already clocked out at {booking.clock_out.strftime('%H:%M:%S')}")
        return redirect('staff_dashboard')
    
    # Clock out
    booking.clock_out = timezone.now()
    booking.save()
    
    # Calculate duration
    duration = booking.get_duration()
    
    messages.success(request, f"Successfully clocked out. Total work duration: {duration} hours.")
    return redirect('staff_dashboard')

@login_required
def admin_assign_service(request):
    """Admin page to assign services to staff members."""
    # Only check for user.profile.is_admin, don't rely on Django's admin permissions
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get all staff members (is_staff=True)
    staff_members = User.objects.filter(is_staff=True).order_by('first_name', 'last_name')
    
    # Get all services
    services = Service.objects.filter(is_archived=False).order_by('name')
    
    # Get all staff service assignments
    staff_services = StaffService.objects.select_related('staff', 'service').all().order_by(
        'staff__first_name', 'staff__last_name', '-is_primary', 'service__name'
    )
    
    # Handle form submission
    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        service_id = request.POST.get('service_id')
        is_primary = request.POST.get('is_primary') == '1'
        notes = request.POST.get('notes', '')
        
        try:
            staff = User.objects.get(id=staff_id, is_staff=True)
            service = Service.objects.get(id=service_id, is_archived=False)
            
            # Check if assignment already exists
            assignment, created = StaffService.objects.get_or_create(
                staff=staff,
                service=service,
                defaults={
                    'is_primary': is_primary,
                    'notes': notes
                }
            )
            
            if not created:
                # Update existing assignment
                assignment.is_primary = is_primary
                assignment.notes = notes
                assignment.save()
                messages.success(request, f"Updated service assignment for {staff.get_full_name() or staff.username}")
            else:
                messages.success(request, f"Service successfully assigned to {staff.get_full_name() or staff.username}")
                
        except User.DoesNotExist:
            messages.error(request, "Selected staff member does not exist or is not a staff user.")
        except Service.DoesNotExist:
            messages.error(request, "Selected service does not exist.")
        
        return redirect('admin_assign_service')
    
    context = {
        'staff_members': staff_members,
        'services': services,
        'staff_services': staff_services,
    }
    
    return render(request, 'admin/admin_assign_service.html', context)

@login_required
def admin_update_assignment(request):
    """Update an existing staff service assignment."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('home')
    
    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        staff_id = request.POST.get('staff_id')
        service_id = request.POST.get('service_id')
        is_primary = request.POST.get('is_primary') == '1'
        notes = request.POST.get('notes', '')
        
        try:
            assignment = StaffService.objects.get(id=assignment_id)
            staff = User.objects.get(id=staff_id, is_staff=True)
            service = Service.objects.get(id=service_id)
            
            # Check if this would create a duplicate
            if assignment.staff != staff or assignment.service != service:
                if StaffService.objects.filter(staff=staff, service=service).exclude(id=assignment_id).exists():
                    messages.error(request, "This staff member is already assigned to this service.")
                    return redirect('admin_assign_service')
            
            assignment.staff = staff
            assignment.service = service
            assignment.is_primary = is_primary
            assignment.notes = notes
            assignment.save()
            
            messages.success(request, "Service assignment updated successfully.")
            
        except StaffService.DoesNotExist:
            messages.error(request, "Assignment not found.")
        except User.DoesNotExist:
            messages.error(request, "Selected staff member does not exist or is not a staff user.")
        except Service.DoesNotExist:
            messages.error(request, "Selected service does not exist.")
    
    return redirect('admin_assign_service')

@login_required
def admin_delete_assignment(request):
    """Delete a staff service assignment."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('home')
    
    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        
        try:
            assignment = StaffService.objects.get(id=assignment_id)
            staff_name = assignment.staff.get_full_name() or assignment.staff.username
            service_name = assignment.service.name
            
            assignment.delete()
            
            messages.success(request, f"Removed '{service_name}' service from {staff_name}.")
            
        except StaffService.DoesNotExist:
            messages.error(request, "Assignment not found.")
    
    return redirect('admin_assign_service')

@login_required
def staff_profile_update(request):
    """Update staff profile information."""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('home')
    
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validate current password
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('staff_dashboard')
        
        # Update user basic info
        request.user.first_name = first_name
        request.user.last_name = last_name
        
        # Check if email is changing and if it's available
        if email != request.user.email:
            if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.error(request, "Email already in use.")
                return redirect('staff_dashboard')
            request.user.email = email
        
        # Update password if provided
        if new_password:
            if new_password != confirm_password:
                messages.error(request, "New passwords don't match.")
                return redirect('staff_dashboard')
            
            request.user.set_password(new_password)
        
        request.user.save()
        
        # Update profile info
        if hasattr(request.user, 'profile'):
            request.user.profile.phone = phone
            request.user.profile.save()
        
        # Update session auth hash so user remains logged in after password change
        if new_password:
            update_session_auth_hash(request, request.user)
        
        messages.success(request, "Profile updated successfully.")
        return redirect('staff_dashboard')
    
    return redirect('staff_dashboard')

@login_required
def booking_detail(request, booking_id):
    """Get details for a specific booking."""
    try:
        booking = Booking.objects.get(id=booking_id)
        
        # Get qualified staff for this service
        qualified_staff = StaffService.objects.filter(service=booking.service).select_related('staff')
        qualified_staff_names = [staff.staff.get_full_name() for staff in qualified_staff]
        
        response = {
            'id': booking.id,
            'customer_name': booking.customer.name,
            'customer_email': booking.customer.email,
            'customer_phone': booking.customer.phone,
            'customer_address': booking.customer.address,
            'service_name': booking.service.name,
            'date': booking.date.strftime('%Y-%m-%d'),
            'time': booking.time.strftime('%H:%M:%S'),
            'status': booking.status,
            'price': booking.service.price,
            'duration': f"{booking.service.duration} hours" if hasattr(booking.service, 'duration') else "2 hours",
            'assigned_staff': booking.assigned_staff.id if booking.assigned_staff else None,
            'staff_name': booking.assigned_staff.get_full_name() if booking.assigned_staff else None,
            'clock_in': booking.clock_in.strftime('%H:%M:%S') if booking.clock_in else None,
            'clock_out': booking.clock_out.strftime('%H:%M:%S') if booking.clock_out else None,
            'work_duration': booking.get_duration() if hasattr(booking, 'get_duration') else None,
            'notes': booking.notes,
            'user_note': booking.user_note,
            'admin_note': booking.admin_note,
            'qualified_staff': qualified_staff_names,
        }
        
        return JsonResponse(response)
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)

@login_required
def staff_booking_detail(request, booking_id):
    """Get details for a specific booking from staff perspective."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    return booking_detail(request, booking_id)


@login_required
def staff_get_assignments(request):
    """Get staff assignments for calendar display."""
    if not request.user.is_staff:
        return JsonResponse([], safe=False)
    
    # Get date range from request
    start_param = request.GET.get('start', '')
    end_param = request.GET.get('end', '')
    
    # Parse dates correctly
    try:
        start_date = datetime.strptime(start_param.split('T')[0], '%Y-%m-%d').date()
        end_date = datetime.strptime(end_param.split('T')[0], '%Y-%m-%d').date()
    except (ValueError, IndexError):
        # Use default date range if parsing fails
        start_date = timezone.now().date()
        end_date = start_date + timezone.timedelta(days=30)
    
    # Get bookings assigned to this staff within the date range
    bookings = Booking.objects.filter(
        assigned_staff=request.user,
        date__range=[start_date, end_date],
        status__in=['pending', 'confirmed', 'completed']
    ).select_related('customer', 'service')
    
    # Format bookings for FullCalendar
    events = []
    for booking in bookings:
        events.append({
            'id': booking.id,
            'service_name': booking.service.name,
            'customer_name': booking.customer.name,
            'date': booking.date.strftime('%Y-%m-%d'),
            'time': booking.time.strftime('%H:%M:%S'),
            'duration': f"{booking.service.duration} hours" if hasattr(booking.service, 'duration') else "2 hours",
            'address': booking.customer.address,
            'status': booking.status,
            'staff_count': 1
        })
    
    return JsonResponse(events, safe=False)

@login_required
def admin_staff(request):
    """Admin staff management page."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get all staff users (users with is_staff=True)
    staff_list = User.objects.filter(is_staff=True).order_by('-date_joined')
    
    return render(request, 'admin/staff_management.html', {
        'staff_list': staff_list
    })

@login_required
def admin_staff_create(request):
    """Create a new staff member."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email', '')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            phone = request.POST.get('phone', '')
            
            # Validate required fields
            if not all([username, first_name, last_name, password, confirm_password]):
                messages.error(request, "Please fill in all required fields.")
                return redirect('admin_staff')
            
            # Validate password match
            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect('admin_staff')
            
            # Validate password length
            if len(password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return redirect('admin_staff')
            
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists. Please choose a different username.")
                return redirect('admin_staff')
            
            # Check if email already exists (if provided)
            if email and User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists. Please use a different email.")
                return redirect('admin_staff')
            
            # Create the staff user
            staff_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True  # Automatically set is_staff to True
            )
            
            # Create or update user profile
            profile, created = UserProfile.objects.get_or_create(user=staff_user)
            if phone:
                profile.phone = phone
                profile.save()
            
            messages.success(request, f"Staff account '{username}' created successfully!")
            
        except Exception as e:
            messages.error(request, f"Error creating staff account: {str(e)}")
    
    return redirect('admin_staff')

@login_required
def admin_staff_update(request):
    """Update an existing staff member."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    if request.method == 'POST':
        try:
            staff_id = request.POST.get('staff_id')
            username = request.POST.get('username')
            email = request.POST.get('email', '')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            new_password = request.POST.get('new_password', '')
            phone = request.POST.get('phone', '')
            
            # Get the staff user
            staff_user = User.objects.get(id=staff_id, is_staff=True)
            
            # Validate required fields
            if not all([username, first_name, last_name]):
                messages.error(request, "Please fill in all required fields.")
                return redirect('admin_staff')
            
            # Check if username already exists (excluding current user)
            if User.objects.filter(username=username).exclude(id=staff_id).exists():
                messages.error(request, "Username already exists. Please choose a different username.")
                return redirect('admin_staff')
            
            # Check if email already exists (excluding current user, if provided)
            if email and User.objects.filter(email=email).exclude(id=staff_id).exists():
                messages.error(request, "Email already exists. Please use a different email.")
                return redirect('admin_staff')
            
            # Update user fields
            staff_user.username = username
            staff_user.email = email
            staff_user.first_name = first_name
            staff_user.last_name = last_name
            
            # Update password if provided
            if new_password:
                if len(new_password) < 8:
                    messages.error(request, "New password must be at least 8 characters long.")
                    return redirect('admin_staff')
                staff_user.set_password(new_password)
            
            staff_user.save()
            
            # Update profile
            profile, created = UserProfile.objects.get_or_create(user=staff_user)
            profile.phone = phone
            profile.save()
            
            messages.success(request, f"Staff account '{username}' updated successfully!")
            
        except User.DoesNotExist:
            messages.error(request, "Staff member not found.")
        except Exception as e:
            messages.error(request, f"Error updating staff account: {str(e)}")
    
    return redirect('admin_staff')

@login_required
def admin_staff_status(request):
    """Activate or deactivate a staff member."""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    if request.method == 'POST':
        try:
            staff_id = request.POST.get('staff_id')
            action = request.POST.get('action')
            
            # Get the staff user
            staff_user = User.objects.get(id=staff_id, is_staff=True)
            
            # Prevent admin from deactivating themselves
            if staff_user == request.user:
                messages.error(request, "You cannot change your own status.")
                return redirect('admin_staff')
            
            if action == 'activate':
                staff_user.is_active = True
                staff_user.save()
                messages.success(request, f"Staff member '{staff_user.get_full_name() or staff_user.username}' activated successfully!")
            elif action == 'deactivate':
                staff_user.is_active = False
                staff_user.save()
                messages.success(request, f"Staff member '{staff_user.get_full_name() or staff_user.username}' deactivated successfully!")
            else:
                messages.error(request, "Invalid action.")
                
        except User.DoesNotExist:
            messages.error(request, "Staff member not found.")
        except Exception as e:
            messages.error(request, f"Error changing staff status: {str(e)}")
    
    return redirect('admin_staff')

# ======================== FEEDBACK SYSTEM VIEWS ========================

@login_required
def feedback_page(request, booking_id):
    """Display feedback form for a completed booking"""
    try:
        # Get the booking and ensure it belongs to the current user
        booking = get_object_or_404(Booking, id=booking_id)
        
        # Check if user has permission to leave feedback for this booking
        user_can_give_feedback = False
        
        if request.user.is_authenticated:
            # Check if user is the customer for this booking (by email or user link)
            if hasattr(request.user, 'customer') and booking.customer == request.user.customer:
                user_can_give_feedback = True
            elif booking.customer.email == request.user.email:
                user_can_give_feedback = True
            elif request.user.is_staff and booking.assigned_staff == request.user:
                user_can_give_feedback = True
        
        if not user_can_give_feedback:
            messages.error(request, "You don't have permission to access this feedback page.")
            return redirect('user_dashboard')
        
        # Check if feedback already exists
        from .models import Feedback
        existing_feedback = Feedback.objects.filter(booking=booking).first()
        if existing_feedback:
            messages.info(request, "You have already submitted feedback for this booking.")
            return redirect('user_dashboard')
        
        # Allow feedback for pending, confirmed or completed bookings
        if booking.status not in ['pending', 'confirmed', 'completed']:
            messages.warning(request, "Feedback can only be submitted for valid bookings.")
            return redirect('user_dashboard')
        
        return render(request, 'feedback.html', {
            'booking': booking
        })
        
    except Exception as e:
        messages.error(request, f"Error loading feedback page: {str(e)}")
        return redirect('user_dashboard')

@login_required
def submit_feedback(request, booking_id):
    """Handle feedback form submission"""
    if request.method != 'POST':
        return redirect('feedback_page', booking_id=booking_id)
    
    try:
        # Get the booking and verify permissions
        booking = get_object_or_404(Booking, id=booking_id)
        
        if not (hasattr(request.user, 'customer') and booking.customer == request.user.customer):
            messages.error(request, "You don't have permission to submit feedback for this booking.")
            return redirect('user_dashboard')
        
        # Check if feedback already exists
        from .models import Feedback
        if Feedback.objects.filter(booking=booking).exists():
            messages.error(request, "Feedback has already been submitted for this booking.")
            return redirect('user_dashboard')
        
        # Get form data
        overall_rating = int(request.POST.get('overall_rating'))
        quality_rating = int(request.POST.get('quality_rating'))
        punctuality_rating = int(request.POST.get('punctuality_rating'))
        staff_behavior_rating = int(request.POST.get('staff_behavior_rating'))
        value_for_money_rating = int(request.POST.get('value_for_money_rating'))
        would_recommend = request.POST.get('would_recommend') == 'true'
        
        positive_feedback = request.POST.get('positive_feedback', '').strip()
        improvement_feedback = request.POST.get('improvement_feedback', '').strip()
        additional_comments = request.POST.get('additional_comments', '').strip()
        
        # Validate ratings
        ratings = [overall_rating, quality_rating, punctuality_rating, staff_behavior_rating, value_for_money_rating]
        if not all(1 <= rating <= 5 for rating in ratings):
            messages.error(request, "All ratings must be between 1 and 5.")
            return redirect('feedback_page', booking_id=booking_id)
        
        # Create feedback
        feedback = Feedback.objects.create(
            booking=booking,
            customer=booking.customer,
            service=booking.service,
            assigned_staff=booking.assigned_staff,
            overall_rating=overall_rating,
            quality_rating=quality_rating,
            punctuality_rating=punctuality_rating,
            staff_behavior_rating=staff_behavior_rating,
            value_for_money_rating=value_for_money_rating,
            positive_feedback=positive_feedback or None,
            improvement_feedback=improvement_feedback or None,
            additional_comments=additional_comments or None,
            would_recommend=would_recommend
        )
        
        messages.success(request, "Thank you for your feedback! Your review helps us improve our services.")
        
        # Redirect to feedback success page with the feedback data
        return render(request, 'feedback_success.html', {
            'feedback': feedback,
            'booking': booking
        })
        
    except ValueError as e:
        messages.error(request, "Invalid rating values. Please provide ratings between 1 and 5.")
        return redirect('feedback_page', booking_id=booking_id)
    except Exception as e:
        messages.error(request, f"Error submitting feedback: {str(e)}")
        return redirect('feedback_page', booking_id=booking_id)

@login_required
def admin_ratings(request):
    """Admin view for all customer ratings and feedback"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    try:
        # Try to import Feedback model
        try:
            from .models import Feedback
        except ImportError:
            # Feedback model doesn't exist yet, show empty page
            messages.info(request, "Feedback system not yet initialized. No ratings to display.")
            return render(request, 'admin/ratings.html', {
                'feedbacks': [],
                'analytics': {
                    'total_feedbacks': 0,
                    'average_ratings': {
                        'overall': 0,
                        'quality': 0,
                        'punctuality': 0,
                        'staff_behavior': 0,
                        'value_for_money': 0,
                    },
                    'recommendation_rate': 0,
                    'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                },
                'services': Service.objects.filter(is_archived=False).order_by('name'),
                'featured_count': 0,
            })
        
        from django.db.models import Q, Avg
        
        # Get all feedbacks
        feedbacks = Feedback.objects.select_related('customer', 'service', 'assigned_staff', 'booking').order_by('-created_at')
        
        # Apply filters
        service_filter = request.GET.get('service')
        if service_filter:
            feedbacks = feedbacks.filter(service_id=service_filter)
        
        rating_filter = request.GET.get('rating')
        if rating_filter:
            min_rating = int(rating_filter)
            feedbacks = feedbacks.filter(overall_rating__gte=min_rating)
        
        date_range = request.GET.get('date_range')
        if date_range:
            now = timezone.now()
            if date_range == 'week':
                start_date = now - timedelta(weeks=1)
            elif date_range == 'month':
                start_date = now - timedelta(days=30)
            elif date_range == 'quarter':
                start_date = now - timedelta(days=90)
            else:
                start_date = None
            
            if start_date:
                feedbacks = feedbacks.filter(created_at__gte=start_date)
        
        # Get analytics
        try:
            analytics = Feedback.get_service_analytics()
        except:
            analytics = None
            
        if not analytics:
            analytics = {
                'total_feedbacks': 0,
                'average_ratings': {
                    'overall': 0,
                    'quality': 0,
                    'punctuality': 0,
                    'staff_behavior': 0,
                    'value_for_money': 0,
                },
                'recommendation_rate': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            }
        
        # Get services for filter dropdown
        services = Service.objects.filter(is_archived=False).order_by('name')
        
        # Get featured count
        try:
            featured_count = Feedback.objects.filter(is_featured=True).count()
        except:
            featured_count = 0
        
        return render(request, 'admin/ratings.html', {
            'feedbacks': feedbacks,
            'analytics': analytics,
            'services': services,
            'featured_count': featured_count,
        })
        
    except Exception as e:
        messages.error(request, f"Error loading ratings page: {str(e)}")
        # Return a simple template instead of redirecting to avoid infinite loops
        return render(request, 'admin/ratings.html', {
            'feedbacks': [],
            'analytics': {
                'total_feedbacks': 0,
                'average_ratings': {
                    'overall': 0,
                    'quality': 0,
                    'punctuality': 0,
                    'staff_behavior': 0,
                    'value_for_money': 0,
                },
                'recommendation_rate': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            },
            'services': [],
            'featured_count': 0,
        })

@login_required
@require_POST
def admin_respond_feedback(request):
    """Handle admin response to customer feedback"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('home')
    
    try:
        from .models import Feedback
        
        feedback_id = request.POST.get('feedback_id')
        admin_response = request.POST.get('admin_response', '').strip()
        
        if not feedback_id or not admin_response:
            messages.error(request, "Feedback ID and response are required.")
            return redirect('admin_ratings')
        
        feedback = get_object_or_404(Feedback, id=feedback_id)
        feedback.admin_response = admin_response
        feedback.save()
        
        messages.success(request, "Response added successfully!")
        return redirect('admin_ratings')
        
    except Exception as e:
        messages.error(request, f"Error adding response: {str(e)}")
        return redirect('admin_ratings')

@login_required
@require_POST  
def admin_toggle_featured(request):
    """Toggle featured status of feedback"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        import json
        from .models import Feedback
        
        data = json.loads(request.body)
        feedback_id = data.get('feedback_id')
        is_featured = data.get('is_featured', False)
        
        feedback = get_object_or_404(Feedback, id=feedback_id)
        feedback.is_featured = is_featured
        feedback.save()
        
        return JsonResponse({
            'success': True, 
            'is_featured': feedback.is_featured
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Downloadable Reports Views
@login_required
def download_booking_report(request):
    """Download booking reports in CSV format"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    import csv
    from django.http import HttpResponse
    
    # Get report type and period
    report_type = request.GET.get('type', 'monthly')  # weekly, monthly, quarterly, annually
    period = request.GET.get('period', 'current')      # current, last, all
    
    # Determine date range
    now = timezone.now()
    if report_type == 'weekly':
        if period == 'current':
            start_date = now - timedelta(days=now.weekday())
            end_date = start_date + timedelta(days=6)
            filename = f'weekly_bookings_{start_date.strftime("%Y%m%d")}.csv'
        elif period == 'last':
            start_date = now - timedelta(days=now.weekday() + 7)
            end_date = start_date + timedelta(days=6)
            filename = f'weekly_bookings_{start_date.strftime("%Y%m%d")}.csv'
    elif report_type == 'monthly':
        if period == 'current':
            start_date = now.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            filename = f'monthly_bookings_{start_date.strftime("%Y%m")}.csv'
        elif period == 'last':
            start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
            end_date = now.replace(day=1) - timedelta(days=1)
            filename = f'monthly_bookings_{start_date.strftime("%Y%m")}.csv'
    elif report_type == 'quarterly':
        quarter = (now.month - 1) // 3 + 1
        if period == 'current':
            start_date = now.replace(month=(quarter-1)*3+1, day=1)
            end_date = (start_date + timedelta(days=95)).replace(day=1) - timedelta(days=1)
            filename = f'quarterly_bookings_Q{quarter}_{now.year}.csv'
    elif report_type == 'annually':
        if period == 'current':
            start_date = now.replace(month=1, day=1)
            end_date = now.replace(month=12, day=31)
            filename = f'annual_bookings_{now.year}.csv'
        elif period == 'last':
            start_date = now.replace(year=now.year-1, month=1, day=1)
            end_date = now.replace(year=now.year-1, month=12, day=31)
            filename = f'annual_bookings_{now.year-1}.csv'
    else:
        start_date = None
        end_date = None
        filename = 'all_bookings.csv'
    
    # Filter bookings
    bookings = Booking.objects.select_related('customer', 'service', 'assigned_staff')
    if start_date and end_date:
        try:
            # Check if created_at column exists
            with connection.cursor() as cursor:
                cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='core_booking' AND column_name='created_at')")
                created_at_exists = cursor.fetchone()[0]
            
            if created_at_exists:
                bookings = bookings.filter(created_at__gte=start_date, created_at__lte=end_date)
            else:
                bookings = bookings.filter(date__gte=start_date.date(), date__lte=end_date.date())
        except:
            bookings = bookings.filter(date__gte=start_date.date(), date__lte=end_date.date())
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Booking ID', 'Customer Name', 'Service', 'Date', 'Time', 
        'Status', 'Address', 'Phone', 'Email', 'Staff Assigned', 
        'Service Price', 'Created At'
    ])
    
    for booking in bookings:
        try:
            staff_name = booking.assigned_staff.get_full_name() if booking.assigned_staff else 'Not Assigned'
            service_price = booking.service.price if hasattr(booking.service, 'price') else 'N/A'
            created_at = booking.created_at if hasattr(booking, 'created_at') else 'N/A'
        except:
            staff_name = 'Not Assigned'
            service_price = 'N/A'
            created_at = 'N/A'
            
            writer.writerow([
                booking.id,
                booking.customer.name,
                booking.service.name,
                booking.date,
                booking.time,
                booking.status,
                booking.customer.address,
                booking.customer.phone,
                booking.customer.email,
                staff_name,
                service_price,
                created_at
            ])
    
    return response

@login_required
def download_service_report(request):
    """Download service popularity reports in CSV format"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="service_popularity_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Service Name', 'Total Bookings', 'Completed Bookings', 'Pending Bookings', 'Total Revenue'])
    
    services = Service.objects.annotate(
        total_bookings=Count('booking'),
        completed_bookings=Count('booking', filter=Q(booking__status='completed')),
        pending_bookings=Count('booking', filter=Q(booking__status='pending'))
    ).order_by('-total_bookings')
    
    for service in services:
        try:
            revenue = Booking.objects.filter(service=service, status='completed').aggregate(
                total=Sum('service__price')
            )['total'] or 0
        except:
            revenue = 0
            
        writer.writerow([
            service.name,
            service.total_bookings,
            service.completed_bookings,
            service.pending_bookings,
            revenue
        ])
    
    return response

@login_required
def download_location_report(request):
    """Download location-based booking reports in CSV format"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="location_booking_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Customer Name', 'Address', 'Total Bookings', 'Completed Bookings', 'Pending Bookings'])
    
    locations = Booking.objects.values('customer__name', 'customer__address').annotate(
        total_bookings=Count('id'),
        completed_bookings=Count('id', filter=Q(status='completed')),
        pending_bookings=Count('id', filter=Q(status='pending'))
    ).order_by('customer__name')
    
    for location in locations:
        writer.writerow([
            location['customer__name'] or 'N/A',
            location['customer__address'] or 'N/A',
            location['total_bookings'],
            location['completed_bookings'],
            location['pending_bookings']
        ])
    
    return response

@login_required
def download_staff_report(request):
    """Download staff performance reports in CSV format"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="staff_performance_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Staff Name', 'Total Assignments', 'Completed Jobs', 'Pending Jobs', 'Completion Rate'])
    
    staff_members = User.objects.filter(is_staff=True).annotate(
        total_assignments=Count('assigned_bookings'),
        completed_jobs=Count('assigned_bookings', filter=Q(assigned_bookings__status='completed')),
        pending_jobs=Count('assigned_bookings', filter=Q(assigned_bookings__status='pending'))
    )
    
    for staff in staff_members:
        completion_rate = (staff.completed_jobs / staff.total_assignments * 100) if staff.total_assignments > 0 else 0
            
        writer.writerow([
            staff.get_full_name() or staff.username,
            staff.total_assignments,
            staff.completed_jobs,
            staff.pending_jobs,
            f"{completion_rate:.1f}%"
        ])
    
    return response

@login_required
def download_revenue_report(request):
    """Download revenue reports in CSV format"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    import csv
    from django.http import HttpResponse
    
    report_type = request.GET.get('type', 'monthly')
    period = request.GET.get('period', 'current')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="revenue_report_{report_type}_{period}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Period', 'Total Bookings', 'Completed Bookings', 'Total Revenue', 'Average Revenue per Booking'])
    
    now = timezone.now()
    
    if report_type == 'monthly':
        for month in range(1, 13):
            try:
                # Check if created_at column exists
                with connection.cursor() as cursor:
                    cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='core_booking' AND column_name='created_at')")
                    created_at_exists = cursor.fetchone()[0]
                
                if created_at_exists:
                    bookings = Booking.objects.filter(created_at__year=now.year, created_at__month=month)
                else:
                    bookings = Booking.objects.filter(date__year=now.year, date__month=month)
                    
                completed = bookings.filter(status='completed')
                revenue = completed.aggregate(total=Sum('service__price'))['total'] or 0
                avg_revenue = revenue / completed.count() if completed.count() > 0 else 0
                
                writer.writerow([
                    f"{now.year}-{month:02d}",
                    bookings.count(),
                    completed.count(),
                    revenue,
                    f"{avg_revenue:.2f}"
                ])
            except:
                writer.writerow([f"{now.year}-{month:02d}", 0, 0, 0, 0])
    
    return response


@login_required
def admin_loyal_customers(request):
    """Admin view for loyal customers - ranked by booking count"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    try:
        # Get customers with their booking counts
        customers = Customer.objects.annotate(
            total_bookings=Count('booking'),
            completed_bookings=Count('booking', filter=Q(booking__status='completed')),
            pending_bookings=Count('booking', filter=Q(booking__status='pending')),
            cancelled_bookings=Count('booking', filter=Q(booking__status='cancelled'))
        ).filter(total_bookings__gt=0).order_by('-total_bookings')
        
        # Calculate loyalty levels
        loyal_customers = []
        for customer in customers:
            if customer.total_bookings >= 10:
                loyalty_level = "Platinum"
                loyalty_class = "text-warning"
            elif customer.total_bookings >= 5:
                loyalty_level = "Gold"
                loyalty_class = "text-primary"
            elif customer.total_bookings >= 3:
                loyalty_level = "Silver"
                loyalty_class = "text-info"
            else:
                loyalty_level = "Bronze"
                loyalty_class = "text-secondary"
            
            # Calculate completion rate
            completion_rate = (customer.completed_bookings / customer.total_bookings * 100) if customer.total_bookings > 0 else 0
            
            loyal_customers.append({
                'customer': customer,
                'loyalty_level': loyalty_level,
                'loyalty_class': loyalty_class,
                'completion_rate': completion_rate
            })
        
        # Pagination
        paginator = Paginator(loyal_customers, 20)  # Show 20 customers per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Stats for the dashboard
        total_customers = Customer.objects.count()
        active_customers = Customer.objects.filter(booking__isnull=False).distinct().count()
        platinum_customers = len([c for c in loyal_customers if c['loyalty_level'] == 'Platinum'])
        gold_customers = len([c for c in loyal_customers if c['loyalty_level'] == 'Gold'])
        
        context = {
            'loyal_customers': page_obj,
            'total_customers': total_customers,
            'active_customers': active_customers,
            'platinum_customers': platinum_customers,
            'gold_customers': gold_customers,
        }
        
        return render(request, 'admin/loyal_customers.html', context)
        
    except Exception as e:
        print(f"Loyal Customers Error: {str(e)}")
        messages.error(request, f"Error loading loyal customers: {str(e)}")
        return render(request, 'admin/loyal_customers.html', {
            'loyal_customers': [],
            'total_customers': 0,
            'active_customers': 0,
            'platinum_customers': 0,
            'gold_customers': 0,
        })
