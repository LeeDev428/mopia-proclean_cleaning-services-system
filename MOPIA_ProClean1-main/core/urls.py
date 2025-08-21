from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('booking/', views.booking, name='booking'),
    path('booking/submit/', views.booking_submit, name='booking_submit'),
    path('booking/confirmation/<int:booking_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('contact/', views.contact, name='contact'),
    path('available-slots/', views.available_slots, name='available_slots'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-bookings/', views.admin_bookings, name='admin_bookings'),
    path('admin-services/', views.admin_services, name='admin_services'),
    path('admin-customers/', views.admin_customers, name='admin_customers'),
    path('admin-settings/', views.admin_settings, name='admin_settings'),
    path('admin-service-save/', views.admin_service_save, name='admin_service_save'),
    path('admin-service-delete/', views.admin_service_delete, name='admin_service_delete'),
    path('update-booking-status/', views.update_booking_status, name='update_booking_status'),
    path('api/services/', views.api_services, name='api_services'),
    path('admin-service-archive/', views.admin_service_archive, name='admin_service_archive'),
    path('update-booking-status/', views.update_booking_status, name='update_booking_status'),
    path('update-admin-note/', views.update_admin_note, name='update_admin_note'),

    # Correctly named path without underscore (to match the URL in the template)
    path('mark-notifications-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('verify-email-sent/', views.verify_email_sent, name='verify_email_sent'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),

    #Notification API for Users
    path('check-notifications/', views.check_notifications, name='check_notifications'),
    path('mark-notifications-read/', views.mark_notifications_read, name='mark_notifications_read'),

    # Staff dashboard URLs
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/profile/update/', views.staff_profile_update, name='staff_profile_update'),
    path('staff/booking/<int:booking_id>/', views.staff_booking_detail, name='staff_booking_detail'),
    path('staff/get_assignments/', views.staff_get_assignments, name='staff_get_assignments'),

    # Staff URLs
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/clock-in/<int:booking_id>/', views.staff_clock_in, name='staff_clock_in'),
    path('staff/clock-out/<int:booking_id>/', views.staff_clock_out, name='staff_clock_out'),
    path('staff/upload-before-photo/<int:booking_id>/', views.upload_before_photo, name='upload_before_photo'),
    path('staff/upload-after-photo/<int:booking_id>/', views.upload_after_photo, name='upload_after_photo'),
    path('staff/confirm-full-payment/<int:booking_id>/', views.confirm_full_payment, name='confirm_full_payment'),
    path('staff/mark-completed-full-paid/<int:booking_id>/', views.mark_completed_and_full_paid, name='mark_completed_and_full_paid'),

    # Admin service assignment URLs
    path('admin-assign-service/', views.admin_assign_service, name='admin_assign_service'),
    path('admin-update-assignment/', views.admin_update_assignment, name='admin_update_assignment'),
    path('admin-delete-assignment/', views.admin_delete_assignment, name='admin_delete_assignment'),

    # Admin staff management URLs
    path('admin-staff/', views.admin_staff, name='admin_staff'),
    path('admin-staff-create/', views.admin_staff_create, name='admin_staff_create'),
    path('admin-staff-update/', views.admin_staff_update, name='admin_staff_update'),
    path('admin-staff-status/', views.admin_staff_status, name='admin_staff_status'),

    path('staff/booking/<int:booking_id>/', views.booking_detail, name='staff_booking_detail'),
    path('staff/bookings/', views.staff_bookings, name='staff_bookings'),
    path('staff/assign_booking/', views.staff_assign_booking, name='staff_assign_booking'),
    
    # Feedback system URLs
    path('feedback/<int:booking_id>/', views.feedback_page, name='feedback_page'),
    path('feedback/submit/<int:booking_id>/', views.submit_feedback, name='submit_feedback'),
    path('admin-ratings/', views.admin_ratings, name='admin_ratings'),
    path('admin-respond-feedback/', views.admin_respond_feedback, name='admin_respond_feedback'),
    path('admin-toggle-featured/', views.admin_toggle_featured, name='admin_toggle_featured'),
    
    # Loyal Customers URL
    path('admin-loyal-customers/', views.admin_loyal_customers, name='admin_loyal_customers'),
    
    # Downloadable Reports URLs
    path('admin-reports/bookings/', views.download_booking_report, name='download_booking_report'),
    path('admin-reports/services/', views.download_service_report, name='download_service_report'),
    path('admin-reports/locations/', views.download_location_report, name='download_location_report'),
    path('admin-reports/staff/', views.download_staff_report, name='download_staff_report'),
    path('admin-reports/revenue/', views.download_revenue_report, name='download_revenue_report'),
    
    # Inventory and Logistics URLs
    path('admin-inventory/', views.admin_inventory, name='admin_inventory'),
    path('admin-inventory/get-item/<int:item_id>/', views.admin_inventory_get_item, name='admin_inventory_get_item'),
    path('admin-inventory/transactions/<int:item_id>/', views.admin_inventory_transactions, name='admin_inventory_transactions'),
    path('admin-logistics/', views.admin_logistics, name='admin_logistics'),
    
]