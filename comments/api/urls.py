from django.urls import path
from ..views.comment_views import (
    CreateCommentView,
    UpdateCommentView,
    DeleteCommentView,
    SeenCommentsView,
)

urlpatterns = [
    path('create/', CreateCommentView.as_view(), name='create-comment'),
    path('update/<str:comment_id>/', UpdateCommentView.as_view(), name='update-comment'),
    path('delete/<str:comment_id>/', DeleteCommentView.as_view(), name='delete-comment'),
    path('seen/', SeenCommentsView.as_view(), name='seen-comments'),
]