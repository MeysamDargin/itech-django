from django.urls import path
from ai.views.ai import (
    ProcessArticlesView,
    DebugArticleDataView,
    FindSimilarArticlesView,
    GenerateUserEmbeddingView
)

urlpatterns = [
    path('process-articles/', ProcessArticlesView.as_view(), name='process_articles_with_embeddings'),
    path('debug-article/', DebugArticleDataView.as_view(), name='debug_article_data'),
    path('find-similar-articles/', FindSimilarArticlesView.as_view(), name='find_similar_articles'),
    path('generate-embedding/', GenerateUserEmbeddingView.as_view(), name='generate_user_embedding'),

] 