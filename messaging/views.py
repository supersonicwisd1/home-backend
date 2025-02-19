# messaging/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, F, Max
from django.contrib.auth import get_user_model
from .models import Message, Contact, UserStatus
from .serializers import (
    MessageSerializer,
    ContactSerializer,
    UserStatusSerializer,
    ContactInviteSerializer
)

User = get_user_model()

from logging import getLogger

logger = getLogger(__name__)

class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or user.is_anonymous:
            raise PermissionDenied("Authentication required")
        return Contact.objects.filter(user=user)\
            .select_related('contact', 'contact__userstatus', 'last_message')\
            .annotate(
                last_message_time=Max('last_message__created_at')
            ).order_by('-last_message_time')

    @action(detail=False, methods=['post'])
    def invite(self, request):
        serializer = ContactInviteSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                contact_user = User.objects.get(email=email)
                # Create two-way contact
                contact = Contact.objects.create(
                    user=request.user,
                    contact=contact_user
                )
                Contact.objects.create(
                    user=contact_user,
                    contact=request.user
                )
                return Response(
                    ContactSerializer(contact).data,
                    status=status.HTTP_201_CREATED
                )
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        try:
            contact = self.get_object()
            Message.objects.filter(
                sender=contact.contact,
                receiver=request.user,
                is_read=False
            ).update(is_read=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Contact.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        contact_id = self.request.query_params.get('contact')
        
        print(f"📌 DEBUG: Extracted contact_id: {contact_id}")

        if not contact_id:
            print("❌ No contact_id provided, returning empty queryset.")
            return Message.objects.none()  # Return empty queryset

        try:
            contact = Contact.objects.get(
                user=self.request.user,
                contact_id=contact_id
            )
            print(f"✅ Found contact: {contact}")
        except Contact.DoesNotExist:
            print(f"❌ Contact not found for user {self.request.user.id} and contact_id {contact_id}")
            return Message.objects.none()

        # Fetch messages between sender and receiver
        queryset = Message.objects.filter(
            Q(sender=self.request.user, receiver_id=contact_id) |
            Q(sender_id=contact_id, receiver=self.request.user)
        ).select_related('sender').order_by('created_at')

        print(f"✅ Found {queryset.count()} messages for conversation with {contact_id}")

        return queryset


    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Add debug information
        print(f"Request user: {request.user.id}")
        print(f"Query params: {request.query_params}")
        print(f"Message count: {queryset.count()}")
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        print(f"Created message: {message.id} from {message.sender} to {message.receiver}")  # Debug log
        
        # Update last message for both contacts
        contacts_updated = Contact.objects.filter(
            Q(user=self.request.user, contact=message.receiver) |
            Q(user=message.receiver, contact=self.request.user)
        ).update(last_message=message)
        
        print(f"Updated {contacts_updated} contacts with new last message")  # Debug log
        
        return message

class UserStatusViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserStatusSerializer 

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        status, created = UserStatus.objects.get_or_create(
            user=request.user,
            defaults={'is_online': True}
        )
        if not created:
            status.is_online = not status.is_online
            status.save()
        
        serializer = self.get_serializer(status) 
        return Response(serializer.data)