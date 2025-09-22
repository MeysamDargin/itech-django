from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .models import Profile
from asgiref.sync import sync_to_async
from django.db.models import Count
from following.models import Follow
from django.contrib.auth.models import User
import logging

# تنظیم لاگر
logger = logging.getLogger(__name__)


class ChengProfilesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_authenticated:
            self.user_id = user.id
            await self.channel_layer.group_add("Profile_group", self.channel_name)
            await self.accept()
            logger.info(f"WebSocket: User {user.username} connected to Profile_group.")

            # ارسال داده‌های اولیه به کلاینت
            await self.fetch_and_send_profiles()
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("Profile_group", self.channel_name)
        logger.info(f"WebSocket: User disconnected from Profile_group with code {close_code}.")

    async def receive(self, text_data):
        """دریافت داده‌های ارسالی از کلاینت و ذخیره در دیتابیس"""
        try:
            data = json.loads(text_data)
            action = data.get("action")
            logger.info(f"WebSocket: Received action {action} from client.")

            if action == "update":
                # ذخیره تغییرات در پروفایل کاربر
                await self.update_user_profile(data)

                # ارسال داده‌های به‌روز شده به کلاینت
                await self.fetch_and_send_profiles()

        except Exception as e:
            logger.error(f"WebSocket: Error processing received data: {e}")
            # ارسال کد وضعیت 500 در صورت بروز خطا
            await self.send(text_data=json.dumps({"status": 500, "message": "Internal server error."}))

    async def send_model_update(self, event):
        data = event["data"]
        logger.info(f"WebSocket: Received model update event with data: {data}")
        if data.get("user_id") == self.user_id:
            logger.info(f"WebSocket: Sending model update to user {self.user_id}")
            await self.send(text_data=json.dumps(data))

    async def fetch_and_send_profiles(self):
        """دریافت داده‌های پروفایل از دیتابیس و ارسال به کلاینت"""
        try:
            profile = await self.get_user_profile(self.user_id)
            if profile:
                # دریافت تعداد مقالات، فالوئرها و فالوئینگ‌ها
                article_count = await self.get_user_article_count(self.user_id)
                follower_count = await self.get_follower_count(self.user_id)
                following_count = await self.get_following_count(self.user_id)
                
                logger.info(f"WebSocket: Fetched profile data for user {self.user_id} - articles: {article_count}, followers: {follower_count}, following: {following_count}")
                
                formatted_data = {
                    "action": "updated",
                    "status": 200,  # ارسال کد وضعیت 200
                    "id": profile.id,
                    "user_profile": profile.user.username,
                    "user_id": profile.user.id,
                    "first_name": profile.first_name,
                    "job_title": profile.job_title,
                    "bio": profile.bio,
                    "phone_number": profile.phone_number,
                    "country": profile.country,
                    "website": profile.website,
                    "city_state": profile.city_state,
                    "last_name": profile.last_name,
                    "profile_picture": profile.profile_picture.url if profile.profile_picture else None,
                    "profile_caver": profile.profile_caver.url if profile.profile_caver else None,
                    "article_count": article_count,
                    "follower_count": follower_count,
                    "following_count": following_count,
                }
                await self.send(text_data=json.dumps(formatted_data))
            else:
                logger.warning(f"WebSocket: No profile found for user ID {self.user_id}")
                # ارسال کد وضعیت 404 اگر پروفایل پیدا نشد
                await self.send(text_data=json.dumps({"status": 404, "message": "Profile not found."}))
        except Exception as e:
            logger.error(f"WebSocket: Error fetching profiles: {e}")
            # ارسال کد وضعیت 500 در صورت بروز خطا
            await self.send(text_data=json.dumps({"status": 500, "message": "Internal server error."}))
    
    @staticmethod
    async def get_user_profile(user_id):
        """دریافت پروفایل کاربر به‌صورت async"""
        try:
            return await Profile.objects.select_related("user").aget(user_id=user_id)
        except Profile.DoesNotExist:
            logger.error(f"WebSocket: Profile does not exist for user {user_id}")
            return None
    
    @staticmethod
    async def get_user_article_count(user_id):
        """دریافت تعداد مقالات کاربر به‌صورت async"""
        try:
            from config.mongo_utils import get_collection
            articles_users_collection = get_collection('articles_users')
            # استفاده از count_documents برای شمارش مقالات کاربر
            count = await sync_to_async(articles_users_collection.count_documents)({"userId": user_id})
            return count
        except Exception as e:
            logger.error(f"WebSocket: Error counting user articles: {e}")
            return 0
    
    @staticmethod
    async def get_follower_count(user_id):
        """دریافت تعداد فالوئرها به‌صورت async"""
        try:
            count = await sync_to_async(Follow.objects.filter(followed_id=user_id).count)()
            return count
        except Exception as e:
            logger.error(f"WebSocket: Error counting followers: {e}")
            return 0
    
    @staticmethod
    async def get_following_count(user_id):
        """دریافت تعداد فالوئینگ‌ها به‌صورت async"""
        try:
            count = await sync_to_async(Follow.objects.filter(follower_id=user_id).count)()
            return count
        except Exception as e:
            logger.error(f"WebSocket: Error counting following: {e}")
            return 0
