# messaging/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, Contact, UserStatus
from django.utils.timezone import now
from django.db.models import Q
from urllib.parse import parse_qs

User = get_user_model()

import logging
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("Attempting WebSocket connection...")
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            logger.warning("User not authenticated, closing connection")
            await self.close()
            return

        query_params = parse_qs(self.scope["query_string"].decode())
        self.contact_id = query_params.get("contact_id", [None])[0]

        if not self.contact_id:
            logger.error("Missing contact_id in WebSocket request, closing connection")
            await self.close()
            return

        self.user_group = f"user_{self.user.id}"
        self.room_group_name = f"chat_{self.contact_id}"

        # Join user-specific & chat-specific groups
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Mark user as online
        await self.set_user_online(True)
        await self.notify_status_change(True)

        logger.info("WebSocket connection accepted")
        await self.accept()

    async def disconnect(self, close_code):
        logger.info(f"Disconnecting with code: {close_code}")
        if hasattr(self, 'user_group'):
            # Leave user's group
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )
            
            # Set user as offline
            await self.set_user_online(False)
            await self.notify_status_change(False)
            logger.info("Cleanup completed")

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'message')

        if message_type == 'message':
            await self.handle_message(data)
        elif message_type == 'edit':
            await self.handle_edit_message(data)
        elif message_type == 'typing':
            await self.handle_typing(data)
        elif message_type == 'read':
            await self.handle_read_status(data)

    async def handle_message(self, data):
        try:
            receiver_id = data.get('receiver')
            content = data.get('content')
            is_image = data.get('is_image', False)
            image_url = data.get('image_url')

            if not receiver_id or not content:
                logger.warning("Missing receiver_id or content in message")
                return

            # Save message to database
            message = await self.save_message(
                receiver_id=receiver_id,
                content=content,
                is_image=is_image,
                image_url=image_url
            )

            # Get avatar URL instead of ImageFieldFile
            avatar_url = self.user.avatar.url if self.user.avatar else None

            # Update last message for contacts
            await self.update_last_message(message)

            message_data = {
                'type': 'chat_message',
                'message': {
                    'id': str(message.id),
                    'content': message.content,
                    'senderId': str(self.user.id),
                    'senderName': self.user.username,
                    'senderAvatar': avatar_url,  # Use URL instead of ImageFieldFile
                    'isImage': message.is_image,
                    'imageUrl': message.image_url.url if message.image_url else None,  # Get URL if exists
                    'timestamp': message.created_at.isoformat(),
                    'isRead': False
                }
            }

            # Send to receiver's group
            await self.channel_layer.group_send(
                f"user_{receiver_id}",
                message_data
            )

            # Send back to sender's group
            await self.channel_layer.group_send(
                self.user_group,
                message_data
            )
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to send message'
            }))

    async def handle_edit_message(self, data):
        message_id = data.get('message_id')
        new_content = data.get('content')

        message = await self.edit_message(message_id, new_content)
        if message:
            edit_data = {
                'type': 'message_edited',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'edited_at': message.edited_at.isoformat()
                }
            }

            # Notify both sender and receiver
            await self.channel_layer.group_send(
                self.user_group,
                edit_data
            )
            await self.channel_layer.group_send(
                f"user_{message.receiver.id}",
                edit_data
            )

    async def handle_typing(self, data):
        receiver_id = data.get('receiver')
        is_typing = data.get('is_typing', False)

        if receiver_id:
            await self.channel_layer.group_send(
                f"user_{receiver_id}",
                {
                    'type': 'typing_status',
                    'user_id': self.user.id,
                    'is_typing': is_typing
                }
            )

    async def handle_read_status(self, data):
        sender_id = data.get('sender')
        if sender_id:
            await self.mark_messages_read(sender_id)
            await self.channel_layer.group_send(
                f"user_{sender_id}",
                {
                    'type': 'messages_read',
                    'reader_id': self.user.id
                }
            )

    # Message handlers
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message': event['message']
        }))

    async def typing_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        }))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read_status',
            'reader_id': event['reader_id']
        }))

    # Database operations
    @database_sync_to_async
    def save_message(self, receiver_id, content, is_image=False, image_url=None):
        return Message.objects.create(
            sender=self.user,
            receiver_id=receiver_id,
            content=content,
            is_image=is_image,
            image_url=image_url
        )

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        try:
            message = Message.objects.get(id=message_id, sender=self.user)
            message.edit_message(new_content)
            return message
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def mark_messages_read(self, sender_id):
        Message.objects.filter(
            sender_id=sender_id,
            receiver=self.user,
            is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def update_last_message(self, message):
        Contact.objects.filter(
            Q(user=message.sender, contact=message.receiver) |
            Q(user=message.receiver, contact=message.sender)
        ).update(last_message=message)

    @database_sync_to_async
    def set_user_online(self, is_online):
        UserStatus.objects.update_or_create(
            user=self.user,
            defaults={'is_online': is_online}
        )

    async def notify_status_change(self, is_online):
        # Get user's contacts
        contacts = await self.get_user_contacts()
        
        # Notify all contacts about status change
        for contact in contacts:
            await self.channel_layer.group_send(
                f"user_{contact}",
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'is_online': is_online
                }
            )

    @database_sync_to_async
    def get_user_contacts(self):
        return list(Contact.objects.filter(
            contact=self.user
        ).values_list('user_id', flat=True))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'is_online': event['is_online']
        }))