from django.urls import path
from .views import UserRegisterView, CustomTokenObtainPairView, ToggleStaffStatusView, list_users
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Rejestracja nowego użytkownika
    path('register/', UserRegisterView.as_view(), name='user_register'),
    
    # Logowanie (uzyskanie tokena JWT)
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Lista użytkowników (Tylko Admin)
    path('list/', list_users, name='list_users'),
    
    # Zmiana statusu konta (Tylko Admin)
    # Przykład użycia: POST /api/users/toggle-staff/janek/
    path('toggle-staff/<str:username>/', ToggleStaffStatusView.as_view(), name='toggle_staff_status'),
]