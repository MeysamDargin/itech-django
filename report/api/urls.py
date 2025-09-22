from django.urls import path
from ..views.report import CreateReportAPIView

urlpatterns = [
    path('create-report/', CreateReportAPIView.as_view(), name='api-create-feedback'),
]
