from django.contrib.auth.models import User
from following.models import Follow
from following.api.services.notification_service import send_follow_notification
from following.utils.mutual_follow import update_mutual_follow_status
import logging

logger = logging.getLogger(__name__)

def handle_follow_toggle(actor_user, target_user_id):

    if str(actor_user.id) == str(target_user_id):
        return {
            'status': 'error',
            'message': 'You cannot follow yourself',
            'code': 400
        }

    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return {
            'status': 'error',
            'message': 'User not found',
            'code': 404
        }

    follow_exists = Follow.objects.filter(follower=actor_user, followed=target_user).exists()

    if follow_exists:
        Follow.objects.filter(follower=actor_user, followed=target_user).delete()
        update_mutual_follow_status(actor_user.id, target_user.id)

        return {
            'status': 'success',
            'action': 'unfollow',
            'message': f'You have unfollowed {target_user.username}',
            'code': 200
        }

    else:
        Follow.objects.create(follower=actor_user, followed=target_user)
        send_follow_notification(actor_user, target_user)
        update_mutual_follow_status(actor_user.id, target_user.id)

        return {
            'status': 'success',
            'action': 'follow',
            'message': f'You are now following {target_user.username}',
            'code': 200
        }
