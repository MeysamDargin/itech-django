from rest_framework import serializers
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile


class FilterLinksSerializer(serializers.Serializer):
    """Serializer for filtering new links"""
    link = serializers.URLField()
    title = serializers.CharField(max_length=500)
    category = serializers.CharField(max_length=100)


class ArticleListSerializer(serializers.Serializer):
    """Serializer for article list response"""
    id = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    imgCover = serializers.URLField()
    username = serializers.CharField()
    profilePicture = serializers.URLField()
    createdAt = serializers.DateTimeField()
    likes_count = serializers.IntegerField()
    comments_count = serializers.IntegerField()
    reads_count = serializers.IntegerField()


class ArticleDetailSerializer(serializers.Serializer):
    """Serializer for detailed article response"""
    id = serializers.CharField()
    title = serializers.CharField()
    user_id_login = serializers.IntegerField(required=False, allow_null=True)
    text = serializers.CharField()
    delta = serializers.CharField()
    category = serializers.CharField()
    imgCover = serializers.URLField()
    userId = serializers.IntegerField()
    collection = serializers.CharField()
    createdAt = serializers.DateTimeField()
    updatedAt = serializers.DateTimeField()
    username = serializers.CharField()
    bio = serializers.CharField()
    profilePicture = serializers.URLField()
    likes_count = serializers.IntegerField()
    comments_count = serializers.IntegerField()
    reads_count = serializers.IntegerField()
    isLiked = serializers.BooleanField()
    isSaved = serializers.BooleanField()


class CreateArticleSerializer(serializers.Serializer):
    """Serializer for creating articles"""
    title = serializers.CharField(max_length=500)
    text = serializers.CharField()
    delta = serializers.CharField()
    category = serializers.CharField(max_length=100)
    imgCover = serializers.ImageField()

    def validate_imgCover(self, value):
        """Validate image file"""
        if not isinstance(value, (InMemoryUploadedFile, TemporaryUploadedFile)):
            raise serializers.ValidationError("Invalid image file")
        
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Image file too large (max 10MB)")
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Invalid image type. Only JPEG, PNG, and WebP are allowed")
        
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        if not attrs.get('title') or not attrs.get('text') or not attrs.get('delta'):
            raise serializers.ValidationError("Title, text, and delta are required")
        return attrs


class UpdateArticleSerializer(serializers.Serializer):
    """Serializer for updating articles"""
    title = serializers.CharField(max_length=500, required=False)
    text = serializers.CharField(required=False)
    delta = serializers.CharField(required=False)
    category = serializers.CharField(max_length=100, required=False)
    imgCover = serializers.ImageField(required=False)

    def validate_imgCover(self, value):
        """Validate image file"""
        if value and not isinstance(value, (InMemoryUploadedFile, TemporaryUploadedFile)):
            raise serializers.ValidationError("Invalid image file")
        
        if value and value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Image file too large (max 10MB)")
        
        if value:
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Invalid image type. Only JPEG, PNG, and WebP are allowed")
        
        return value


class ToggleLikeSerializer(serializers.Serializer):
    """Serializer for toggle like response"""
    status = serializers.CharField()
    message = serializers.CharField()
    liked = serializers.BooleanField()
    like_id = serializers.CharField(required=False)


class TrackReadSerializer(serializers.Serializer):
    """Serializer for tracking article reads"""
    article_id = serializers.CharField()
    source = serializers.CharField(default='unknown')
    device = serializers.CharField(default='unknown')
    duration = serializers.IntegerField(required=False, min_value=0)
    read_percentage = serializers.IntegerField(required=False, min_value=0, max_value=100)

    def validate_article_id(self, value):
        """Validate ObjectId format"""
        from bson import ObjectId
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError("Invalid article ID format")
        return value


class UploadImageSerializer(serializers.Serializer):
    """Serializer for image upload"""
    image = serializers.ImageField()

    def validate_image(self, value):
        """Validate uploaded image"""
        if not isinstance(value, (InMemoryUploadedFile, TemporaryUploadedFile)):
            raise serializers.ValidationError("Invalid image file")
        
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Image file too large (max 10MB)")
        
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Invalid image type. Only JPEG, PNG, and WebP are allowed")
        
        return value


class SaveDirectorySerializer(serializers.Serializer):
    """Serializer for save directories"""
    id = serializers.CharField()
    name = serializers.CharField()
    createdAt = serializers.DateTimeField()
    articleCount = serializers.IntegerField()


class CreateSaveDirectorySerializer(serializers.Serializer):
    """Serializer for creating save directories"""
    name = serializers.CharField(max_length=100)

    def validate_name(self, value):
        """Validate directory name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Directory name cannot be empty")
        return value.strip()


class UpdateSaveDirectorySerializer(serializers.Serializer):
    """Serializer for updating save directories"""
    name = serializers.CharField(max_length=100)

    def validate_name(self, value):
        """Validate directory name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Directory name cannot be empty")
        return value.strip()


class ToggleSaveSerializer(serializers.Serializer):
    """Serializer for toggling save status"""
    directoryId = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_directoryId(self, value):
        """Validate directory ID"""
        if value:
            from bson import ObjectId
            if not ObjectId.is_valid(value):
                raise serializers.ValidationError("Invalid directory ID format")
        return value


class SavedArticleDetailsSerializer(serializers.Serializer):
    """Serializer for saved article details"""
    id = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    imgCover = serializers.URLField()
    username = serializers.CharField()
    profilePicture = serializers.URLField()
    createdAt = serializers.DateTimeField()
    likes_count = serializers.IntegerField()
    comments_count = serializers.IntegerField()
    reads_count = serializers.IntegerField()


class SaveDetailsSerializer(serializers.Serializer):
    """Serializer for save details"""
    save_id = serializers.CharField()
    articleId = serializers.CharField()
    userId = serializers.IntegerField()
    directoryId = serializers.CharField(allow_null=True)
    createdAt = serializers.DateTimeField()


class SavedItemSerializer(serializers.Serializer):
    """Serializer for combined saved item"""
    save_details = SaveDetailsSerializer()
    article_details = SavedArticleDetailsSerializer()


class CheckSavedSerializer(serializers.Serializer):
    """Serializer for checking saved status"""
    status = serializers.CharField()
    is_saved = serializers.BooleanField()
    save_id = serializers.CharField(allow_null=True)
    directory = serializers.DictField(allow_null=True)


class TimeBasedArticleSerializer(serializers.Serializer):
    """Serializer for time-based articles (morning, afternoon, night)"""
    id = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    imgCover = serializers.URLField()
    createdAt = serializers.DateTimeField()


class StandardResponseSerializer(serializers.Serializer):
    """Standard API response serializer"""
    status = serializers.CharField()
    message = serializers.CharField(required=False)
    data = serializers.DictField(required=False)


class PaginatedResponseSerializer(serializers.Serializer):
    """Paginated response serializer"""
    status = serializers.CharField()
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = serializers.ListField()


class ErrorResponseSerializer(serializers.Serializer):
    """Error response serializer"""
    status = serializers.CharField(default='error')
    message = serializers.CharField()
    errors = serializers.DictField(required=False)