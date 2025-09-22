from bson import ObjectId
from django.contrib.auth.models import User
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime
import logging

from profiles.models import Profile
from config.mongo_utils import get_collection

logger = logging.getLogger(__name__)


def get_user_info(user_id):
    try:
        user = User.objects.get(id=user_id)
        try:
            profile = Profile.objects.get(user=user)
            profile_picture = profile.profile_picture.url if profile.profile_picture else None
            return {
                "first_name": profile.first_name or user.first_name,
                "last_name": profile.last_name or user.last_name,
                "profile_picture": profile_picture
            }
        except Profile.DoesNotExist:
            return {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "profile_picture": None
            }
    except User.DoesNotExist:
        return {
            "first_name": "",
            "last_name": "",
            "profile_picture": None
        }

def format_comment(comment):
    comment['_id'] = str(comment['_id'])
    comment['article_id'] = str(comment['article_id'])
    
    user_id = comment['user_id']
    user_info = get_user_info(user_id)
    comment['user_info'] = user_info
    comment['user_id'] = str(user_id)
    
    if 'seen' not in comment:
        comment['seen'] = False
    
    if comment.get('reply_to'):
        reply_to_id = comment['reply_to']
        comments_collection = get_collection('comments')
        try:
            parent_comment = comments_collection.find_one({"_id": reply_to_id})
            if parent_comment:
                parent_user_id = parent_comment['user_id']
                parent_user_info = get_user_info(parent_user_id)
                
                comment['reply_to'] = {
                    "_id": str(reply_to_id),
                    "message": parent_comment['message'],
                    "user_id": str(parent_user_id),
                    "user_info": parent_user_info
                }
            else:
                comment['reply_to'] = str(reply_to_id)
        except Exception as e:
            logger.error(f"Error getting parent comment: {str(e)}")
            comment['reply_to'] = str(reply_to_id)
    
    if isinstance(comment.get('created_at'), datetime):
        comment['created_at'] = comment['created_at'].isoformat()
    
    return comment

def send_to_group(article_id, message_type, comment_data):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{article_id}",
            {
                "type": "chat_message",
                "message": {
                    "type": message_type,
                    "comment": comment_data
                }
            }
        )
        logger.info(f"Sent {message_type} signal to group chat_{article_id}")
    except Exception as e:
        logger.error(f"Error sending to WebSocket group: {str(e)}")


def send_notification(user_id, notification_data):
    """Sends a real-time notification to a user."""
    try:
        channel_layer = get_channel_layer()
        # Ensure all data is JSON serializable
        if '_id' in notification_data and isinstance(notification_data['_id'], ObjectId):
            notification_data['_id'] = str(notification_data['_id'])
        if 'created_at' in notification_data and isinstance(notification_data['created_at'], datetime):
            notification_data['created_at'] = notification_data['created_at'].isoformat()
        
        # Convert ObjectIds in target field
        if 'target' in notification_data:
            for key, value in notification_data['target'].items():
                if isinstance(value, ObjectId):
                    notification_data['target'][key] = str(value)

        async_to_sync(channel_layer.group_send)(
            f"notification_user_{user_id}",
            {
                "type": "send_notification",
                "data": notification_data,
            },
        )
        logger.info(f"Sent notification to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")


