from django.contrib.auth import get_user_model
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail

from rest_framework.decorators import api_view
from social_django.utils import psa

from .serializers import (RegisterSerializer, CustomTokenObtainPairSerializer,
                           LogoutSerializer, PasswordResetRequestSerializer,
                           PasswordResetConfirmSerializer)

from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import ProfileSerializer, UserSerializer
from .models import Profile

User = get_user_model()

from logging import getLogger

logger = getLogger(__name__)

@api_view(["POST"])
@psa("social:complete")
def google_login(request):
    token = request.data.get("access_token")
    if not token:
        return Response({"error": "Access token is required"}, status=status.HTTP_400_BAD_REQUEST)

    user = request.backend.do_auth(token)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {"email": user.email, "username": user.username},
            }
        )
    return Response({"error": "Google authentication failed"}, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]  # Make sure this is set

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            logger.debug("done with serialization")
            print("done with serialization")
            user = serializer.save()
            logger.info("saved serialization")
            return Response({
                'message': 'Registration successful! Please login to continue.',
                'email': user.email
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        # Get or create profile if it doesn't exist
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Handle avatar separately as it's on the User model
        avatar = request.FILES.get('avatar')
        if avatar:
            instance.user.avatar = avatar
            instance.user.save()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

class UserAvatarView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        if 'avatar' not in request.FILES:
            return Response(
                {'error': 'No avatar file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)

class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                reset_url = f"http://yourfrontend.com/reset-password/{user.id}/{token}/"
                
                send_mail(
                    "Password Reset Request",
                    f"Click the link to reset your password: {reset_url}",
                    "noreply@yourdomain.com",
                    [email],
                    fail_silently=False,
                )
                return Response({"message": "Password reset email sent."}, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data["user_id"]
            token = serializer.validated_data["token"]
            new_password = serializer.validated_data["new_password"]

            try:
                user = User.objects.get(id=user_id)
                if default_token_generator.check_token(user, token):
                    user.set_password(new_password)
                    user.save()
                    return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
    
class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_204_NO_CONTENT)