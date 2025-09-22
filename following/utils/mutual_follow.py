from following.models import Follow
from config.mongo_utils import get_collection
import logging

logger = logging.getLogger(__name__)
notifications_collection = get_collection('notifications')

def update_mutual_follow_status(user1_id, user2_id):
    try:
        is_user1_following_user2 = Follow.objects.filter(follower_id=user1_id, followed_id=user2_id).exists()
        is_user2_following_user1 = Follow.objects.filter(follower_id=user2_id, followed_id=user1_id).exists()

        notifications_collection.update_many(
            {"type": "follow", "actor_id": user1_id, "user_id": user2_id},
            {"$set": {"is_mutual_follow": is_user2_following_user1}}
        )
        notifications_collection.update_many(
            {"type": "follow", "actor_id": user2_id, "user_id": user1_id},
            {"$set": {"is_mutual_follow": is_user1_following_user2}}
        )
        logger.info(f"Updated mutual follow status between users {user1_id} and {user2_id}")
    except Exception as e:
        logger.error(f"Error updating mutual follow status: {str(e)}")
