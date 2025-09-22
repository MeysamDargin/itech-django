from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from profiles.services.profile_services import UserService, ProfileService
from profiles.serializers.serializers import (
    BasicUserRegistrationSerializer,
    FullUserRegistrationSerializer,
    UsernameCheckSerializer,
    EmailCheckSerializer,
    ProfileUpdateSerializer,
    UserProfileResponseSerializer,
    AvailabilityResponseSerializer,
    SuccessResponseSerializer,
    ErrorResponseSerializer
)
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_basic(request):
    serializer = BasicUserRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ErrorResponseSerializer({'error': 'Username, email, and password are required.'}).data,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        validated_data = serializer.validated_data
        user = UserService.create_basic_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        session_key = UserService.authenticate_and_login(
            request, 
            validated_data['username'], 
            validated_data['password']
        )
        
        if session_key:
            response_data = SuccessResponseSerializer({
                'message': 'User registered successfully.',
                'sessionid': session_key
            }).data
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                ErrorResponseSerializer({'error': 'Invalid credentials'}).data,
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except ValidationError as e:
        return Response(
            ErrorResponseSerializer({'error': str(e)}).data,
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def register_full(request):
    serializer = FullUserRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            ErrorResponseSerializer({'error': 'Username, email, and password are required.'}).data,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        validated_data = serializer.validated_data
        user = UserService.create_full_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('firstName'),
            last_name=validated_data.get('lastName'),
            address=validated_data.get('address'),
            phone_number=validated_data.get('phoneNumber'),
            age=validated_data.get('age'),
            profile_image=request.FILES.get("profile_image")
        )
        
        response_data = SuccessResponseSerializer({
            'message': 'User registered successfully.',
            'user_id': user.id
        }).data
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response(
            ErrorResponseSerializer({'error': str(e)}).data,
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def profile_update(request):
    try:
        profile = ProfileService.update_profile(request.user, request.POST, request.FILES)
        
        updated_data = {
            'EmailAddress': profile.user.email,
            'username': profile.user.username,
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'job_title': profile.job_title,
            'website': profile.website,
            'bio': profile.bio,
            'phone_number': profile.phone_number,
            'country': profile.country,
            'city_state': profile.city_state,
            'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
            'profile_caver': profile.profile_caver.url if profile.profile_caver else None,
        }
        
        return Response(updated_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            ErrorResponseSerializer({'error': f'خطا در به‌روزرسانی: {str(e)}'}).data,
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def check_username(request):
    try:
        username = request.POST.get('username', '')
        if not username:
            return Response(
                ErrorResponseSerializer({'error': 'Username is required'}).data,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_available = UserService.check_username_availability(username)
        
        if is_available:
            response_data = AvailabilityResponseSerializer({
                'available': True,
                'message': 'نام کاربری مجاز است'
            }).data
        else:
            response_data = AvailabilityResponseSerializer({
                'available': False,
                'message': 'این نام کاربری قبلاً استفاده شده است'
            }).data
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            ErrorResponseSerializer({'error': str(e)}).data,
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def check_email(request):
    try:
        email = request.POST.get('email', '')
        if not email:
            return Response(
                ErrorResponseSerializer({'error': 'Email is required'}).data,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_available = UserService.check_email_availability(email)
        
        if is_available:
            response_data = AvailabilityResponseSerializer({
                'available': True,
                'message': 'ایمیل مجاز است'
            }).data
        else:
            response_data = AvailabilityResponseSerializer({
                'available': False,
                'message': 'این ایمیل قبلاً استفاده شده است'
            }).data
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            ErrorResponseSerializer({'error': str(e)}).data,
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_profile(request):
    username = request.GET.get('username')
    
    if not username:
        return Response(
            ErrorResponseSerializer({'error': 'نام کاربری الزامی است'}).data,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        profile_data = ProfileService.get_user_profile_data(username, request.user)
        response_data = UserProfileResponseSerializer(profile_data).data
        return Response(response_data, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response(
            ErrorResponseSerializer({'error': str(e)}).data,
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"خطا در دریافت پروفایل کاربر: {str(e)}")
        return Response(
            ErrorResponseSerializer({'error': f'خطای سیستمی: {str(e)}'}).data,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )