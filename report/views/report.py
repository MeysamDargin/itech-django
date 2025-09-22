import datetime
from bson import ObjectId
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from config.mongo_utils import get_collection
from report.serializers.report_serializers import ReportSerializer

class CreateReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        message = serializer.validated_data['message']
        article = serializer.validated_data['article']
        now = datetime.datetime.utcnow()

        report_to_save = {
            "article_id": ObjectId(article),
            "user_id": request.user.id,
            "message": message,
            "created_at": now,
            "seen": False
        }

        report_collection = get_collection('report')
        result = report_collection.insert_one(report_to_save)
        inserted_id = str(result.inserted_id)

        return Response({
            'message': 'send report!',
            'article_id': article,
            'report_id': inserted_id,
        }, status=status.HTTP_201_CREATED)
