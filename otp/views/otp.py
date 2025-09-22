from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from otp.models import OTP
from otp.utils.utils import send_otp_to_user, generate_otp
from django.contrib.auth.models import User
import logging
logger = logging.getLogger(__name__)

class SendOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'E-Mail erforderlich'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Diese E-Mail ist bereits registriert'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            success = send_otp_to_user(email)
            if success:
                return Response({'message': 'Ein Bestätigungscode wurde an Ihre E-Mail gesendet'}, 
                              status=status.HTTP_200_OK)
            return Response({'error': 'Fehler beim Senden des Codes'}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error in OTP sending: {str(e)}")
            return Response({'error': f'Fehler beim Senden des Codes: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp')
        
        if not email or not otp_code:
            return Response({'error': 'E-Mail und OTP erforderlich'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            otp = OTP.objects.filter(email=email, otp_code=otp_code).latest('created_at')
            if otp.is_valid():
                otp.is_used = True
                otp.save()
                return Response(status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Code ungültig oder abgelaufen'}, status=status.HTTP_400_BAD_REQUEST)
        except OTP.DoesNotExist:
            return Response({'error': 'Ungültiger Code oder E-Mail'}, status=status.HTTP_400_BAD_REQUEST)