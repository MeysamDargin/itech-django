import logging
import json
import requests
from datetime import datetime, timedelta
import numpy as np
import re
from config.mongo_utils import get_collection
from bson import ObjectId
import os

# تنظیم لاگ‌گذاری
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
embed_api_url = os.getenv("EMBEDDING_SERVER_URL")

# Mongo collections
likes = get_collection('likes')
article_reads = get_collection('articleReads')
articles = get_collection('articles')
user_profiles = get_collection('user_profiles')
saved_articles = get_collection('saved')
search_history = get_collection('search')


class EmbeddingService:
    @staticmethod
    def get_embedding(text, timeout=30):
        """درخواست embedding از سرویس"""
        try:
            logger.debug(f"Getting embedding for text (length: {len(text)})")
            response = requests.post(
                embed_api_url,
                headers={'Content-Type': 'application/json'},
                json={'texts': [text]},
                timeout=timeout
            )
            response.raise_for_status()
            raw_embedding = response.json().get('embeddings', [[]])[0]
            return EmbeddingService.normalize_embedding(raw_embedding)
        except requests.RequestException as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return []

    @staticmethod
    def normalize_embedding(embedding):
        """نرمالایز کردن embedding با استفاده از L2 norm"""
        if not embedding:
            return embedding
        
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        
        if norm == 0:
            return embedding  # جلوگیری از تقسیم بر صفر
        
        normalized = embedding_array / norm
        return normalized.tolist()


class TextProcessingService:
    @staticmethod
    def delta_to_plain_text(delta):
        """تبدیل دلتا (Quill Delta) به متن ساده"""
        text = ""

        # بررسی اینکه آیا delta یک دیکشنری با کلید ops است یا مستقیماً یک آرایه
        ops = []
        if isinstance(delta, dict) and "ops" in delta:
            ops = delta.get("ops", [])
        elif isinstance(delta, list):
            ops = delta
        else:
            ops = []

        for op in ops:
            if isinstance(op, dict):
                insert = op.get("insert", "")
                if isinstance(insert, str):
                    text += insert
                elif isinstance(insert, dict):
                    # اگر خواستی اینجا آبجکت‌ها رو مدیریت کن، الان حذف می‌کنیم
                    pass

        return text

    @staticmethod
    def clean_html_tags(text):
        """پاک کردن تگ‌های HTML از متن"""
        clean = re.compile('<.*?>')
        return re.sub(clean, '', text)

    @staticmethod
    def process_text_field(text_delta):
        """پردازش فیلد text و تبدیل به متن ساده"""
        cleaned_text = ""
        try:
            if isinstance(text_delta, dict):
                # اگر text یک دیکشنری باشد
                cleaned_text = TextProcessingService.delta_to_plain_text(text_delta)
            elif isinstance(text_delta, str):
                # اگر text یک رشته است، بررسی می‌کنیم که آیا JSON است یا HTML
                try:
                    # تلاش برای تبدیل رشته به JSON
                    json_data = json.loads(text_delta)
                    cleaned_text = TextProcessingService.delta_to_plain_text(json_data)
                except json.JSONDecodeError:
                    # اگر JSON نیست، فرض می‌کنیم HTML است
                    cleaned_text = TextProcessingService.clean_html_tags(text_delta)
            else:
                cleaned_text = ""

            logger.debug(f"Cleaned text length: {len(cleaned_text)}")
        except Exception as e:
            logger.error(f"Error cleaning text: {str(e)}")
            cleaned_text = ""
        
        return cleaned_text


