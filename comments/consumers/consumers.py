import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs
from comments.consumers.services.consumer_services import (
    send_initial_comments,
    close_mongo_connection,
)

logger = logging.getLogger(__name__)

class CommentsConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.article_id = None
        self.mongo_client = None
        self.db = None
        self.comments_collection = None
        self.user = None
        self.group_name = None

    async def connect(self):
        """
        Handle WebSocket connection.
        Extract article_id from URL parameters and authenticate user.
        """
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        query_string = self.scope["query_string"].decode()
        query_params = parse_qs(query_string)

        if "article_id" not in query_params:
            await self.close()
            return

        self.article_id = query_params["article_id"][0]
        self.group_name = f"chat_{self.article_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        await send_initial_comments(self)

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        Remove user from group.
        """
        if self.group_name:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

        if self.mongo_client:
            close_mongo_connection(self.mongo_client)

    async def receive(self, text_data):
        """
        Handle messages received from WebSocket.
        This is a read-only consumer, so we don't process any incoming messages.
        """
        pass

    async def chat_message(self, event):
        """
        Handle chat messages from group.
        Send message to WebSocket.
        """
        await self.send(text_data=json.dumps(event["message"]))