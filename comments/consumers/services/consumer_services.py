import json
import logging
from django.conf import settings
from bson import ObjectId
import pymongo
from django.contrib.auth.models import User
from profiles.models import Profile
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)

def connect_to_mongo():
    """
    Connect to MongoDB.
    """
    try:
        mongo_client = pymongo.MongoClient(settings.MONGODB_URI)
        db_name = settings.MONGODB_URI.split('/')[-1].split('?')[0]
        db = mongo_client[db_name]
        comments_collection = db["comments"]
        logger.info(f"Connected to MongoDB database: {db_name}")
        return mongo_client, db, comments_collection
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}")
        return None, None, None

def close_mongo_connection(mongo_client):
    """
    Close MongoDB connection.
    """
    if mongo_client:
        mongo_client.close()

@database_sync_to_async
def get_user_info(user_id):
    """Get user information (first name, last name, profile picture)"""
    try:
        user = User.objects.get(id=user_id)
        try:
            profile = Profile.objects.get(user=user)
            profile_picture = profile.profile_picture.url if profile.profile_picture else None
            return {
                "first_name": profile.first_name or user.first_name,
                "last_name": profile.last_name or user.last_name,
                "profile_picture": profile_picture,
                "username": user.username
            }
        except Profile.DoesNotExist:
            return {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "profile_picture": None,
                "username": user.username
            }
    except User.DoesNotExist:
        return {
            "first_name": "",
            "last_name": "",
            "profile_picture": None
        }

async def format_comment(comment, comments_collection):
    """
    Format comment for WebSocket.
    """
    comment["_id"] = str(comment["_id"])
    comment["article_id"] = str(comment["article_id"])

    user_id = comment["user_id"]
    user_info = await get_user_info(user_id)
    comment["user_info"] = user_info
    comment["user_id"] = str(user_id)

    if "seen" not in comment:
        comment["seen"] = False

    if comment.get("reply_to"):
        reply_to_id = comment["reply_to"]
        try:
            parent_comment = comments_collection.find_one({"_id": reply_to_id})
            if parent_comment:
                parent_user_id = parent_comment["user_id"]
                parent_user_info = await get_user_info(parent_user_id)
                comment["reply_to"] = {
                    "_id": str(reply_to_id),
                    "message": parent_comment["message"],
                    "user_id": str(parent_user_id),
                    "user_info": parent_user_info
                }
            else:
                comment["reply_to"] = str(reply_to_id)
        except Exception as e:
            logger.error(f"Error getting parent comment: {str(e)}")
            comment["reply_to"] = str(reply_to_id)

    if "created_at" in comment and comment["created_at"]:
        comment["created_at"] = comment["created_at"].isoformat()

    return comment

async def send_initial_comments(consumer):
    """
    Send initial comments to client.
    """
    mongo_client, db, comments_collection = connect_to_mongo()
    if not mongo_client:
        await consumer.close()
        return

    consumer.mongo_client = mongo_client
    consumer.db = db
    consumer.comments_collection = comments_collection

    try:
        comments = list(consumer.comments_collection.find({"article_id": ObjectId(consumer.article_id)}))
        formatted_comments = []
        for comment in comments:
            formatted_comment = await format_comment(comment, consumer.comments_collection)
            formatted_comments.append(formatted_comment)

        await consumer.send(text_data=json.dumps({
            "type": "comments_list",
            "comments": formatted_comments
        }))
        logger.info(f"Sent {len(formatted_comments)} comments to client for article {consumer.article_id}")
    except Exception as e:
        logger.error(f"Error sending initial comments: {str(e)}")
        await consumer.close()