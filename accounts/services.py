from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from typing import Literal

channel_layer = get_channel_layer()

def send_user_update(action: Literal['created', 'updated', 'deleted'], user: User) -> None:
    """
    Send a message to the 'User_group' channel layer about user model changes.
    """
    async_to_sync(channel_layer.group_send)(
        "User_group",
        {
            "type": "send_model_update",
            "data": {
                "action": action,
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "date_joined": user.date_joined.isoformat(),
                "groups": list(user.groups.values_list('name', flat=True)),
            },
        },
    )
