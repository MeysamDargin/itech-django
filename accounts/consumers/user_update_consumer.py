import json
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .handlers import get_user_data, get_user_object, update_user_data


class UserUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_authenticated:
            self.user_id = user.id
            await self.channel_layer.group_add("User_group", self.channel_name)
            await self.accept()
            await self.fetch_and_send_user()
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("User_group", self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get("action") == "update":
                await update_user_data(self.user_id, data)
                await self.fetch_and_send_user()
        except Exception as e:
            print(f"Error processing data: {e}")

    async def send_model_update(self, event):
        data = event["data"]
        if isinstance(data.get("date_joined"), datetime.datetime):
            data["date_joined"] = data["date_joined"].isoformat()
        await self.send(text_data=json.dumps(data))

    async def fetch_and_send_user(self):
        user_data = await get_user_data(self.user_id)
        if user_data:
            await self.send(text_data=json.dumps(user_data))
