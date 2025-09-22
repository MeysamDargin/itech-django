from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('otp/', include('otp.api.urls')),
    path('accounts/', include('accounts.api.urls')),
    path('profiles/', include('profiles.api.urls')),
    path('articles/', include('articles.api.urls')),
    path('comments/', include('comments.api.urls')),
    path('following/', include('following.api.urls')),
    path('feedback/', include('feedback.api.urls')),
    path('report/', include('report.api.urls')),
    path('search/', include('search.api.urls')),
    path('ai/', include('ai.api.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 