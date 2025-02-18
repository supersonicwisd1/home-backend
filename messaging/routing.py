from django.urls import re_path
from .consumers import ChatConsumer
import logging

logger = logging.getLogger(__name__)

logger.info("Registering WebSocket URL patterns")

websocket_urlpatterns = [
    re_path(r'^ws/chat/$', ChatConsumer.as_asgi()),
]
logger.info(f"WebSocket patterns registered: {websocket_urlpatterns}")