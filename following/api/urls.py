from django.urls import path
from following.views.toggle import ToggleFollowAPIView

app_name = "following"

urlpatterns = [
    path("toggle/", ToggleFollowAPIView.as_view(), name="toggle_follow"),
]
