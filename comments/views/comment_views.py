from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from ..serializers.comment_serializers import CommentSerializer, SeenCommentsSerializer
from ..services.comment_services import (
    create_comment_service,
    update_comment_service,
    delete_comment_service,
    seen_comments_service,
)

class CreateCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user_id'] = request.user.id

        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            try:
                comment = create_comment_service(serializer.validated_data, request.user)
                return Response(comment, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id, *args, **kwargs):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                comment = update_comment_service(comment_id, serializer.validated_data, request.user)
                return Response(comment, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeleteCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id, *args, **kwargs):
        try:
            deleted_comment_id = delete_comment_service(comment_id, request.user)
            return Response({"success": True, "comment_id": deleted_comment_id}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SeenCommentsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = SeenCommentsSerializer(data=request.data)
        if serializer.is_valid():
            try:
                result = seen_comments_service(serializer.validated_data)
                return Response(result, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)