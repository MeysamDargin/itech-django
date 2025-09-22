from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from .models import Follow
import logging

# تنظیم لاگر
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Follow)
def follow_created(sender, instance, created, **kwargs):
    if created:
        logger.info(f"SIGNAL: Follow created - User {instance.follower.username} followed {instance.followed.username}")
        channel_layer = get_channel_layer()
        # Send to follower's profile group
        logger.info(f"SIGNAL: Sending follow update to follower {instance.follower.id} - following count: {instance.follower.following.count()}, follower count: {instance.follower.followers.count()}")
        async_to_sync(channel_layer.group_send)(
            "Profile_group",
            {
                "type": "send_model_update",
                "data": {
                    "action": "follow_update",
                    "user_id": instance.follower.id,
                    "follower_count": instance.follower.following.count(),
                    "following_count": instance.follower.followers.count(),
                }
            }
        )
        # Send to followed user's profile group
        logger.info(f"SIGNAL: Sending follow update to followed user {instance.followed.id} - following count: {instance.followed.following.count()}, follower count: {instance.followed.followers.count()}")
        async_to_sync(channel_layer.group_send)(
            "Profile_group",
            {
                "type": "send_model_update",
                "data": {
                    "action": "follow_update",
                    "user_id": instance.followed.id,
                    "follower_count": instance.followed.followers.count(),
                    "following_count": instance.followed.following.count(),
                }
            }
        )


@receiver(post_delete, sender=Follow)
def follow_deleted(sender, instance, **kwargs):
    logger.info(f"SIGNAL: Follow deleted - User {instance.follower.username} unfollowed {instance.followed.username}")
    channel_layer = get_channel_layer()
    # Send to follower's profile group
    logger.info(f"SIGNAL: Sending unfollow update to follower {instance.follower.id} - following count: {instance.follower.following.count()}, follower count: {instance.follower.followers.count()}")
    async_to_sync(channel_layer.group_send)(
        "Profile_group",
        {
            "type": "send_model_update",
            "data": {
                "action": "follow_update",
                "user_id": instance.follower.id,
                "follower_count": instance.follower.followers.count(),
                "following_count": instance.follower.following.count(),
            }
        }
    )
    # Send to followed user's profile group
    logger.info(f"SIGNAL: Sending unfollow update to followed user {instance.followed.id} - following count: {instance.followed.following.count()}, follower count: {instance.followed.followers.count()}")
    async_to_sync(channel_layer.group_send)(
        "Profile_group",
        {
            "type": "send_model_update",
            "data": {
                "action": "follow_update",
                "user_id": instance.followed.id,
                "follower_count": instance.followed.followers.count(),
                "following_count": instance.followed.following.count(),
            }
        }
    ) 