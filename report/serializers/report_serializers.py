from rest_framework import serializers

class ReportSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, write_only=True)
    article = serializers.CharField(required=True,)
