from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from channels.middleware import BaseMiddleware
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = parse_qs(scope["query_string"].decode())
        token = query_string.get("token", [None])[0]

        if token:
            try:
                logger.info(f"Received WebSocket token: {token}")  # ✅ Log token for debugging

                access_token = AccessToken(token)
                user = await sync_to_async(User.objects.get)(id=access_token["user_id"])
                scope["user"] = user
                logger.info(f"User authenticated: {user.username}")
            except Exception as e:
                logger.warning(f"Invalid token: {e}")
                scope["user"] = AnonymousUser()
        else:
            logger.warning("No token found in WebSocket request")
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
