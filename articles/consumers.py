import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from config.mongo_utils import get_collection
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

# دریافت مجموعه MongoDB یک بار در سطح ماژول
articles_users_collection = get_collection('articles_users')
likes_collection = get_collection('likes')
comments_collection = get_collection('comments')

class ChengArticlesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection"""
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning("Unauthenticated user tried to connect to articles WebSocket")
            await self.close()
            return
        
        self.user = user
        self.user_id = user.id
        self.group_name = f"articles_user_{self.user_id}"
        
        if self.channel_layer is not None:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
        else:
            logger.warning("Channel layer is not available")
        
        await self.accept()
        await self.send_user_articles()
        logger.info(f"User {self.user_id} connected to articles WebSocket")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name') and self.channel_layer is not None:
            # Leave user-specific group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        
        logger.info(f"User {self.user_id if hasattr(self, 'user_id') else 'Unknown'} disconnected from articles WebSocket")

    async def receive(self, text_data):
        """Handle messages received from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            if message_type == 'get_articles':
                # Refresh articles when requested
                await self.send_user_articles()
            elif message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': str(asyncio.get_event_loop().time())
                }))
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in WebSocket")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")

    async def send_user_articles(self):
        """Fetch and send user's articles"""
        try:
            articles = await self.get_user_articles()
            await self.send(text_data=json.dumps({
                'type': 'articles_list',
                'articles': articles,
                'user_id': self.user_id,
                'count': len(articles)
            }))
        except Exception as e:
            logger.error(f"Error sending user articles: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to fetch articles'
            }))

    @database_sync_to_async
    def get_user_articles(self):
        """Fetch user's articles from MongoDB"""
        try:
            cursor = articles_users_collection.find({'userId': self.user_id})
            articles = []
            
            for article in cursor:
                article_id = article['_id']
                
                # Get like count for this article
                like_count = likes_collection.count_documents({'articleId': article_id})
                
                # Get comment count for this article
                comment_count = comments_collection.count_documents({'article_id': str(article_id)})
                
                # Convert ObjectId to string and format dates
                article_data = {
                    '_id': str(article['_id']),
                    'title': article.get('title', ''),
                    'text': article.get('text', ''),
                    'delta': article.get('delta', ''),
                    'imgCover': article.get('imgCover', ''),
                    'category': article.get('category', ''),
                    'userId': article.get('userId'),
                    'likes_count': like_count,
                    'comments_count': comment_count,
                    'createdAt': article.get('createdAt').isoformat() if article.get('createdAt') else None,
                    'updatedAt': article.get('updatedAt').isoformat() if article.get('updatedAt') else None
                }
                articles.append(article_data)
            
            # Sort by creation date (newest first)
            articles.sort(key=lambda x: x['createdAt'] if x['createdAt'] else '', reverse=True)
            
            return articles
        except Exception as e:
            logger.error(f"Error fetching user articles from MongoDB: {str(e)}")
            return []

    # Handle messages from group
    async def article_created(self, event):
        """Handle article creation signal"""
        article = event['article']
        if article.get('userId') == self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'article_created',
                'article': article
            }))

    async def article_updated(self, event):
        """Handle article update signal"""
        article = event['article']
        if article.get('userId') == self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'article_updated',
                'article': article
            }))

    async def article_deleted(self, event):
        """Handle article deletion signal"""
        article_id = event['article_id']
        user_id = event['user_id']
        if user_id == self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'article_deleted',
                'article_id': article_id
            }))

    async def change_stream_notification(self, event):
        """Handle change stream notifications"""
        await self.send(text_data=json.dumps(event['data']))