class WeightCalculationService:
    @staticmethod
    def calculate_article_weight(read=None, like=None, saved=None):
        """محاسبه وزن مقاله بر اساس تعاملات کاربر"""
        weight = 0.0
        recency_factor = 1.0

        if like:
            logger.debug(f"Processing like: {like}")
            try:
                created_at_raw = like.get("createdAt")
                logger.debug(f"Raw createdAt: {created_at_raw}, type: {type(created_at_raw)}")
                
                # تبدیل به رشته اگر نوع دیگری است
                if not isinstance(created_at_raw, str):
                    created_at_raw = str(created_at_raw)
                    
                # حذف Z یا تبدیل به فرمت استاندارد
                if 'Z' in created_at_raw:
                    created_at_raw = created_at_raw.replace("Z", "+00:00")
                elif not ('+' in created_at_raw or '-' in created_at_raw[-6:]):
                    created_at_raw = created_at_raw + "+00:00"
                    
                created_at = datetime.fromisoformat(created_at_raw)
                logger.debug(f"Converted createdAt: {created_at}, type: {type(created_at)}")
                recency_factor = 1.2 if (datetime.now() - created_at) < timedelta(hours=24) else 0.8
                weight += 0.5 * recency_factor
                logger.debug(f"Like weight: 0.5 * {recency_factor} = {weight}")
            except Exception as e:
                logger.error(f"Error processing like fields: {str(e)}")
                # اگر نتوانستیم تاریخ را تبدیل کنیم، از مقدار پیش‌فرض استفاده می‌کنیم
                weight += 0.5 * 0.8  # مقدار پیش‌فرض با فرض قدیمی بودن لایک
                logger.debug(f"Using default like weight: 0.4")
                
        if saved:
            logger.debug(f"Processing saved article: {saved}")
            try:
                created_at_raw = saved.get("createdAt")
                logger.debug(f"Raw createdAt for saved: {created_at_raw}, type: {type(created_at_raw)}")
                
                # تبدیل به رشته اگر نوع دیگری است
                if not isinstance(created_at_raw, str) and created_at_raw is not None:
                    if isinstance(created_at_raw, dict) and "$date" in created_at_raw:
                        created_at_raw = str(created_at_raw["$date"])
                    else:
                        created_at_raw = str(created_at_raw)
                    
                # حذف Z یا تبدیل به فرمت استاندارد
                if created_at_raw and 'Z' in created_at_raw:
                    created_at_raw = created_at_raw.replace("Z", "+00:00")
                elif created_at_raw and not ('+' in created_at_raw or '-' in created_at_raw[-6:]):
                    created_at_raw = created_at_raw + "+00:00"
                    
                if created_at_raw:
                    created_at = datetime.fromisoformat(created_at_raw)
                    logger.debug(f"Converted createdAt for saved: {created_at}, type: {type(created_at)}")
                    recency_factor = 1.2 if (datetime.now() - created_at) < timedelta(hours=24) else 0.8
                else:
                    recency_factor = 0.8  # مقدار پیش‌فرض با فرض قدیمی بودن
                    
                weight += 0.4 * recency_factor  # وزن پایه 0.4 برای مقالات ذخیره شده
                logger.debug(f"Saved article weight: 0.4 * {recency_factor} = {0.4 * recency_factor}")
            except Exception as e:
                logger.error(f"Error processing saved article fields: {str(e)}")
                # اگر نتوانستیم تاریخ را تبدیل کنیم، از مقدار پیش‌فرض استفاده می‌کنیم
                weight += 0.4 * 0.8  # مقدار پیش‌فرض با فرض قدیمی بودن
                logger.debug(f"Using default saved article weight: {0.4 * 0.8}")

        if read:
            logger.debug(f"Processing read: {read}")
            try:
                # استخراج مقادیر با مقادیر پیش‌فرض
                read_count_raw = read.get("readCount", 1)
                initial_duration_raw = read.get("initialDuration", 0)
                latest_duration_raw = read.get("latestDuration", 0)
                initial_percentage_raw = read.get("initialReadPercentage", 0)
                latest_percentage_raw = read.get("latestReadPercentage", 0)
                last_read_at_raw = read.get("lastReadAt")
                
                logger.debug(f"Raw read fields: readCount={read_count_raw} ({type(read_count_raw)}), "
                            f"initialDuration={initial_duration_raw} ({type(initial_duration_raw)}), "
                            f"latestDuration={latest_duration_raw} ({type(latest_duration_raw)}), "
                            f"initialReadPercentage={initial_percentage_raw} ({type(initial_percentage_raw)}), "
                            f"latestReadPercentage={latest_percentage_raw} ({type(latest_percentage_raw)}), "
                            f"lastReadAt={last_read_at_raw} ({type(last_read_at_raw)})")

                # تبدیل به اعداد با استفاده از حلقه امن
                try:
                    read_count = int(read_count_raw)
                except (ValueError, TypeError):
                    read_count = 1
                    
                try:
                    initial_duration = int(initial_duration_raw)
                except (ValueError, TypeError):
                    initial_duration = 0
                    
                try:
                    latest_duration = int(latest_duration_raw)
                except (ValueError, TypeError):
                    latest_duration = 0
                    
                try:
                    initial_percentage = float(initial_percentage_raw)
                except (ValueError, TypeError):
                    initial_percentage = 0
                    
                try:
                    latest_percentage = float(latest_percentage_raw)
                except (ValueError, TypeError):
                    latest_percentage = 0
                
                # تبدیل تاریخ با حلقه امن
                try:
                    if not isinstance(last_read_at_raw, str):
                        last_read_at_raw = str(last_read_at_raw)
                        
                    # حذف Z یا تبدیل به فرمت استاندارد
                    if 'Z' in last_read_at_raw:
                        last_read_at_raw = last_read_at_raw.replace("Z", "+00:00")
                    elif not ('+' in last_read_at_raw or '-' in last_read_at_raw[-6:]):
                        last_read_at_raw = last_read_at_raw + "+00:00"
                        
                    last_read_at = datetime.fromisoformat(last_read_at_raw)
                except Exception:
                    last_read_at = datetime.now() - timedelta(days=2)  # مقدار پیش‌فرض قدیمی

                logger.debug(f"Converted read fields: readCount={read_count} ({type(read_count)}), "
                            f"initialDuration={initial_duration} ({type(initial_duration)}), "
                            f"latestDuration={latest_duration} ({type(latest_duration)}), "
                            f"initialReadPercentage={initial_percentage} ({type(initial_percentage)}), "
                            f"latestReadPercentage={latest_percentage} ({type(latest_percentage)}), "
                            f"lastReadAt={last_read_at} ({type(last_read_at)})")

                read_count_weight = 0.1 * read_count
                duration_weight = 0.3 * min((initial_duration + latest_duration) / 60, 5)
                percentage_weight = 0.2 * ((initial_percentage + latest_percentage) / 2) / 100
                recency_factor = 1.2 if (datetime.now() - last_read_at) < timedelta(hours=24) else 0.8

                weight += (read_count_weight + duration_weight + percentage_weight) * recency_factor
                logger.debug(f"Read weights: read_count={read_count_weight}, duration={duration_weight}, "
                            f"percentage={percentage_weight}, recency={recency_factor}, total={weight}")
            except Exception as e:
                logger.error(f"Error converting read fields: {str(e)}")
                # اگر خطایی رخ داد، از مقدار پیش‌فرض استفاده می‌کنیم
                weight += 0.3  # مقدار پیش‌فرض برای خواندن
                logger.debug(f"Using default read weight: 0.3")

        return weight


