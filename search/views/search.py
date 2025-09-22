from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from config.mongo_utils import get_collection
from bson import ObjectId
import datetime
import requests
from scipy.spatial.distance import cosine
import numpy as np
from following.models import Follow
import faiss
from django.contrib.auth.models import User
from profiles.models import Profile
import os

embed_api_url = os.getenv("EMBEDDING_SERVER_URL")
base_url = os.getenv("BASE_URL")

class SearchArticlesView(APIView):
    permission_classes = [IsAuthenticated]

    def normalize_embedding(self, embedding):
        emb = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(emb)
        print(f"[DEBUG] Embedding norm before normalization: {norm}")
        if norm == 0:
            return emb
        return emb / norm

    def get(self, request):
        search_text = request.query_params.get('q', '')
        print(f"[LOG] Received search query: '{search_text}'")

        if not search_text:
            return Response({"error": "Search text is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        # جستجوی کاربران بر اساس نام کاربری
        users = User.objects.filter(username__icontains=search_text)[:5]
        user_results = []
        for user in users:
            try:
                profile = Profile.objects.get(user=user)
                profile_picture = profile.profile_picture.url if profile.profile_picture else '/media/profile_pics/default.png'
            except Profile.DoesNotExist:
                profile_picture = '/media/profile_pics/default.png'
                
            user_results.append({
                'type': 'user',
                'id': str(user.id),
                'username': user.username,
                'profile_picture': f'{base_url}{profile_picture}',
                'first_name': profile.first_name,
                'last_name': profile.last_name
            })

        cleaned_text = search_text.strip()
        print(f"[LOG] Cleaned search text: '{cleaned_text}'")

        # دریافت embedding
        try:
            print(f"[LOG] Sending POST request to embedding service with text: {cleaned_text}")
            text_response = requests.post(
                embed_api_url,
                headers={'Content-Type': 'application/json'},
                json={'texts': [cleaned_text]},
                timeout=60
            )
            text_response.raise_for_status()
            response_json = text_response.json()
            print(f"[LOG] Embedding service response: {response_json}")
            search_embedding = response_json['embeddings'][0]
            
            # ذخیره کوئری و embedding آن در کالکشن search
            search_collection = get_collection('search')
            search_document = {
                'query': cleaned_text,
                'embedding': search_embedding,  # ذخیره به صورت آرایه
                'user_id': str(request.user.id),
                'created_at': datetime.datetime.now()
            }
            search_id = search_collection.insert_one(search_document).inserted_id
            print(f"[LOG] Search query saved with ID: {search_id}")
            
        except Exception as e:
            print(f"[ERROR] Failed to get embedding or save search: {str(e)}")
            return Response({"error": f"Failed to get embedding: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        search_embedding_norm = self.normalize_embedding(search_embedding)

        # لود مقالات و انبدیگ‌ها
        article_collection = get_collection('articles')
        user_article_collection = get_collection('articles_users')
        like_collection = get_collection('likes')
        comment_collection = get_collection('comments')
        reads_collection = get_collection('articleReads')  # اضافه کردن کالکشن خوانده‌ها

        articles = list(article_collection.find()) + list(user_article_collection.find())
        print(f"[LOG] Total articles fetched: {len(articles)}")

        # آماده‌سازی برای FAISS
        embeddings = []
        article_ids = []
        for article in articles:
            text_emb = article.get('text_embedding')
            if text_emb:
                embeddings.append(self.normalize_embedding(text_emb))
                article_ids.append(str(article['_id']))

        if not embeddings:
            return Response({"error": "No valid embeddings found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        embeddings = np.array(embeddings).astype('float32')
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)

        # سرچ با FAISS
        search_embedding_norm = np.array([search_embedding_norm]).astype('float32')
        distances, indices = index.search(search_embedding_norm, k=20)

        results = []
        max_popularity = 1
        for i, idx in enumerate(indices[0]):
            article = articles[idx]
            article_id = str(article['_id'])
            similarity = distances[0][i]

            if similarity < 0.3:  # آستانه کاهش‌یافته
                continue

            author_id = article.get('author_id')
            likes = like_collection.count_documents({'article_id': ObjectId(article_id)})
            comments = comment_collection.count_documents({'article_id': ObjectId(article_id)})
            popularity = likes + comments
            max_popularity = max(max_popularity, popularity)

            created_at = article.get('created_at', datetime.datetime.min)
            recency = (datetime.datetime.now() - created_at).days

            is_followed = False
            if author_id:
                try:
                    is_followed = Follow.objects.filter(follower=request.user, followed_id=author_id).exists()
                except (ValueError, TypeError):
                    is_followed = False

            # امتیاز ترکیبی
            score = (0.5 * similarity) + (0.2 * (100 if is_followed else 0)) - (0.2 * recency / 365) + (0.1 * popularity / max_popularity)

            # دریافت اطلاعات نویسنده
            user_id = article.get('userId') or article.get('author_id')
            username = ''
            profile_picture = ''
            
            # اگر نویسنده کاربر است (نه AI)
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    username = user.username
                    
                    # دریافت عکس پروفایل
                    try:
                        profile = Profile.objects.get(user=user)
                        if profile.profile_picture:
                            profile_picture = profile.profile_picture.url
                    except Profile.DoesNotExist:
                        pass
                except User.DoesNotExist:
                    pass
            else:
                # اگر مقاله توسط AI نوشته شده
                username = 'AI'
                profile_picture = '/media/profile_pics/default.png'
            
            # شمارش لایک‌ها، کامنت‌ها و خوانده‌ها
            # برای کامنت‌ها، هر سه حالت ممکن را بررسی می‌کنیم
            count_str = comment_collection.count_documents({'article_id': str(article_id)})
            count_obj = 0
            try:
                count_obj = comment_collection.count_documents({'article_id': ObjectId(article_id)})
            except Exception:
                pass
            count_camel_obj = comment_collection.count_documents({'articleId': ObjectId(article_id)})
            comments_count = count_str + count_obj + count_camel_obj
            
            # شمارش لایک‌ها
            likes_count = like_collection.count_documents({'articleId': ObjectId(article_id)})
            
            # شمارش خوانده‌ها
            reads_count = reads_collection.count_documents({'articleId': ObjectId(article_id)})
            
            results.append({
                'type': 'article',
                'article_id': article_id,
                'title': article.get('title'),
                'category': article.get('category'),
                'imgCover': f'{base_url}{article.get("imgCover", "")}',
                'createdAt': article.get('createdAt').isoformat() if article.get('createdAt') else None,
                'score': score,
                'similarity': similarity,
                'username': username,
                'profilePicture': f'{base_url}{profile_picture}',
                'likes_count': likes_count,
                'comments_count': comments_count,
                'reads_count': reads_count
            })
        # مرتب‌سازی نتایج مقالات بر اساس امتیاز
        results.sort(key=lambda x: x['score'], reverse=True)
        article_results = results[:10]
        
        # ترکیب نتایج کاربران و مقالات
        combined_results = {
            'users': user_results,
            'articles': article_results,
            'total_users': len(user_results),
            'total_articles': len(article_results)
        }
        
        print(f"[LOG] Returning {len(article_results)} articles and {len(user_results)} users after filtering and sorting")
        return Response(combined_results, status=status.HTTP_200_OK)


class UserSearchHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """بازیابی تاریخچه جستجوهای کاربر از کالکشن search در MongoDB"""
        try:
            # دریافت کالکشن search
            search_collection = get_collection('search')
            
            # جستجوی تمام رکوردهای مربوط به کاربر فعلی
            user_searches = search_collection.find(
                {'user_id': str(request.user.id)},
                {'_id': 1, 'query': 1, 'created_at': 1}
            ).sort('created_at', -1)  # مرتب‌سازی بر اساس زمان (جدیدترین اول)
            
            # تبدیل نتایج به لیست و فرمت‌دهی
            search_history = []
            for search in user_searches:
                search_history.append({
                    'id': str(search['_id']),
                    'query': search['query'],
                    'created_at': search['created_at'].isoformat() if search.get('created_at') else None
                })
            
            return Response(search_history, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"[ERROR] Failed to retrieve search history: {str(e)}")
            return Response(
                {"error": f"Failed to retrieve search history: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )