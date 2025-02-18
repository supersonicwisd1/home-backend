from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (RegisterView, CustomTokenObtainPairView, LogoutView, 
                    PasswordResetRequestView, google_login, 
                    PasswordResetConfirmView, ProfileView, UserAvatarView)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path('profile/', ProfileView.as_view(), name='profile'),
    path('avatar/', UserAvatarView.as_view(), name='avatar'),

    path("google-auth/", google_login, name="google_auth"),

    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
