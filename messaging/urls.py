# messaging/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MessageViewSet, ContactViewSet, UserStatusViewSet
from .routing import websocket_urlpatterns

router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'status', UserStatusViewSet, basename='status')

urlpatterns = [
    path('', include(router.urls)),
]