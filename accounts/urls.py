from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import CurrentUserView, LoginView, RegisterView


urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('me/', CurrentUserView.as_view(), name='auth-me'),
]
