
import json
import datetime
import logging
import os
import requests
from typing import Dict, List, Optional, Tuple
from bson import ObjectId
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from iTech import settings
from config.mongo_utils import get_collection
from profiles.models import Profile
from following.models import Follow
from articles.utils.article_utils import (
    delta_to_plain_text, clean_html_tags, get_user_profile_data,
    get_article_counts, send_websocket_notification, format_article_data,
    get_similar_articles, filter_articles_by_time, format_article_for_response
)

logger = logging.getLogger(__name__)
embed_api_url = os.getenv("EMBEDDING_SERVER_URL")
base_url = os.getenv("BASE_URL")


class ArticleService:
    def __init__(self):
        self.articles_collection = get_collection('articles')
        self.articles_users_collection = get_collection('articles_users')
        self.likes_collection = get_collection('likes')
        self.comments_collection = get_collection('comments')
        self.reads_collection = get_collection('articleReads')
        self.saved_collection = get_collection('saved')
        self.save_directory_collection = get_collection('save_directory')
        self.notifications_collection = get_collection('notifications')

    def filter_new_links(self, data: List[Dict]) -> List[Dict]:
        """Filter out existing links and return only new ones."""
        incoming_links = [item['link'] for item in data]
        
        existing_links = self.articles_collection.find(
            {'link': {'$in': incoming_links}},
            {'link': 1, '_id': 0}
        )
        existing_links_set = {doc['link'] for doc in existing_links}
        
        new_links = [
            {
                'link': item['link'],
                'title': item['title'],
                'category': item['category']
            }
            for item in data
            if item['link'] not in existing_links_set
        ]
        
        return new_links

    def get_all_articles(self) -> List[Dict]:
        """Get all articles from both collections with metadata."""
        articles_list = []
        
        # Process articles_users collection
        for article in self.articles_users_collection.find({}, {
            'title': 1, 'category': 1, 'imgCover': 1, 'userId': 1, 'createdAt': 1
        }):
            article_id = article['_id']
            user_data = get_user_profile_data(article.get('userId'))
            counts = get_article_counts(article_id)
            
            articles_list.append({
                'id': str(article_id),
                'title': article.get('title', ''),
                'category': article.get('category', ''),
                'imgCover': f'{base_url}{article.get("imgCover", "")}',
                'username': user_data['username'],
                'profilePicture': user_data['profilePicture'],
                'createdAt': article.get('createdAt').isoformat() if article.get('createdAt') else None,
                **counts
            })
        
        # Process articles collection (AI articles)
        for article in self.articles_collection.find({}, {
            'title': 1, 'category': 1, 'imgCover': 1, 'createdAt': 1
        }):
            article_id = article['_id']
            counts = get_article_counts(article_id)
            
            articles_list.append({
                'id': str(article_id),
                'title': article.get('title', ''),
                'category': article.get('category', ''),
                'imgCover': article.get('imgCover', ''),
                'username': 'AI',
                'profilePicture': 'http://localhost:8001/media/profile_pics/default.png',
                'createdAt': article.get('createdAt').isoformat() if article.get('createdAt') else None,
                **counts
            })

        # Sort by newest
        articles_list.sort(
            key=lambda x: x['createdAt'] or "",  # Handle None by placing at end
            reverse=True  # Newest first
        )
        
        return articles_list

    def get_recommended_articles(self, user_id: int) -> List[Dict]:
        """Get recommended articles for a user based on similarity, excluding already read articles."""
        articles_list = []

        # 1️⃣ Get articles user has read
        read_articles_cursor = self.reads_collection.find({"userId": user_id}, {"articleId": 1})
        read_article_ids = {read["articleId"] for read in read_articles_cursor}

        # 2️⃣ Get similar articles for the user
        similar_articles = get_similar_articles(user_id)
        similar_article_ids = [str(article['_id']) for article in similar_articles if '_id' in article]

        if not similar_article_ids:
            # No similar articles found
            return []

        # 3️⃣ Filter out read articles from similar articles
        unread_similar_article_ids = [
            aid for aid in similar_article_ids 
            if ObjectId(aid) not in read_article_ids
        ]

        if not unread_similar_article_ids:
            # All similar articles have been read
            return []

        # 4️⃣ Fetch user articles (excluding read ones)
        user_articles_cursor = self.articles_users_collection.find(
            {'_id': {'$in': [ObjectId(aid) for aid in unread_similar_article_ids]}},  # Only unread similar articles
            {'title': 1, 'category': 1, 'imgCover': 1, 'userId': 1, 'createdAt': 1}  # projection
        )

        for article in user_articles_cursor:
            article_id = article['_id']
            user_data = get_user_profile_data(article.get('userId'))
            counts = get_article_counts(article_id)

            articles_list.append({
                'id': str(article_id),
                'title': article.get('title', ''),
                'category': article.get('category', ''),
                'imgCover': f'{base_url}{article.get("imgCover", "")}',
                'username': user_data.get('username', 'Unknown'),
                'profilePicture': user_data.get('profilePicture', ''),
                'createdAt': article.get('createdAt').isoformat() if article.get('createdAt') else None,
                **counts
            })

        # 5️⃣ Fetch AI articles (excluding read ones)
        ai_articles_cursor = self.articles_collection.find(
            {'_id': {'$in': [ObjectId(aid) for aid in unread_similar_article_ids]}},
            {'title': 1, 'category': 1, 'imgCover': 1, 'createdAt': 1}
        )

        for article in ai_articles_cursor:
            article_id = article['_id']
            counts = get_article_counts(article_id)

            articles_list.append({
                'id': str(article_id),
                'title': article.get('title', ''),
                'category': article.get('category', ''),
                'imgCover': article.get('imgCover', ''),
                'username': 'AI',
                'profilePicture': 'http://localhost:8001/media/profile_pics/default.png',
                'createdAt': article.get('createdAt').isoformat() if article.get('createdAt') else None,
                **counts
            })

        # 6️⃣ Sort by newest
        articles_list.sort(
            key=lambda x: x['createdAt'] or "",
            reverse=True
        )

        return articles_list

    def get_article_by_id(self, article_id: str, user_id: int = None) -> Tuple[Dict, bool]:
        """Get article details by ID."""
        # Try articles_users first
        article = self.articles_users_collection.find_one({'_id': ObjectId(article_id)})
        collection_name = 'articles_users'
        
        if not article:
            # Try articles collection
            article = self.articles_collection.find_one({'_id': ObjectId(article_id)})
            collection_name = 'articles'
            
            if not article:
                return None, False
        
        # For 'articles' collection, use text as delta since delta may not exist
        if collection_name == 'articles':
            article['delta'] = article.get('text', '')

        # Build article data
        counts = get_article_counts(ObjectId(article_id))
        
        article_data = {
            'id': str(article['_id']),
            'title': article.get('title', ''),
            'user_id_login': user_id,
            'text': article.get('text', ''),
            'delta': article.get('delta', ''),
            'category': article.get('category', ''),
            'imgCover': article.get('imgCover', ''),
            'collection': collection_name,
            'createdAt': article.get('createdAt', datetime.datetime.now()).isoformat() if hasattr(article.get('createdAt', datetime.datetime.now()), 'isoformat') else str(article.get('createdAt', datetime.datetime.now())),
            'updatedAt': article.get('updatedAt', datetime.datetime.now()).isoformat() if hasattr(article.get('updatedAt', datetime.datetime.now()), 'isoformat') else str(article.get('updatedAt', datetime.datetime.now())),
            **counts
        }
        
        if collection_name == 'articles_users':
            user_data = get_user_profile_data(article.get('userId'))
            article_data.update({
                'userId': article.get('userId'),
                'username': user_data['username'],
                'bio': user_data['bio'],
                'profilePicture': user_data['profilePicture']
            })
        else:
            article_data.update({
                'userId': 0,
                'username': 'AI',
                'bio': 'created by ai',
                'profilePicture': 'http://localhost:8001/media/profile_pics/default.png'
            })
        
        # Check user interactions if authenticated
        if user_id:
            article_data['isLiked'] = self.likes_collection.find_one({
                'articleId': ObjectId(article_id),
                'userId': user_id
            }) is not None
            
            article_data['isSaved'] = self.saved_collection.find_one({
                'articleId': ObjectId(article_id),
                'userId': user_id
            }) is not None
        else:
            article_data['isLiked'] = False
            article_data['isSaved'] = False
        
        return article_data, True

    def toggle_like(self, article_id: str, user_id: int, request) -> Tuple[Dict, int]:
        """Toggle like status for an article."""
        existing_like = self.likes_collection.find_one({
            'articleId': ObjectId(article_id),
            'userId': user_id
        })
        
        if existing_like:
            # Remove like
            result = self.likes_collection.delete_one({'_id': existing_like['_id']})
            return {
                'status': 'success',
                'message': 'Article unliked successfully',
                'liked': False
            }, 200
        else:
            # Add like
            now = datetime.datetime.now()
            like_data = {
                'articleId': ObjectId(article_id),
                'userId': user_id,
                'createdAt': now
            }
            
            result = self.likes_collection.insert_one(like_data)
            
            # Send notification
            self._send_like_notification(article_id, user_id, request)
            
            return {
                'status': 'success',
                'message': 'Article liked successfully',
                'liked': True,
                'like_id': str(result.inserted_id)
            }, 200

    def create_article(self, article_data: Dict, user_id: int, request) -> Tuple[Dict, int]:
        """Create a new article."""
        # Generate embeddings
        embeddings = self._generate_embeddings(
            article_data['title'],
            article_data['delta']
        )
        
        # Handle image upload
        img_cover_path = self._handle_image_upload(article_data.get('imgCover'))
        
        if not img_cover_path:
            return {
                'status': 'error',
                'message': 'Image cover is required'
            }, 400
        
        # Create article document
        now = datetime.datetime.now()
        article_doc = {
            'title': article_data['title'],
            'text': article_data['text'],
            'delta': article_data['delta'],
            'imgCover': img_cover_path,
            'category': article_data['category'],
            'userId': user_id,
            'title_embedding': embeddings.get('title', []),
            'text_embedding': embeddings.get('text', []),
            'createdAt': now,
            'updatedAt': now
        }
        
        # Insert article
        result = self.articles_users_collection.insert_one(article_doc)
        article_id = result.inserted_id
        
        # Send notifications
        self._send_article_notifications(article_id, user_id, request)
        
        return {
            'status': 'success',
            'message': 'Article created successfully',
            'article_id': str(article_id)
        }, 201

    def update_article(self, article_id: str, update_data: Dict, user_id: int) -> Tuple[Dict, int]:
        """Update an existing article."""
        # Check ownership
        article = self.articles_users_collection.find_one({'_id': ObjectId(article_id)})
        
        if not article or article.get('userId') != user_id:
            return {
                'status': 'error',
                'message': 'Article not found or unauthorized'
            }, 403
        
        # Build update document
        update_doc = {}
        
        for field in ['title', 'text', 'delta', 'category']:
            if field in update_data:
                update_doc[field] = update_data[field]
        
        # Handle image update
        if 'imgCover' in update_data:
            img_path = self._handle_image_upload(update_data['imgCover'])
            if img_path:
                update_doc['imgCover'] = img_path
        
        # Regenerate embeddings if content changed
        if 'title' in update_data or 'delta' in update_data:
            embeddings = self._generate_embeddings(
                update_data.get('title', article.get('title')),
                update_data.get('delta', article.get('delta'))
            )
            update_doc.update({
                'title_embedding': embeddings.get('title', article.get('title_embedding', [])),
                'text_embedding': embeddings.get('text', article.get('text_embedding', []))
            })
        
        update_doc['updatedAt'] = datetime.datetime.now()
        
        # Update article
        self.articles_users_collection.update_one(
            {'_id': ObjectId(article_id)},
            {'$set': update_doc}
        )
        
        # Send WebSocket notification
        updated_article = self.articles_users_collection.find_one({'_id': ObjectId(article_id)})
        send_websocket_notification(
            f"articles_user_{user_id}",
            'article_updated',
            {'article': format_article_data(updated_article)}
        )
        
        return {
            'status': 'success',
            'message': 'Article updated successfully'
        }, 200

    def delete_article(self, article_id: str, user_id: int) -> Tuple[Dict, int]:
        """Delete an article."""
        article = self.articles_users_collection.find_one({'_id': ObjectId(article_id)})
        
        if not article or article.get('userId') != user_id:
            return {
                'status': 'error',
                'message': 'Article not found or unauthorized'
            }, 403
        
        # Delete article
        result = self.articles_users_collection.delete_one({'_id': ObjectId(article_id)})
        
        if result.deleted_count == 1:
            # Send WebSocket notification for article deletion
            send_websocket_notification(
                f"articles_user_{user_id}",
                'article_deleted',
                {'article_id': article_id, 'user_id': user_id}
            )
            
            # Send profile article count update
            article_count = self.articles_users_collection.count_documents({"userId": user_id})
            send_websocket_notification(
                "Profile_group",
                'send_model_update',
                {
                    'data': {
                        'action': 'article_update',
                        'user_id': user_id,
                        'article_count': article_count
                    }
                }
            )
            logger.info(f"Sent article count update to Profile_group for user {user_id}: {article_count} articles")
            
            return {
                'status': 'success',
                'message': 'Article deleted successfully'
            }, 200
        
        return {
            'status': 'error',
            'message': 'Failed to delete article'
        }, 500

    def track_article_read(self, read_data: Dict) -> Tuple[Dict, int]:
        """Track article reading activity."""
        article_id = ObjectId(read_data['article_id'])
        user_id = read_data['user_id']
        
        existing_read = self.reads_collection.find_one({
            'userId': user_id,
            'articleId': article_id
        })
        
        current_time = datetime.datetime.now()
        
        if existing_read:
            # Update existing read
            update_data = {
                '$inc': {'readCount': 1},
                '$set': {
                    'lastReadAt': current_time,
                    'device': read_data.get('device', 'unknown')
                },
                '$push': {'sources': read_data.get('source', 'unknown')}
            }
            
            if 'duration' in read_data:
                update_data['$set']['latestDuration'] = read_data['duration']
            
            if 'read_percentage' in read_data:
                update_data['$set']['latestReadPercentage'] = read_data['read_percentage']
            
            self.reads_collection.update_one(
                {'_id': existing_read['_id']},
                update_data
            )
            
            return {
                'status': 'success',
                'message': 'Article read updated successfully',
                'read_count': existing_read.get('readCount', 0) + 1
            }, 200
        else:
            # Create new read record
            read_doc = {
                'userId': user_id,
                'articleId': article_id,
                'readAt': current_time,
                'lastReadAt': current_time,
                'readCount': 1,
                'sources': [read_data.get('source', 'unknown')],
                'device': read_data.get('device', 'unknown')
            }
            
            if 'duration' in read_data:
                read_doc.update({
                    'initialDuration': read_data['duration'],
                    'latestDuration': read_data['duration']
                })
            
            if 'read_percentage' in read_data:
                read_doc.update({
                    'initialReadPercentage': read_data['read_percentage'],
                    'latestReadPercentage': read_data['read_percentage']
                })
            
            result = self.reads_collection.insert_one(read_doc)
            
            return {
                'status': 'success',
                'message': 'Article read recorded successfully',
                'read_id': str(result.inserted_id),
                'read_count': 1
            }, 201

    def get_time_based_articles(self, user_id: int, request, hours_primary: int = 12, hours_fallback: int = 72) -> List[Dict]:
        """Get time-based personalized articles."""
        # Get articles user has read
        read_articles_cursor = self.reads_collection.find({"userId": user_id}, {"articleId": 1})
        read_article_ids = {read["articleId"] for read in read_articles_cursor}
        
        # Get similar articles
        similar_articles = get_similar_articles(user_id)
        
        # Filter by time and read status
        filtered_articles = filter_articles_by_time(
            similar_articles, read_article_ids, hours_primary, hours_fallback
        )
        
        # Format and return top 5
        return [
            format_article_for_response(article, request)
            for article in filtered_articles[:5]
        ]

    def _generate_embeddings(self, title: str, delta: str) -> Dict:
        """Generate embeddings for title and text."""
        embeddings = {}
        
        try:
            # Title embedding
            title_response = requests.post(
                embed_api_url,
                json={'texts': [title]},
                timeout=30
            )
            if title_response.status_code == 200:
                embeddings['title'] = title_response.json().get('embeddings', [[]])[0]
            
            # Text embedding
            cleaned_text = ""
            try:
                delta_json = json.loads(delta)
                cleaned_text = delta_to_plain_text(delta_json)
            except (json.JSONDecodeError, TypeError):
                cleaned_text = clean_html_tags(delta)
            
            text_response = requests.post(
                embed_api_url,
                json={'texts': [cleaned_text]},
                timeout=60
            )
            if text_response.status_code == 200:
                embeddings['text'] = text_response.json().get('embeddings', [[]])[0]
            
        except requests.RequestException as e:
            logger.error(f"Error generating embeddings: {str(e)}")
        
        return embeddings

    def _handle_image_upload(self, image_file) -> Optional[str]:
        """Handle image file upload."""
        if not image_file:
            return None
        
        current_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"article_{current_date}_{image_file.name}"
        path = os.path.join('article_covers', filename)
        
        saved_path = default_storage.save(path, ContentFile(image_file.read()))
        return f"{settings.MEDIA_URL}{saved_path}"

    def _send_like_notification(self, article_id: str, user_id: int, request):
        """Send notification when article is liked."""
        # Get article and owner info
        article = self.articles_users_collection.find_one({'_id': ObjectId(article_id)})
        if not article:
            return
        
        article_owner_id = article.get('userId')
        if not article_owner_id or article_owner_id == user_id:
            return
        
        try:
            actor_user = User.objects.get(id=user_id)
            now = datetime.datetime.now()
            
            # Save notification
            notification_data = {
                "user_id": article_owner_id,
                "type": "like",
                "actor_id": user_id,
                "target": {"type": "article", "id": ObjectId(article_id)},
                "created_at": now,
                "is_read": False,
                "extra_data": {
                    "article_title": article.get("title", "a post"),
                    "article_img_cover": request.build_absolute_uri(article.get("imgCover", ""))
                }
            }
            result = self.notifications_collection.insert_one(notification_data)
            
            # Send real-time notification
            user_data = get_user_profile_data(user_id)
            
            notification_payload = {
                "_id": str(result.inserted_id),
                "user_id": article_owner_id,
                "type": "like",
                "actor_id": user_id,
                "actor_username": actor_user.username,
                "actor_profile_img": user_data['profilePicture'],
                "target": {"type": "article", "id": str(article_id)},
                "created_at": now.isoformat(),
                "is_read": False,
                "extra_data": notification_data["extra_data"]
            }
            
            send_websocket_notification(
                f"notification_user_{article_owner_id}",
                "send_notification",
                {"data": notification_payload}
            )
            
        except Exception as e:
            logger.error(f"Failed to send like notification: {str(e)}")

    def _send_article_notifications(self, article_id: ObjectId, user_id: int, request):
        """Send notifications when new article is created."""
        try:
            # Get article
            article = self.articles_users_collection.find_one({'_id': article_id})
            if not article:
                return
            
            # Notify author
            send_websocket_notification(
                f"articles_user_{user_id}",
                'article_created',
                {'article': format_article_data(article)}
            )
            
            # Notify followers
            followers = Follow.objects.filter(followed_id=user_id).select_related('follower')
            if followers:
                actor_user = User.objects.get(id=user_id)
                user_data = get_user_profile_data(user_id)
                now = datetime.datetime.now()
                
                # Save notifications for followers
                notifications_to_save = []
                for follow in followers:
                    notifications_to_save.append({
                        "user_id": follow.follower.id,
                        "type": "new_article",
                        "actor_id": user_id,
                        "target": {"type": "new_article", "article_id": article_id},
                        "created_at": now,
                        "is_read": False,
                        "extra_data": {
                            "title": article.get('title', ''),
                            "imgCover": article.get('imgCover', '')
                        }
                    })
                
                if notifications_to_save:
                    self.notifications_collection.insert_many(notifications_to_save)
                
                # Send real-time notification
                notification_payload = {
                    "type": "new_article",
                    "actor_id": user_id,
                    "actor_username": actor_user.username,
                    "actor_profile_img": user_data['profilePicture'],
                    "target_id": {"type": "new_article", "article_id": str(article_id)},
                    "created_at": now.isoformat(),
                    "read": False,
                    "extra_data": {
                        "title": article.get('title', ''),
                        "imgCover": article.get('imgCover', '')
                    }
                }
                
                send_websocket_notification(
                    f"new_article_feed_{user_id}",
                    "new_article_notification",
                    {"data": notification_payload}
                )
            
            # Update profile article count
            article_count = self.articles_users_collection.count_documents({"userId": user_id})
            send_websocket_notification(
                "Profile_group",
                'send_model_update',
                {
                    'data': {
                        'action': 'article_update',
                        'user_id': user_id,
                        'article_count': article_count
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send article notifications: {str(e)}")


class SaveService:
    def __init__(self):
        self.saved_collection = get_collection('saved')
        self.save_directory_collection = get_collection('save_directory')
        self.articles_users_collection = get_collection('articles_users')
        self.articles_collection = get_collection('articles')

    def create_directory(self, name: str, user_id: int) -> Tuple[Dict, int]:
        """Create a new save directory."""
        now = datetime.datetime.now()
        directory_data = {
            'name': name,
            'userId': user_id,
            'createdAt': now
        }
        
        result = self.save_directory_collection.insert_one(directory_data)
        
        return {
            'status': 'success',
            'message': 'Save directory created successfully',
            'directory': {
                'id': str(result.inserted_id),
                'name': name,
                'createdAt': now.isoformat()
            }
        }, 201

    def get_directories(self, user_id: int) -> List[Dict]:
        """Get all directories for a user."""
        directories = self.save_directory_collection.find({'userId': user_id})
        
        directories_list = []
        for directory in directories:
            article_count = self.saved_collection.count_documents({
                'userId': user_id,
                'directoryId': directory['_id']
            })
            
            directories_list.append({
                'id': str(directory['_id']),
                'name': directory.get('name', ''),
                'createdAt': directory.get('createdAt').isoformat() if directory.get('createdAt') else None,
                'articleCount': article_count
            })
        
        return directories_list

    def toggle_save(self, article_id: str, user_id: int, directory_id: str = None) -> Tuple[Dict, int]:
        """Toggle save status for an article."""
        existing_save = self.saved_collection.find_one({
            'articleId': ObjectId(article_id),
            'userId': user_id
        })
        
        if existing_save:
            # Remove save
            result = self.saved_collection.delete_one({'_id': existing_save['_id']})
            return {
                'status': 'success',
                'message': 'Article unsaved successfully',
                'saved': False
            }, 200
        else:
            # Add save
            now = datetime.datetime.now()
            save_data = {
                'articleId': ObjectId(article_id),
                'userId': user_id,
                'createdAt': now
            }
            
            if directory_id:
                save_data['directoryId'] = ObjectId(directory_id)
            
            result = self.saved_collection.insert_one(save_data)
            
            # Get directory name if specified
            directory_name = None
            if directory_id:
                directory = self.save_directory_collection.find_one({'_id': ObjectId(directory_id)})
                if directory:
                    directory_name = directory.get('name')
            
            return {
                'status': 'success',
                'message': 'Article saved successfully',
                'saved': True,
                'save_id': str(result.inserted_id),
                'directoryId': directory_id,
                'directoryName': directory_name
            }, 201

    def get_saved_articles(self, user_id: int) -> List[Dict]:
        """Get all saved articles for a user."""
        saved_articles_cursor = self.saved_collection.find({'userId': user_id})
        
        response_list = []
        
        for saved_doc in saved_articles_cursor:
            article_id = saved_doc.get('articleId')
            if not article_id:
                continue
            
            # Get article details
            article = self.articles_users_collection.find_one({'_id': article_id})
            source_collection = 'articles_users'
            
            if not article:
                article = self.articles_collection.find_one({'_id': article_id})
                source_collection = 'articles'
            
            if not article:
                continue
            
            # Get article counts
            counts = get_article_counts(article_id)
            
            article_details = {
                'id': str(article['_id']),
                'title': article.get('title', ''),
                'category': article.get('category', ''),
                'imgCover': article.get('imgCover', ''),
                'createdAt': article.get('createdAt').isoformat() if article.get('createdAt') else None,
                **counts
            }
            
            if source_collection == 'articles_users':
                user_data = get_user_profile_data(article.get('userId'))
                article_details.update({
                    'username': user_data['username'],
                    'profilePicture': user_data['profilePicture'],
                    'imgCover': f'{base_url}{article.get("imgCover", "")}'
                })
            else:
                article_details.update({
                    'username': 'AI',
                    'profilePicture': 'http://localhost:8001/media/profile_pics/default.png'
                })
            
            # Format save details
            save_details = {
                'save_id': str(saved_doc['_id']),
                'articleId': str(saved_doc.get('articleId')),
                'userId': saved_doc.get('userId'),
                'directoryId': str(saved_doc.get('directoryId')) if saved_doc.get('directoryId') else None,
                'createdAt': saved_doc.get('createdAt').isoformat() if saved_doc.get('createdAt') else None,
            }
            
            combined_item = {
                'save_details': save_details,
                'article_details': article_details
            }
            
            response_list.append(combined_item)
        
        return response_list

    def check_saved(self, article_id: str, user_id: int) -> Dict:
        """Check if article is saved by user."""
        saved = self.saved_collection.find_one({
            'articleId': ObjectId(article_id),
            'userId': user_id
        })
        
        directory_info = None
        if saved and saved.get('directoryId'):
            directory = self.save_directory_collection.find_one({'_id': saved.get('directoryId')})
            if directory:
                directory_info = {
                    'id': str(directory['_id']),
                    'name': directory.get('name', '')
                }
        
        return {
            'status': 'success',
            'is_saved': saved is not None,
            'save_id': str(saved['_id']) if saved else None,
            'directory': directory_info
        }

    def delete_directory(self, directory_id: str, user_id: int) -> Tuple[Dict, int]:
        """Delete a save directory."""
        directory = self.save_directory_collection.find_one({
            '_id': ObjectId(directory_id),
            'userId': user_id
        })
        
        if not directory:
            return {
                'status': 'error',
                'message': 'Directory not found or unauthorized'
            }, 404
        
        # Remove directory reference from saved articles
        self.saved_collection.update_many(
            {'directoryId': ObjectId(directory_id), 'userId': user_id},
            {'$unset': {'directoryId': ''}}
        )
        
        # Delete directory
        result = self.save_directory_collection.delete_one({'_id': ObjectId(directory_id)})
        
        if result.deleted_count == 1:
            return {
                'status': 'success',
                'message': 'Directory deleted successfully'
            }, 200
        
        return {
            'status': 'error',
            'message': 'Failed to delete directory'
        }, 500

    def update_directory(self, directory_id: str, name: str, user_id: int) -> Tuple[Dict, int]:
        """Update directory name."""
        directory = self.save_directory_collection.find_one({
            '_id': ObjectId(directory_id),
            'userId': user_id
        })
        
        if not directory:
            return {
                'status': 'error',
                'message': 'Directory not found or unauthorized'
            }, 404
        
        result = self.save_directory_collection.update_one(
            {'_id': ObjectId(directory_id)},
            {'$set': {'name': name}}
        )
        
        if result.modified_count == 1:
            return {
                'status': 'success',
                'message': 'Directory name updated successfully',
                'directory': {'id': directory_id, 'name': name}
            }, 200
        
        return {
            'status': 'error',
            'message': 'Failed to update directory name'
        }, 500