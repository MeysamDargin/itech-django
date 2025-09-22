import json
from channels.generic.websocket import WebsocketConsumer
from channels.auth import get_user
from django.contrib.auth.models import AnonymousUser
from datetime import datetime
import pymongo
from config.mongo_utils import insert_document
import logging

logger = logging.getLogger(__name__)

class TemporalBehaviorConsumer(WebsocketConsumer):
    """
    WebSocket consumer that tracks user login and logout times.
    When a user connects, it records the login time, and when they disconnect,
    it records the logout time in MongoDB.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.login_time = None
        self.session_id = None
        self.ip_address = None
    
    def connect(self):
        # Get the authenticated user
        self.user = self.scope.get('user', AnonymousUser())
        self.session_id = self.scope.get('session', {}).get('session_key', None)
        
        # Extract the real IP address
        headers = dict(self.scope['headers'])
        x_forwarded_for = headers.get(b'x-forwarded-for')
        if x_forwarded_for:
            self.ip_address = x_forwarded_for.decode().split(',')[0].strip()
        else:
            client = self.scope.get('client')
            self.ip_address = client[0] if client else "unknown"
        
        # Only allow authenticated users
        if self.user.is_authenticated:
            # Accept the connection
            self.accept()
            
            # Record login time
            self.login_time = datetime.now()
            
            # Log the connection
            logger.info(f"User {self.user.id} connected from IP {self.ip_address} at {self.login_time}")
            
            # Send confirmation message to client
            self.send(text_data=json.dumps({
                'type': 'connection_established',
                'user_id': self.user.id,
                'login_time': self.login_time.isoformat()
            }))
        else:
            # Reject the connection if user is not authenticated
            logger.warning("Unauthenticated user attempted to connect")
            self.close()
    
    def disconnect(self, close_code):
        # Only record if user was authenticated and connection was accepted
        if self.user and self.user.is_authenticated and self.login_time:
            # Record logout time
            logout_time = datetime.now()
            
            # Calculate session duration in seconds
            duration_seconds = (logout_time - self.login_time).total_seconds()
            
            # Create document to store in MongoDB
            temporal_data = {
                'user_id': self.user.id,
                'username': self.user.username,
                'session_id': self.session_id,
                'ip_address': self.ip_address,
                'login_time': self.login_time,
                'logout_time': logout_time,
                'duration_seconds': duration_seconds,
                'created_at': datetime.now()
            }
            
            try:
                # Store the document in MongoDB
                insert_document('temporalBehavior', temporal_data)
                logger.info(f"User {self.user.id} session recorded from IP {self.ip_address}: login at {self.login_time}, logout at {logout_time}")
            except Exception as e:
                logger.error(f"Error saving temporal behavior data: {str(e)}")
    
    def receive(self, text_data):
        """
        Handle messages from client (if needed)
        """
        try:
            data = json.loads(text_data)
            # You can add custom message handling here if needed
            
            # Echo back the message as acknowledgement
            self.send(text_data=json.dumps({
                'type': 'echo',
                'message': data
            }))
        except json.JSONDecodeError:
            logger.error("Received invalid JSON data")