class UserEmbeddingService:
    @staticmethod
    def generate_user_embedding(user_id: int) -> dict:
        """
        این تابع embedding کاربر رو بر اساس interactions محاسبه می‌کنه و ذخیره می‌کنه.
        ورودی: user_id (int)
        خروجی: dict مثل {'message': '...'} یا {'error': '...'}
        """
        try:
            if not isinstance(user_id, int) or user_id <= 0:
                logger.error(f"Invalid user_id: {user_id}")
                return {"error": f"Invalid user_id: {user_id}"}

            # گرفتن تعاملات
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

            # وزن‌دهی به لایک‌ها
            for like in user_likes:
                try:
                    article_id_raw = like.get("articleId")
                    article_id = ObjectId(article_id_raw) if isinstance(article_id_raw, str) else article_id_raw
                    article_weights[article_id] = article_weights.get(article_id, 0) + WeightCalculationService.calculate_article_weight(like=like)
                except Exception as e:
                    logger.error(f"Error processing like for user {user_id}: {str(e)}")
                    continue

            # وزن‌دهی به خوندن‌ها
            for read in user_reads:
                try:
                    article_id_raw = read.get("articleId")
                    article_id = ObjectId(article_id_raw) if isinstance(article_id_raw, str) else article_id_raw
                    article_weights[article_id] = article_weights.get(article_id, 0) + WeightCalculationService.calculate_article_weight(read=read)
                except Exception as e:
                    logger.error(f"Error processing read for user {user_id}: {str(e)}")
                    continue
                    
            # وزن‌دهی به مقالات ذخیره شده
            for saved in user_saved_articles:
                try:
                    article_id_raw = saved.get("articleId")
                    if isinstance(article_id_raw, dict) and "$oid" in article_id_raw:
                        article_id = ObjectId(article_id_raw["$oid"])
                    elif isinstance(article_id_raw, str):
                        article_id = ObjectId(article_id_raw)
                    else:
                        article_id = article_id_raw
                    article_weights[article_id] = article_weights.get(article_id, 0) + WeightCalculationService.calculate_article_weight(saved=saved)
                except Exception as e:
                    logger.error(f"Error processing saved article for user {user_id}: {str(e)}")
                    continue

            # پردازش سرچ‌های اخیر کاربر
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


class ArticleProcessingService:
    @staticmethod
    def process_single_article(article):
        """پردازش یک مقاله و اضافه کردن embedding"""
        title = article.get('title', '')
        text_delta = article.get('text', {})
        
        logger.debug(f"Processing article with title: {title[:30]}...")

        # تبدیل دلتا به متن ساده
        cleaned_text = TextProcessingService.process_text_field(text_delta)

        # گرفتن embedding برای عنوان
        title_embedding = EmbeddingService.get_embedding(title)
        
        # گرفتن embedding برای متن با timeout بیشتر
        text_embedding = EmbeddingService.get_embedding(cleaned_text, timeout=60)

        # ایجاد یک کپی از مقاله و اضافه کردن فیلدهای جدید
        processed_article = article.copy()
        processed_article['title_embedding'] = title_embedding
        processed_article['text_embedding'] = text_embedding
        processed_article['cleaned_text'] = cleaned_text

        logger.debug(f"Processed article: {title[:30]}")
        return processed_article

    @staticmethod
    def process_articles_list(articles_data):
        """پردازش لیست مقالات"""
        processed_articles = []
        for article in articles_data:
            processed_article = ArticleProcessingService.process_single_article(article)
            processed_articles.append(processed_article)
        
        return processed_articles


