from mixpanel import Mixpanel
from django.conf import settings

# Initialize Mixpanel with your project token
# Replace 'YOUR_PROJECT_TOKEN' with your actual Mixpanel project token
mixpanel = Mixpanel('9ba136110737b9f78c97109ec98c5ea2')

def track_event(event_name, properties=None, user_id=None):
    """
    Track an event in Mixpanel
    
    Args:
        event_name (str): Name of the event to track
        properties (dict): Additional properties for the event
        user_id (str): User ID to associate with the event
    """
    try:
        if user_id:
            mixpanel.track(user_id, event_name, properties or {})
        else:
            mixpanel.track(event_name, properties or {})
    except Exception as e:
        # Log the error but don't break the application
        print(f"Mixpanel tracking error: {str(e)}")

def identify_user(user_id, properties=None):
    """
    Identify a user in Mixpanel
    
    Args:
        user_id (str): User ID to identify
        properties (dict): User properties
    """
    try:
        mixpanel.people_set(user_id, properties or {})
    except Exception as e:
        print(f"Mixpanel identification error: {str(e)}") 