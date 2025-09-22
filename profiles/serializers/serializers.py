from rest_framework import serializers

class BasicUserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(min_length=6, required=True)

class FullUserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(min_length=6, required=True)
    firstName = serializers.CharField(max_length=30, required=False, allow_blank=True)
    lastName = serializers.CharField(max_length=30, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    phoneNumber = serializers.CharField(required=False, allow_blank=True)
    age = serializers.CharField(required=False, allow_blank=True)
    profile_image = serializers.ImageField(required=False)

class UsernameCheckSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)

class EmailCheckSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class ProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    job_title = serializers.CharField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    city_state = serializers.CharField(required=False, allow_blank=True)
    EmailAddress = serializers.EmailField(required=False)
    profile_picture = serializers.ImageField(required=False)
    profile_caver = serializers.ImageField(required=False)

class UserProfileResponseSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    job_title = serializers.CharField()
    website = serializers.CharField()
    bio = serializers.CharField()
    phone_number = serializers.CharField()
    country = serializers.CharField()
    city_state = serializers.CharField()
    profile_picture = serializers.CharField()
    profile_caver = serializers.CharField()
    followers_count = serializers.IntegerField()
    following_count = serializers.IntegerField()
    articles_count = serializers.IntegerField()
    articles = serializers.ListField()
    is_following = serializers.BooleanField()

class AvailabilityResponseSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    message = serializers.CharField()

class SuccessResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    user_id = serializers.IntegerField(required=False)
    sessionid = serializers.CharField(required=False)

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()