from rest_framework import serializers


class ProcessArticlesSerializer(serializers.Serializer):
    articles = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    title = serializers.CharField(required=False, allow_blank=True)
    text = serializers.JSONField(required=False)
    articleId = serializers.CharField(required=False)

    def validate(self, data):
        if 'articles' not in data:
            single_article = {}
            if 'title' in data:
                single_article['title'] = data['title']
            if 'text' in data:
                single_article['text'] = data['text']
            if 'articleId' in data:
                single_article['articleId'] = data['articleId']
            
            if single_article:
                data['articles'] = [single_article]
            else:
                raise serializers.ValidationError("Either 'articles' list or individual article fields are required")
        
        return data


class DebugArticleSerializer(serializers.Serializer):
    articleId = serializers.CharField(required=True)


class FindSimilarArticlesSerializer(serializers.Serializer):
    userId = serializers.IntegerField(required=True)
    limit = serializers.IntegerField(required=False, default=10, min_value=1, max_value=50)


class ArticleResponseSerializer(serializers.Serializer):
    articleId = serializers.CharField()
    title = serializers.CharField()
    title_embedding = serializers.ListField(child=serializers.FloatField())
    text_embedding = serializers.ListField(child=serializers.FloatField())
    cleaned_text = serializers.CharField()


class ProcessArticlesResponseSerializer(serializers.Serializer):
    articles = ArticleResponseSerializer(many=True)


class SimilarArticleSerializer(serializers.Serializer):
    articleId = serializers.CharField()
    title = serializers.CharField()
    similarity = serializers.FloatField()


class FindSimilarArticlesResponseSerializer(serializers.Serializer):
    userId = serializers.IntegerField()
    similarArticles = SimilarArticleSerializer(many=True)
    count = serializers.IntegerField()