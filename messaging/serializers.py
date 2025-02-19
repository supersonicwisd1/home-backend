# messaging/serializers.py
from rest_framework import serializers
from .models import Message, Contact, UserStatus
from accounts.serializers import UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 
            'content', 
            'sender', 
            'receiver', 
            'created_at',
            'is_read', 
            'is_image', 
            'image_url',
            'sender_name',
            'sender_avatar'
        ]
        read_only_fields = ['id', 'created_at', 'sender', 'sender_name', 'sender_avatar']

    def get_sender_avatar(self, obj):
        return obj.sender.avatar.url if hasattr(obj.sender, 'avatar') and obj.sender.avatar else None

    def to_representation(self, instance):
        """Add extra logging for debugging"""
        data = super().to_representation(instance)
        print(f"Serializing message {instance.id}: {data}")
        return data

    def validate_receiver(self, value):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")

        try:
            contact = Contact.objects.get(
                user=request.user,
                contact_id=value
            )
            return contact.contact
        except Contact.DoesNotExist:
            raise serializers.ValidationError(
                f"No contact found between {request.user.id} and {value}"
            )

    def validate(self, data):
        if not data.get('content', '').strip():
            raise serializers.ValidationError({
                'content': 'Content cannot be empty'
            })
        print(f"Validated data: {data}")  # Debug log
        return data
    
class ContactSerializer(serializers.ModelSerializer):
    contact_details = UserSerializer(source='contact', read_only=True)
    last_message = serializers.SerializerMethodField()
    online = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'id', 
            'contact_details', 
            'last_message', 
            'online',
            'unread_count', 
            'created_at'
        ]

    def get_last_message(self, obj):
        if obj.last_message:
            return {
                'id': obj.last_message.id,
                'content': obj.last_message.content,
                'timestamp': obj.last_message.created_at.strftime("%I:%M%p"),
                'is_read': obj.last_message.is_read,
                'is_image': obj.last_message.is_image,
                'image_url': obj.last_message.image_url if obj.last_message.is_image else None
            }
        return None

    def get_online(self, obj):
        try:
            return obj.contact.userstatus.is_online
        except UserStatus.DoesNotExist:
            return False

    def get_unread_count(self, obj):
        return Message.objects.filter(
            sender=obj.contact,
            receiver=obj.user,
            is_read=False
        ).count()

class MessageEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content']

    def validate(self, attrs):
        if not attrs.get('content'):
            raise serializers.ValidationError("Content cannot be empty")
        return attrs

class ContactInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(required=False)

    def validate_email(self, value):
        User = get_user_model()
        try:
            user = User.objects.get(email=value)
            # Check if contact already exists
            if Contact.objects.filter(
                user=self.context['request'].user,
                contact=user
            ).exists():
                raise serializers.ValidationError("Contact already exists")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist")
        

class UserStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStatus
        fields = ['user', 'is_online']