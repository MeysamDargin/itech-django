from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import login, logout
from accounts.api.services.auth_services import authenticate_user, is_new_user
from accounts.serializers.auth_serializers import LoginSerializer

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user, error = authenticate_user(username, password)
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        login(request, user)
        new_user = is_new_user(user)

        return Response({
            'message': 'Logged in',
            'sessionid': request.session.session_key,
            'newUser': new_user
        })


class LogoutAPIView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out'})
