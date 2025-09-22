from django.contrib.auth import authenticate
from profiles.models import Profile

def authenticate_user(username: str, password: str):
    user = authenticate(username=username, password=password)
    if not user:
        return None, "Invalid credentials"
    return user, None

def is_new_user(user) -> bool:
    try:
        profile = Profile.objects.get(user=user)
        return not (profile.first_name and profile.last_name)
    except Profile.DoesNotExist:
        return True
