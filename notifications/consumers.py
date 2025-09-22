import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import logging
import datetime
from bson import ObjectId

from config.mongo_utils import get_collection
from django.contrib.auth.models import User
from profiles.models import Profile

logger = logging.getLogger(__name__)
notifications_collection = get_collection("notifications")


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    A consumer that handles WebSocket connections for user notifications.
    Each user has a private channel, and the consumer pushes notifications
    sent from other parts of the application to the connected client.
    """
    async def connect(self):
        self.user = self.scope.get("user")

        if self.user is None or not self.user.is_authenticated:
            logger.warning("Unauthenticated user tried to connect to notifications WebSocket.")
            await self.close()
            return

        self.group_name = f"notification_user_{self.user.id}"
        logger.info(f"User {self.user.username} joining notification group: {self.group_name}")

        # Join the user-specific group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"User {self.user.username} connected to notifications WebSocket.")

        # Send initial notifications to the newly connected client
        await self.send_initial_notifications()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"User {self.user.username} disconnected from notifications WebSocket.")

    async def receive(self, text_data):
        """
        Handle messages received from the client
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            logger.info(f"Received message from client {self.user.username}: {message_type}")
            
            if message_type == 'get_notifications':
                await self.send_initial_notifications()
            elif message_type == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_as_read(notification_id)
            elif message_type == 'mark_all_read':
                await self.mark_all_notifications_as_read()
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from client {self.user.username}: {text_data}")
        except Exception as e:
            logger.error(f"Error processing message from client {self.user.username}: {e}", exc_info=True)

    async def send_initial_notifications(self):
        """
        Fetches all notifications for the user from MongoDB, enriches them,
        and sends them as a single initial payload.
        """
        try:
            user_notifications = await self._get_user_notifications_from_db(self.user.id)
            enriched_notifications = []
            for notif in user_notifications:
                enriched_data = await self._enrich_notification(notif)
                if enriched_data:
                    enriched_notifications.append(enriched_data)
            
            initial_payload = {
                "type": "notifications_list",
                "notifications": enriched_notifications,
                "created_at": datetime.datetime.now().isoformat()
            }

            await self.send(text_data=json.dumps(initial_payload))
            logger.info(f"Sent {len(enriched_notifications)} initial notifications to {self.user.username}")

        except Exception as e:
            logger.error(f"Error sending initial notifications to {self.user.username}: {e}", exc_info=True)

    async def mark_notification_as_read(self, notification_id):
        """
        Mark a specific notification as read
        """
        try:
            await self._mark_notification_read_in_db(notification_id)
            
            # Send confirmation back to client
            response = {
                "type": "notification_read",
                "notification_id": notification_id,
                "status": "success"
            }
            await self.send(text_data=json.dumps(response))
            logger.info(f"Marked notification {notification_id} as read for user {self.user.username}")
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}", exc_info=True)

    async def mark_all_notifications_as_read(self):
        """
        Mark all notifications as read for the user
        """
        try:
            await self._mark_all_notifications_read_in_db(self.user.id)
            
            # Send confirmation back to client
            response = {
                "type": "notification_read",
                "all_read": True,
                "status": "success"
            }
            await self.send(text_data=json.dumps(response))
            logger.info(f"Marked all notifications as read for user {self.user.username}")
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}", exc_info=True)

    def _serialize_target(self, target):
        """
        Serialize target field, handling both ObjectId and complex objects.
        """
        if target is None:
            return None
        
        if isinstance(target, dict):
            # برای نوتیفیکیشن‌های like که target یک object است
            serialized_target = {}
            for key, value in target.items():
                if isinstance(value, ObjectId):
                    serialized_target[key] = str(value)
                else:
                    serialized_target[key] = value
            return serialized_target
        elif isinstance(target, ObjectId):
            # برای نوتیفیکیشن‌های ساده که target یک ObjectId است
            return str(target)
        else:
            # برای سایر انواع
            return target

    async def _enrich_notification(self, notification):
        """
        Enriches a notification with actor's username and profile image.
        """
        actor_id = notification.get("actor_id")
        if not actor_id:
            return None

        actor_user = await self._get_user_instance(actor_id)
        actor_profile = await self._get_profile_instance(actor_id)
        
        actor_username = actor_user.username if actor_user else "Unknown User"
        actor_profile_img = actor_profile.profile_picture.url if actor_profile and actor_profile.profile_picture else None

        created_at_dt = notification.get("created_at")
        created_at_iso = created_at_dt.isoformat() if isinstance(created_at_dt, datetime.datetime) else str(created_at_dt)

        # Serialize target field properly
        target_serialized = self._serialize_target(notification.get("target"))

        # Reconstruct the payload to match the desired format
        return {
            "notification_id": str(notification.get("_id")),
            "user_id": notification.get("user_id"),
            "type": notification.get("type"),
            "actor_id": actor_id,
            "actor_username": actor_username,
            "actor_profile_img": actor_profile_img,
            "target_id": target_serialized,  # استفاده از target serialize شده
            "created_at": created_at_iso,
            "read": notification.get("is_read", False),
            "is_mutual_follow": notification.get("is_mutual_follow", False),
            "extra_data": notification.get("extra_data", {})
        }

    @database_sync_to_async
    def _get_user_notifications_from_db(self, user_id):
        return list(notifications_collection.find({"user_id": user_id}).sort("created_at", -1))

    @database_sync_to_async
    def _get_user_instance(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def _get_profile_instance(self, user_id):
        try:
            return Profile.objects.select_related('user').get(user_id=user_id)
        except Profile.DoesNotExist:
            return None

    @database_sync_to_async
    def _mark_notification_read_in_db(self, notification_id):
        """
        Mark a notification as read in MongoDB
        """
        try:
            result = notifications_collection.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": {"is_read": True}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating notification in DB: {e}")
            return False

    @database_sync_to_async
    def _mark_all_notifications_read_in_db(self, user_id):
        """
        Mark all notifications as read for a user in MongoDB
        """
        try:
            result = notifications_collection.update_many(
                {"user_id": user_id, "is_read": False},
                {"$set": {"is_read": True}}
            )
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating notifications in DB: {e}")
            return 0

    async def send_notification(self, event):
        """
        Handler for messages sent to the user's notification group.
        It forwards the notification to the client in the required format.
        """
        logger.info(f"NOTIFICATION HANDLER CALLED with event: {event}")
        
        # The event dictionary contains the data sent from the view
        notification_data = event.get('data', {})
        
        # Enrich the notification data
        enriched_data = await self._enrich_notification(notification_data)
        
        # Construct the final payload to be sent to the client
        payload = {
            'type': 'new_notification',
            'notification': enriched_data,
            'created_at': notification_data.get('created_at')
        }

        # Log the payload before sending
        logger.info(f"Sending notification payload to user {self.user.username}: {json.dumps(payload, indent=2)}")

        # Send the payload to the WebSocket client
        await self.send(text_data=json.dumps(payload))
        logger.info(f"Sent notification to user {self.user.username}: {payload.get('type')}")