from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta

def get_google_calendar_service(credentials):
    """
    Build and return a Google Calendar service object.
    
    Args:
        credentials: OAuth2 credentials
        
    Returns:
        Google Calendar service object
    """
    try:
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"Error building calendar service: {e}")
        return None

def create_calendar_event(service, booking):
    """
    Create a calendar event for a booking.
    
    Args:
        service: Google Calendar service object
        booking: Booking model instance
        
    Returns:
        Created event ID or None on failure
    """
    try:
        # Format start and end times
        start_datetime = datetime.combine(booking.date, booking.time)
        # Assuming each booking is 2 hours
        end_datetime = start_datetime + timedelta(hours=2)
        
        timezone = 'Asia/Manila'  # Philippine Standard Time (UTC+8)
        
        event = {
            'summary': f'Cleaning Service - {booking.service.name}',
            'location': booking.customer.address,
            'description': f'Booking for {booking.customer.name}, Phone: {booking.customer.phone}',
            'start': {
                'dateTime': start_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 60},
                ],
            },
        }


        # You would need to specify which calendar to use
        calendar_id = 'primary'  # 'primary' refers to the default calendar
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        
        print(f'Event created: {event.get("htmlLink")}')
        return event['id']
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return None
