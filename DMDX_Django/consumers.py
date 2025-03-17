# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class DeliveryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("WebSocket connection attempt")
        self.group_name = 'delivery_updates'

        # Приєднатися до групи
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        logger.info(f"Added to group: {self.group_name}")

        await self.accept()
        logger.info("WebSocket connection accepted")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        # Від'єднатися від групи
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"Removed from group: {self.group_name}")

    # Отримати повідомлення від групи
    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")
        await self.send(text_data=json.dumps({
            'message': text_data
        }))

    # Отримати повідомлення від групи (метод, який буде викликаний з threading_create_delivery_async)
    async def delivery_complete(self, event):
        logger.info(f"Received delivery_complete event: {event}")
        message = event['message']
        delivery_order_id = event['delivery_order_id']

        await self.send(text_data=json.dumps({
            'message': message,
            'delivery_order_id': delivery_order_id
        }))
        logger.info(f"Sent message to client: {message}")


class NPDocumentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("NP Document WebSocket connection attempt")
        self.group_name = 'np_document_updates'

        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        logger.info(f"Added to NP document group: {self.group_name}")

        await self.accept()
        logger.info("NP Document WebSocket connection accepted")

    async def disconnect(self, close_code):
        logger.info(f"NP Document WebSocket disconnected with code: {close_code}")
        # Leave the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"Removed from NP document group: {self.group_name}")

    async def receive(self, text_data):
        logger.info(f"NP Document received message: {text_data}")
        await self.send(text_data=json.dumps({
            'message': text_data
        }))

    async def delivery_message(self, event):
        logger.info(f"NP Document received delivery_message event: {event}")
        message = event['message']
        delivery_order_id = event['delivery_order_id']

        await self.send(text_data=json.dumps({
            'message': message,
            'delivery_order_id': delivery_order_id
        }))
        logger.info(f"NP Document sent message to client: {message}")
