from django.urls import path
from . import views

urlpatterns = [
    # API endpoints
    path('api/register/', views.api_register, name='api_register'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('api/check-auth/', views.api_check_auth, name='api_check_auth'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('api/verify-email/', views.api_verify_email, name='api_verify_email'),
] 