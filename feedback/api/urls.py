from django.urls import path
from ..views.feedback import CreateFeedbackAPIView

urlpatterns = [
    path('create-feedback/', CreateFeedbackAPIView.as_view(), name='api-create-feedback'),
]
