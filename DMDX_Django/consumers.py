# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class DeliveryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'delivery_updates'

        # Приєднатися до групи
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Від'єднатися від групи
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Отримати повідомлення від групи
    async def receive(self, text_data):
        await self.send(text_data=json.dumps({
            'message': text_data
        }))

    # Отримати повідомлення від групи (метод, який буде викликаний з threading_create_delivery_async)
    async def delivery_complete(self, event):
        message = event['message']
        delivery_order_id = event['delivery_order_id']

        await self.send(text_data=json.dumps({
            'message': message,
            'delivery_order_id': delivery_order_id
        }))
