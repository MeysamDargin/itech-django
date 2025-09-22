from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from following.api.services.follow_service import handle_follow_toggle

class ToggleFollowAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id_to_follow = request.data.get('user_id')

        if not user_id_to_follow:
            return Response(
                {'status': 'error', 'message': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = handle_follow_toggle(request.user, user_id_to_follow)
        status_code = result.pop("code", 200)

        return Response(result, status=status_code)
