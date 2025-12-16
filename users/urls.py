from django.urls import path
from .views import (
    CustomTokenObtainPairView,
    ToggleStaffStatusView,
    TOTPConfirmView,
    TOTPDisableView,
    TOTPSetupView,
    TOTPStatusView,
    UserRegisterView,
    list_users,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Rejestracja nowego użytkownika
    path("register/", UserRegisterView.as_view(), name="user_register"),
    # Logowanie (uzyskanie tokena JWT)
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Lista użytkowników (Tylko Admin)
    path("list/", list_users, name="list_users"),
    # Zmiana statusu konta (Tylko Admin)
    # Przykład użycia: POST /api/users/toggle-staff/janek/
    path(
        "toggle-staff/<str:username>/",
        ToggleStaffStatusView.as_view(),
        name="toggle_staff_status",
    ),
    # 2FA (TOTP)
    path("2fa/setup/", TOTPSetupView.as_view(), name="2fa_setup"),
    path("2fa/confirm/", TOTPConfirmView.as_view(), name="2fa_confirm"),
    path("2fa/disable/", TOTPDisableView.as_view(), name="2fa_disable"),
    path("2fa/status/", TOTPStatusView.as_view(), name="2fa_status"),
]
