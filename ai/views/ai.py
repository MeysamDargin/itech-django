import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from ai.serializers.serializers import (
    ProcessArticlesSerializer,
    ProcessArticlesResponseSerializer,
    DebugArticleSerializer,
    FindSimilarArticlesSerializer,
    FindSimilarArticlesResponseSerializer
)
from ai.services.ai_services import (
    ArticleProcessingService,
    DebugService,
    SimilarityService
)

logger = logging.getLogger(__name__)


class ProcessArticlesView(APIView):
    """
    پردازش مقالات و ایجاد embedding برای آنها
    """
    
    @swagger_auto_schema(
        request_body=ProcessArticlesSerializer,
        responses={200: ProcessArticlesResponseSerializer}
    )
    def post(self, request):
        """پردازش مقالات و ایجاد embedding"""
        try:
            # اعتبارسنجی داده‌های ورودی
            serializer = ProcessArticlesSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid input data', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            validated_data = serializer.validated_data
            articles_data = validated_data.get('articles', [])

            logger.debug(f"Processing {len(articles_data)} articles")
            
            # پردازش مقالات
            processed_articles = ArticleProcessingService.process_articles_list(articles_data)
            
            logger.debug(f"Successfully processed {len(processed_articles)} articles")
            return Response(
                {'articles': processed_articles}, 
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error in ProcessArticlesView: {str(e)}")
            return Response(
                {'error': f'Internal server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DebugArticleDataView(APIView):
    """
    Debug endpoint برای بررسی اطلاعات مقاله در دیتابیس
    """
    
    @swagger_auto_schema(
        request_body=DebugArticleSerializer,
        responses={200: 'Debug information about the article'}
    )
    def post(self, request):
        """دریافت اطلاعات debug برای یک مقاله"""
        try:
            serializer = DebugArticleSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid input data', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            article_id = serializer.validated_data['articleId']
            
            debug_info = DebugService.debug_article_data(article_id)
            
            return Response(debug_info, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in DebugArticleDataView: {str(e)}")
            return Response(
                {'error': f'Internal server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FindSimilarArticlesView(APIView):
    """
    یافتن مقالات مشابه بر اساس embedding کاربر
    """
    
    @swagger_auto_schema(
        request_body=FindSimilarArticlesSerializer,
        responses={200: FindSimilarArticlesResponseSerializer}
    )
    def post(self, request):
        """یافتن مقالات مشابه برای یک کاربر"""
        try:
            serializer = FindSimilarArticlesSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid input data', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            user_id = serializer.validated_data['userId']
            limit = serializer.validated_data['limit']
            
            try:
                similar_articles = SimilarityService.find_similar_articles(user_id, limit)
                
                return Response({
                    "userId": user_id,
                    "similarArticles": similar_articles,
                    "count": len(similar_articles)
                }, status=status.HTTP_200_OK)
                
            except ValueError as ve:
                return Response(
                    {'error': str(ve)}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error in FindSimilarArticlesView: {str(e)}")
            return Response(
                {'error': f'Internal server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateUserEmbeddingView(APIView):
    """
    ایجاد embedding برای کاربر بر اساس تعاملاتش
    """
    
    @swagger_auto_schema(
        request_body=FindSimilarArticlesSerializer,  # استفاده می‌کنیم چون فقط userId لازم داریم
        responses={200: 'User embedding generation result'}
    )
    def post(self, request):
        """ایجاد embedding برای کاربر"""
        try:
            # فقط userId را می‌گیریم
            user_id_raw = request.data.get("userId")
            
            if not user_id_raw:
                return Response(
                    {"error": "userId is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # تبدیل userId به عدد
            try:
                user_id = int(user_id_raw)
            except ValueError:
                return Response(
                    {"error": "userId must be an integer"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from .services import UserEmbeddingService
            result = UserEmbeddingService.generate_user_embedding(user_id)
            
            if "error" in result:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(result, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Error in GenerateUserEmbeddingView: {str(e)}")
            return Response(
                {'error': f'Internal server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




def generate_user_embedding(user_id: int) -> dict:

    try:
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id: {user_id}")
            return {"error": f"Invalid user_id: {user_id}"}

        # گرفتن تعاملات (مثل قبل)
        user_likes = list(likes.find({"userId": user_id}))
        user_reads = list(article_reads.find({"userId": user_id}))
        user_saved_articles = list(saved_articles.find({"userId": user_id}))
        user_searches = list(search_history.find({"user_id": str(user_id)}).sort("created_at", -1).limit(10))
        
        if not any([user_likes, user_reads, user_saved_articles, user_searches]):
            logger.info(f"No interactions found for user {user_id}. Skipping embedding creation.")
            return {"message": f"No interactions found for user {user_id}. Embedding not created."}

        logger.debug(f"Found {len(user_likes)} likes, {len(user_reads)} reads, {len(user_saved_articles)} saved articles, and {len(user_searches)} searches for user {user_id}")

        article_weights = {}
        search_embeddings = []

        # وزن‌دهی به لایک‌ها (مثل قبل)
        for like in user_likes:
            try:
                article_id_raw = like.get("articleId")
                article_id = ObjectId(article_id_raw) if isinstance(article_id_raw, str) else article_id_raw
                article_weights[article_id] = article_weights.get(article_id, 0) + calculate_article_weight(like=like)
            except Exception as e:
                logger.error(f"Error processing like for user {user_id}: {str(e)}")
                continue

        # وزن‌دهی به خوندن‌ها (مثل قبل)
        for read in user_reads:
            try:
                article_id_raw = read.get("articleId")
                article_id = ObjectId(article_id_raw) if isinstance(article_id_raw, str) else article_id_raw
                article_weights[article_id] = article_weights.get(article_id, 0) + calculate_article_weight(read=read)
            except Exception as e:
                logger.error(f"Error processing read for user {user_id}: {str(e)}")
                continue
                
        # وزن‌دهی به مقالات ذخیره شده (مثل قبل)
        for saved in user_saved_articles:
            try:
                article_id_raw = saved.get("articleId")
                if isinstance(article_id_raw, dict) and "$oid" in article_id_raw:
                    article_id = ObjectId(article_id_raw["$oid"])
                elif isinstance(article_id_raw, str):
                    article_id = ObjectId(article_id_raw)
                else:
                    article_id = article_id_raw
                article_weights[article_id] = article_weights.get(article_id, 0) + calculate_article_weight(saved=saved)
            except Exception as e:
                logger.error(f"Error processing saved article for user {user_id}: {str(e)}")
                continue

        # پردازش سرچ‌های اخیر کاربر (مثل قبل)
        for search in user_searches:
            try:
                search_embedding = search.get("embedding")
                created_at_raw = search.get("created_at")
                
                if search_embedding:
                    try:
                        if not isinstance(created_at_raw, str) and created_at_raw is not None:
                            created_at_raw = str(created_at_raw)
                        if created_at_raw and 'Z' in created_at_raw:
                            created_at_raw = created_at_raw.replace("Z", "+00:00")
                        elif created_at_raw and not ('+' in created_at_raw or '-' in created_at_raw[-6:]):
                            created_at_raw = created_at_raw + "+00:00"
                        created_at = datetime.fromisoformat(created_at_raw)
                        recency_factor = 1.2 if (datetime.now() - created_at) < timedelta(hours=24) else 0.8
                    except Exception:
                        recency_factor = 0.8
                    
                    search_embedding_np = np.array(search_embedding)
                    search_embeddings.append((search_embedding_np, 0.2 * recency_factor))
            except Exception as e:
                logger.error(f"Error processing search for user {user_id}: {str(e)}")
                continue
        
        embeddings = []
        weights = []
        for article_id, weight in article_weights.items():
            article = articles.find_one({"articleId": article_id})
            if not article:
                article = articles.find_one({"_id": article_id})
            
            title_embedding = None
            text_embedding = None
            
            if article:
                if "title_embedding" in article:
                    title_embedding = article["title_embedding"]
                elif "titleEmbedding" in article:
                    title_embedding = article["titleEmbedding"]
                if "text_embedding" in article:
                    text_embedding = article["text_embedding"]
                elif "textEmbedding" in article:
                    text_embedding = article["textEmbedding"]
                
                if title_embedding and text_embedding:
                    title_embedding_np = np.array(title_embedding)
                    text_embedding_np = np.array(text_embedding)
                    if len(title_embedding_np) == len(text_embedding_np):
                        combined_embedding = 0.5 * title_embedding_np + 0.5 * text_embedding_np
                        embeddings.append(combined_embedding)
                        weights.append(weight)
                    else:
                        logger.warning(f"Embedding dimensions mismatch for articleId {article_id}")
                else:
                    logger.warning(f"Missing embeddings for articleId {article_id}")
            else:
                logger.warning(f"No article found for articleId: {article_id}")

        has_data = (embeddings and weights) or search_embeddings
        
        if has_data:
            total_weight = 0
            weighted_sum = np.zeros(1024)  # فرض بر dimension 1024، اگر مدل فرق کنه تغییر بده
            
            if embeddings and weights:
                article_weighted_sum = np.sum([w * e for w, e in zip(weights, embeddings)], axis=0)
                total_article_weight = sum(weights)
                weighted_sum += article_weighted_sum
                total_weight += total_article_weight
            
            if search_embeddings:
                for search_embedding, search_weight in search_embeddings:
                    weighted_sum += search_weight * search_embedding
                    total_weight += search_weight
            
            if total_weight > 0:
                user_embedding = weighted_sum / total_weight
                user_profiles.update_one(
                    {"userId": user_id},
                    {"$set": {
                        "embedding": user_embedding.tolist(),
                        "last_updated": datetime.now().isoformat()
                    }},
                    upsert=True
                )
                logger.info(f"User embedding for {user_id} created and stored successfully")
                return {"message": f"User embedding for {user_id} created and stored successfully."}
            else:
                logger.warning(f"Total weight is zero for userId: {user_id}")
                return {"message": f"Total weight is zero for userId: {user_id}. Embedding not created."}
        else:
            logger.info(f"No valid embeddings or weights for userId: {user_id}")
            return {"message": f"No valid embeddings or weights for userId: {user_id}. Embedding not created."}

    except Exception as e:
        logger.error(f"Error in generate_user_embedding for user {user_id}: {str(e)}")
        return {"error": f"Error creating user embedding: {str(e)}"}