def create_comment_service(data, user):
    try:
        article_id_str = data.get('article_id')
        message = data.get('message')
        reply_to_str = data.get('reply_to')

        now = datetime.utcnow()

        comment_to_save = {
            "article_id": ObjectId(article_id_str),
            "user_id": user.id,
            "message": message,
            "created_at": now,
            "reply_to": ObjectId(reply_to_str) if reply_to_str else None,
            "seen": False
        }
        
        comments_collection = get_collection('comments')
        result = comments_collection.insert_one(comment_to_save)
        new_comment_id = result.inserted_id

        # Notification Logic
        notifications_collection = get_collection('notifications')
        
        article = None
        articles_users_collection = get_collection('articles_users')
        article = articles_users_collection.find_one({"_id": ObjectId(article_id_str)})
        if not article:
             articles_collection = get_collection('articles')
             article = articles_collection.find_one({"_id": ObjectId(article_id_str)})

        article_img_cover = ""
        if article:
            img_cover = article.get('imgCover', '')
            # This part needs a request object to build absolute URI, which is not available in service.
            # For now, we'll assume the image URL is absolute or handle it on the client-side.
            article_img_cover = img_cover

        if reply_to_str:
            parent_comment = comments_collection.find_one({"_id": ObjectId(reply_to_str)})
            if parent_comment:
                recipient_id = parent_comment.get('user_id')
                if recipient_id and recipient_id != user.id:
                    notification_to_save = {
                        "user_id": recipient_id,
                        "type": "comment_reply",
                        "actor_id": user.id,
                        "target": {
                            "type": "comment_reply",
                            "replying_to_comment": ObjectId(reply_to_str),
                            "new_comment": new_comment_id,
                            "article_id": ObjectId(article_id_str)
                        },
                        "created_at": now,
                        "is_read": False,
                        "extra_data": {
                            "comment": message,
                            "article_img_cover": article_img_cover
                        }
                    }
                    notif_result = notifications_collection.insert_one(notification_to_save)
                    # WebSocket notification for reply
                    send_notification(recipient_id, notification_to_save)
        else:
            comment_count = comments_collection.count_documents({"article_id": ObjectId(article_id_str)})
            if comment_count == 1:
                if article:
                    recipient_id = article.get('userId')
                    if recipient_id and recipient_id != user.id:
                        notification_to_save = {
                            "user_id": recipient_id,
                            "type": "comment_create",
                            "actor_id": user.id,
                            "target": {
                                "type": "comment_create",
                                "id": new_comment_id,
                                "article_id": ObjectId(article_id_str)
                            },
                            "created_at": now,
                            "is_read": False,
                            "extra_data": {
                                "comment": message,
                                "article_img_cover": article_img_cover
                            }
                        }
                        notif_result = notifications_collection.insert_one(notification_to_save)
                        # WebSocket notification for first comment
                        send_notification(recipient_id, notification_to_save)

        new_comment_doc = comments_collection.find_one({"_id": new_comment_id})
        formatted_comment = format_comment(new_comment_doc)
        send_to_group(article_id_str, "comment_created", formatted_comment)
        
        return formatted_comment
            
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        raise e

def update_comment_service(comment_id, data, user):
    try:
        message = data.get('message')
        
        comments_collection = get_collection('comments')
        
        comment = comments_collection.find_one({"_id": ObjectId(comment_id)})
        
        if not comment:
            raise Exception("Comment not found")
        
        if comment['user_id'] != user.id:
            raise Exception("You don't have permission to edit this comment")
        
        comments_collection.update_one(
            {"_id": ObjectId(comment_id)},
            {"$set": {"message": message}}
        )
        
        updated_comment = comments_collection.find_one({"_id": ObjectId(comment_id)})
        
        formatted_comment = format_comment(updated_comment)
        
        article_id = str(comment['article_id'])
        send_to_group(article_id, "comment_updated", formatted_comment)
        
        return formatted_comment
            
    except Exception as e:
        logger.error(f"Error updating comment: {str(e)}")
        raise e

def delete_comment_service(comment_id, user):
    try:
        comments_collection = get_collection('comments')
        
        comment = comments_collection.find_one({"_id": ObjectId(comment_id)})
        
        if not comment:
            raise Exception("Comment not found")
        
        if comment['user_id'] != user.id:
            raise Exception("You don't have permission to delete this comment")
        
        formatted_comment = format_comment(comment)
        article_id = formatted_comment['article_id']
        
        comments_collection.delete_one({"_id": ObjectId(comment_id)})
        
        send_to_group(article_id, "comment_deleted", {"_id": comment_id})
        
        return comment_id
            
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        raise e

def seen_comments_service(data):
    try:
        article_id = data.get('article_id')
        comment_ids = data.get('comment_ids', [])
        
        if not article_id or not comment_ids:
            raise Exception("Missing required fields")
        
        object_ids = [ObjectId(comment_id) for comment_id in comment_ids]
        
        comments_collection = get_collection('comments')
        
        result = comments_collection.update_many(
            {
                "_id": {"$in": object_ids},
                "article_id": ObjectId(article_id)
            },
            {"$set": {"seen": True}}
        )
        
        updated_comments = list(comments_collection.find({"_id": {"$in": object_ids}}))
        formatted_comments = [format_comment(comment) for comment in updated_comments]
        
        send_to_group(article_id, "comments_seen", {
            "comment_ids": comment_ids,
            "article_id": article_id
        })
        
        return {
            "modified_count": result.modified_count,
            "comments": formatted_comments
        }
            
    except Exception as e:
        logger.error(f"Error marking comments as seen: {str(e)}")
        raise e