from django.urls import path
from ..views.auth_views import LoginAPIView, LogoutAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='api-login'),
    path('logout/', LogoutAPIView.as_view(), name='api-logout'),
]
