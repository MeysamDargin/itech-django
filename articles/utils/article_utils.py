import json
import re
import datetime
import logging
from typing import Dict, List, Optional, Any
from bson import ObjectId
from config.mongo_utils import get_collection, get_database
from django.contrib.auth.models import User
from profiles.models import Profile
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import numpy as np
import os

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()
db = get_database('iTech')
base_url = os.getenv("BASE_URL")

def format_article_data(document: Dict) -> Dict:
    """Format MongoDB document for WebSocket transmission"""
    return {
        '_id': str(document['_id']),
        'title': document.get('title', ''),
        'text': document.get('text', ''),
        'delta': document.get('delta', ''),
        'imgCover': document.get('imgCover', ''),
        'category': document.get('category', ''),
        'userId': document.get('userId'),
        'createdAt': document.get('createdAt').isoformat() if document.get('createdAt') else None,
        'updatedAt': document.get('updatedAt').isoformat() if document.get('updatedAt') else None
    }

def delta_to_plain_text(delta) -> str:
    """Converts Quill Delta to plain text."""
    text = ""
    ops = []
    if isinstance(delta, dict) and "ops" in delta:
        ops = delta.get("ops", [])
    elif isinstance(delta, list):
        ops = delta
    
    for op in ops:
        insert = op.get("insert", "")
        if isinstance(insert, str):
            text += insert
    return text

def clean_html_tags(html_text: str) -> str:
    """Removes HTML tags from text."""
    if not html_text:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', html_text)
    return clean_text.strip()

def get_absolute_img_cover_url(img_cover_path: str, request) -> str:
    """Converts a relative image cover path to an absolute URL."""
    if img_cover_path and not img_cover_path.startswith(('http://', 'https://')):
        return request.build_absolute_uri(img_cover_path)
    return img_cover_path

def get_user_profile_data(user_id: int) -> Dict:
    """Get username and profile picture for a user."""
    username = ''
    profile_picture = ''
    bio = ''
    
    try:
        user = User.objects.get(id=user_id)
        username = user.username
        
        try:
            profile = Profile.objects.get(user=user)
            if profile.profile_picture:
                profile_picture = profile.profile_picture.url
            bio = profile.bio or ''
        except Profile.DoesNotExist:
            pass
    except User.DoesNotExist:
        pass
        
    return {
        'username': username,
        'profilePicture': f'{base_url}{profile_picture}' if profile_picture else 'http://localhost:8001/media/profile_pics/default.png',
        'bio': bio
    }

def get_article_counts(article_id: ObjectId) -> Dict:
    """Get likes, comments, and reads count for an article."""
    likes_collection = get_collection('likes')
    comments_collection = get_collection('comments')
    reads_collection = get_collection('articleReads')
    
    likes_count = likes_collection.count_documents({'articleId': article_id})
    
    # Count comments with different field variations
    comments_count_str = comments_collection.count_documents({'article_id': str(article_id)})
    comments_count_obj = comments_collection.count_documents({'article_id': article_id})
    comments_count_camel = comments_collection.count_documents({'articleId': article_id})
    comments_count = comments_count_str + comments_count_obj + comments_count_camel
    
    reads_count = reads_collection.count_documents({'articleId': article_id})
    
    return {
        'likes_count': likes_count,
        'comments_count': comments_count,
        'reads_count': reads_count
    }

def send_websocket_notification(group_name: str, message_type: str, data: Dict):
    """Send notification via WebSocket."""
    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': message_type,
                **data
            }
        )
        logger.info(f"Sent {message_type} notification to {group_name}")
    except Exception as e:
        logger.error(f"Failed to send {message_type} notification: {str(e)}")

def validate_object_id(object_id: str) -> bool:
    """Validate if string is a valid ObjectId."""
    return ObjectId.is_valid(object_id)

def get_similar_articles(user_id: int, limit: int = 50) -> List[Dict]:
    """Get similar articles based on user profile embedding."""
    articles_collection = get_collection('articles')
    user_profiles = db["user_profiles"]
    
    user_profile = user_profiles.find_one({"userId": user_id})
    if not user_profile or "embedding" not in user_profile:
        return []

    user_embedding = np.array(user_profile["embedding"])

    all_articles = list(articles_collection.find({
        "$or": [
            {"title_embedding": {"$exists": True}, "text_embedding": {"$exists": True}},
            {"titleEmbedding": {"$exists": True}, "textEmbedding": {"$exists": True}}
        ]
    }))

    similar_articles = []
    for article in all_articles:
        title_embedding = article.get("title_embedding") or article.get("titleEmbedding")
        text_embedding = article.get("text_embedding") or article.get("textEmbedding")

        if title_embedding and text_embedding and len(title_embedding) == len(text_embedding):
            combined = 0.5 * np.array(title_embedding) + 0.5 * np.array(text_embedding)
            similarity = np.dot(user_embedding, combined) / (np.linalg.norm(user_embedding) * np.linalg.norm(combined))
            similar_articles.append({
                "article": article,
                "similarity": float(similarity)
            })

    similar_articles.sort(key=lambda x: x["similarity"], reverse=True)
    return [item["article"] for item in similar_articles[:limit]]

def filter_articles_by_time(articles: List[Dict], read_article_ids: set, hours_primary: int = 12, hours_fallback: int = 72) -> List[Dict]:
    """Filter articles by time and read status."""
    now = datetime.datetime.now()
    primary_time_limit = now - datetime.timedelta(hours=hours_primary)
    fallback_time_limit = now - datetime.timedelta(hours=hours_fallback)

    # First try with primary time limit
    filtered_articles = [
        a for a in articles
        if a["_id"] not in read_article_ids and a.get("createdAt", datetime.datetime.min) >= primary_time_limit
    ]

    # If no articles found, use fallback time limit
    if not filtered_articles:
        filtered_articles = [
            a for a in articles
            if a["_id"] not in read_article_ids and a.get("createdAt", datetime.datetime.min) >= fallback_time_limit
        ]

    return filtered_articles

def format_article_for_response(article: Dict, request) -> Dict:
    """Format article data for API response."""
    img_cover = article.get("imgCover", "")
    absolute_img_cover = get_absolute_img_cover_url(img_cover, request)

    return {
        "id": str(article["_id"]),
        "title": article.get("title", ""),
        "category": article.get("category", ""),
        "imgCover": absolute_img_cover,
        "createdAt": article.get("createdAt").isoformat() if article.get("createdAt") else None
    }