from django.urls import re_path
from profiles.consumers import ChengProfilesConsumer
from accounts.consumers.user_update_consumer import UserUpdateConsumer
from articles.consumers import ChengArticlesConsumer
from comments.consumers.consumers import CommentsConsumer
from temporalBehavior.consumers import TemporalBehaviorConsumer
from notifications.consumers import NotificationConsumer
from notifications.group_consumers import GroupNotificationConsumer # Import the new consumer

websocket_urlpatterns = [
    re_path(r'ws/ChengProfiles/', ChengProfilesConsumer.as_asgi()),
    re_path(r'ws/ChengUsers/', UserUpdateConsumer.as_asgi()),
    re_path(r'ws/ChengArticles/', ChengArticlesConsumer.as_asgi()),
    re_path(r'ws/comments/', CommentsConsumer.as_asgi()),
    re_path(r'ws/temporal-behavior/', TemporalBehaviorConsumer.as_asgi()),
    re_path(r'ws/notifications/feed/', GroupNotificationConsumer.as_asgi()), # Changed
    re_path(r'ws/notifications/', NotificationConsumer.as_asgi()),
]
