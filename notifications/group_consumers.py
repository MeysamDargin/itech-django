import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import logging
import datetime
from bson import ObjectId

from config.mongo_utils import get_collection
from django.contrib.auth.models import User
from profiles.models import Profile
from following.models import Follow

logger = logging.getLogger(__name__)
notifications_collection = get_collection("notifications")


class GroupNotificationConsumer(AsyncWebsocketConsumer):
    """
    Handles a single WebSocket connection for a user to receive new article
    notifications from ALL authors they follow.
    """
    async def connect(self):
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        await self.accept()
        logger.info(f"User {self.user.username} connected to the main article feed.")
        
        # Get all authors the user is following
        self.followed_authors_ids = await self.get_followed_authors(self.user.id)
        
        # Subscribe to the feed of each followed author
        for author_id in self.followed_authors_ids:
            group_name = f"new_article_feed_{author_id}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            logger.info(f"User {self.user.username} subscribed to feed: {group_name}")

        # Send an initial list of notifications from all followed authors
        await self.send_initial_feed_notifications()

    async def disconnect(self, close_code):
        if hasattr(self, 'followed_authors_ids'):
            for author_id in self.followed_authors_ids:
                group_name = f"new_article_feed_{author_id}"
                await self.channel_layer.group_discard(group_name, self.channel_name)
        
        logger.info(f"User {self.user.username} disconnected from the main article feed.")

    async def send_initial_feed_notifications(self):
        """
        Fetches and sends the initial list of 'new_article' notifications
        from all followed authors.
        """
        if not self.followed_authors_ids:
            return

        initial_notifications = await self._get_initial_notifications_from_db(
            follower_id=self.user.id,
            author_ids=self.followed_authors_ids
        )
        
        enriched_notifications = []
        for notif in initial_notifications:
            enriched_data = await self._enrich_notification(notif)
            if enriched_data:
                enriched_notifications.append(enriched_data)

        initial_payload = {
            "type": "initial_article_feed",
            "notifications": enriched_notifications,
        }
        await self.send(text_data=json.dumps(initial_payload))
        logger.info(f"Sent {len(enriched_notifications)} initial article notifications to {self.user.username}")

    async def new_article_notification(self, event):
        """
        Handler for real-time signals sent from the create_article view.
        """
        notification_data = event.get('data', {})
        
        # Construct the final payload to be sent to the client
        final_payload = {
            "type": "new_article_notification",
            "notification": notification_data,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        await self.send(text_data=json.dumps(final_payload))
        logger.info(f"Sent real-time new article notification to user {self.user.username}")

    def _serialize_target(self, target):
        """
        Recursively serialize a dictionary, converting ObjectId to string.
        """
        if not isinstance(target, dict):
            return target
        
        serialized = {}
        for key, value in target.items():
            if isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, dict):
                serialized[key] = self._serialize_target(value)
            else:
                serialized[key] = value
        return serialized

    async def _enrich_notification(self, notification):
        """
        Enriches a notification from the DB with details like actor username/profile.
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
        
        return {
            "notification_id": str(notification.get("_id")),
            "user_id": notification.get("user_id"),
            "type": notification.get("type"),
            "actor_id": actor_id,
            "actor_username": actor_username,
            "actor_profile_img": actor_profile_img,
            "target_id": self._serialize_target(notification.get("target")),
            "created_at": created_at_iso,
            "read": notification.get("is_read", False),
            "extra_data": notification.get("extra_data", {})
        }

    @database_sync_to_async
    def _get_initial_notifications_from_db(self, follower_id, author_ids):
        return list(notifications_collection.find({
            "type": "new_article",
            "user_id": follower_id,
            "actor_id": {"$in": author_ids} # Find articles from all followed authors
        }).sort("created_at", -1).limit(50))

    @database_sync_to_async
    def get_followed_authors(self, user_id):
        """Returns a list of IDs of users that the given user_id is following."""
        return list(Follow.objects.filter(follower_id=user_id).values_list('followed_id', flat=True))

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
