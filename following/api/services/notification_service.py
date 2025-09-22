import datetime
from config.mongo_utils import insert_document
from profiles.models import Profile
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from following.models import Follow

logger = logging.getLogger(__name__)

def send_follow_notification(actor_user, followed_user):
    now = datetime.datetime.now()
    is_mutual_follow = Follow.objects.filter(follower=followed_user, followed=actor_user).exists()

    notification_doc = {
        "user_id": followed_user.id,
        "type": "follow",
        "actor_id": actor_user.id,
        "target": None,
        "created_at": now,
        "is_read": False,
        "is_mutual_follow": is_mutual_follow,
        "extra_data": None,
    }
    insert_document('notifications', notification_doc)

    actor_profile_img = ""
    try:
        profile = Profile.objects.get(user=actor_user)
        if profile.profile_picture:
            actor_profile_img = profile.profile_picture.url
    except Profile.DoesNotExist:
        pass

    payload = {
        "user_id": followed_user.id,
        "type": "follow",
        "actor_id": actor_user.id,
        "actor_username": actor_user.username,
        "actor_profile_img": actor_profile_img,
        "target": None,
        "created_at": now.isoformat(),
        "is_read": False,
        "is_mutual_follow": is_mutual_follow,
        "extra_data": None,
    }

    group_name = f"notification_user_{followed_user.id}"
    logger.info(f"Sending notification to group: {group_name}")
    
    async_to_sync(get_channel_layer().group_send)(
        group_name,
        {
            "type": "send_notification",
            "data": payload,
        }
    )
    logger.info(f"Sent 'follow' notification to user {followed_user.username}")
