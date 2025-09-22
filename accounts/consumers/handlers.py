from django.contrib.auth.models import User
from asgiref.sync import sync_to_async


@sync_to_async
def get_user_data(user_id):
    try:
        user = User.objects.prefetch_related("groups").get(id=user_id)
        return {
            "action": "updated",
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "date_joined": user.date_joined.isoformat(),
            "groups": list(user.groups.values_list("name", flat=True)),
        }
    except User.DoesNotExist:
        return None


@sync_to_async
def get_user_object(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


async def update_user_data(user_id, data):
    user = await get_user_object(user_id)
    if not user:
        return
    user.username = data.get("username", user.username)
    user.email = data.get("email", user.email)
    await sync_to_async(user.save)()
