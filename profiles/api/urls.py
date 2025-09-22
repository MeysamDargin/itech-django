from django.urls import path
from profiles.views import profile

urlpatterns = [
    path('register/', profile.register_full, name='register'),
    path('register-basic/', profile.register_basic, name='register_basic'),
    path('update/', profile.profile_update, name='profile_update'),
    # path('logout/', views.logout_view, name='logout'),
    path('check-username/', profile.check_username, name='check_username'),
    path('check-email/', profile.check_email, name='check_email'),
    path('get-user-profile/', profile.get_user_profile, name='get_user_profile'),
]
