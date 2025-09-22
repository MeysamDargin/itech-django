from django.urls import path
from ..views.search import SearchArticlesView, UserSearchHistoryView

urlpatterns = [
    path('search/', SearchArticlesView.as_view(), name='api-search'),
    path('search-history/', UserSearchHistoryView.as_view(), name='api-search-history'),
]