class SimilarityService:
    @staticmethod
    def calculate_cosine_similarity(embedding1, embedding2):
        """محاسبه شباهت کسینوسی بین دو embedding"""
        embedding1_np = np.array(embedding1)
        embedding2_np = np.array(embedding2)
        
        return np.dot(embedding1_np, embedding2_np) / (
            np.linalg.norm(embedding1_np) * np.linalg.norm(embedding2_np)
        )

    @staticmethod
    def find_similar_articles(user_id, limit=10):
        """یافتن مقالات مشابه بر اساس embedding کاربر"""
        # دریافت امبدینگ کاربر
        user_profile = user_profiles.find_one({"userId": user_id})
        if not user_profile or "embedding" not in user_profile:
            raise ValueError(f"No embedding found for user {user_id}")
            
        user_embedding = user_profile["embedding"]
        logger.debug(f"Found user embedding for user {user_id}, length: {len(user_embedding)}")
        
        # دریافت همه مقالات با امبدینگ
        all_articles = list(articles.find({
            "$or": [
                {"title_embedding": {"$exists": True}, "text_embedding": {"$exists": True}},
                {"titleEmbedding": {"$exists": True}, "textEmbedding": {"$exists": True}}
            ]
        }))
        logger.debug(f"Found {len(all_articles)} articles with both title and text embeddings")
        
        # محاسبه شباهت کسینوسی
        similar_articles = []
        for article in all_articles:
            # بررسی وجود امبدینگ عنوان و متن
            title_embedding = None
            text_embedding = None
            
            # بررسی امبدینگ عنوان
            if "title_embedding" in article:
                title_embedding = article["title_embedding"]
            elif "titleEmbedding" in article:
                title_embedding = article["titleEmbedding"]
                
            # بررسی امبدینگ متن
            if "text_embedding" in article:
                text_embedding = article["text_embedding"]
            elif "textEmbedding" in article:
                text_embedding = article["textEmbedding"]
            
            # فقط اگر هر دو امبدینگ موجود باشند، مقاله را در نظر می‌گیریم
            if title_embedding and text_embedding:
                # ترکیب امبدینگ‌ها با وزن 50-50
                title_embedding_np = np.array(title_embedding)
                text_embedding_np = np.array(text_embedding)
                
                # بررسی سازگاری ابعاد
                if len(title_embedding_np) == len(text_embedding_np):
                    combined_embedding = 0.5 * title_embedding_np + 0.5 * text_embedding_np
                    
                    # محاسبه شباهت کسینوسی
                    similarity = SimilarityService.calculate_cosine_similarity(
                        user_embedding, combined_embedding
                    )
                    
                    # اضافه کردن به لیست مقالات مشابه
                    article_info = {
                        "articleId": article.get("articleId") or str(article.get("_id")),
                        "title": article.get("title", "Unknown Title"),
                        "similarity": float(similarity)
                    }
                    similar_articles.append(article_info)
        
        # مرتب‌سازی بر اساس شباهت (نزولی)
        similar_articles.sort(key=lambda x: x["similarity"], reverse=True)
        
        # محدود کردن تعداد نتایج
        return similar_articles[:limit]


class DebugService:
    @staticmethod
    def debug_article_data(article_id_raw):
        """Debug endpoint to check what's in the database for a specific article ID."""
        # تلاش برای تبدیل به ObjectId
        try:
            article_id = ObjectId(article_id_raw)
        except Exception:
            article_id = article_id_raw
            
        # جستجو با استفاده از articleId
        article_by_article_id = articles.find_one({"articleId": article_id})
        
        # جستجو با استفاده از _id
        article_by_id = articles.find_one({"_id": article_id})
        
        # بررسی وجود مقاله در کالکشن‌های دیگر
        likes_for_article = list(likes.find({"articleId": article_id}))
        reads_for_article = list(article_reads.find({"articleId": article_id}))
        
        return {
            "articleId": article_id_raw,
            "article_by_articleId": {
                "found": article_by_article_id is not None,
                "keys": list(article_by_article_id.keys()) if article_by_article_id else None,
                "has_embedding": "title_embedding" in article_by_article_id if article_by_article_id else False
            },
            "article_by_id": {
                "found": article_by_id is not None,
                "keys": list(article_by_id.keys()) if article_by_id else None,
                "has_embedding": "title_embedding" in article_by_id if article_by_id else False
            },
            "likes_count": len(likes_for_article),
            "reads_count": len(reads_for_article)
        }