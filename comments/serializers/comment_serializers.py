from rest_framework import serializers

class CommentSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True)
    article_id = serializers.CharField()
    user_id = serializers.IntegerField()
    message = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    reply_to = serializers.CharField(required=False, allow_null=True)
    seen = serializers.BooleanField(read_only=True, default=False)
    user_info = serializers.DictField(read_only=True)

class SeenCommentsSerializer(serializers.Serializer):
    article_id = serializers.CharField()
    comment_ids = serializers.ListField(
        child=serializers.CharField()
    )