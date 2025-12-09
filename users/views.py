import base64
import io
import urllib.parse

import qrcode
from django.conf import settings
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_totp.models import TOTPDevice
from logs.models import ActivityLog  # Importuj swój model LogBooka
from rest_framework import generics, permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from users.serializers import UserRegisterSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    otp_token = serializers.CharField(
        write_only=True, required=False, allow_blank=True, help_text="6-cyfrowy kod TOTP"
    )
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # !!! TE POLA SĄ DODAWANE DO TOKENA I NAPRAWIAJĄ BŁĄD 'UNDEFINED' !!!
        token['username'] = user.username
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        # Dodajemy też ID, choć JS go na razie nie używa
        token['user_id'] = user.id

        return token

    def validate(self, attrs):
        otp_token = attrs.get("otp_token")
        data = super().validate(attrs)
        
        # Jeżeli użytkownik ma aktywne 2FA (TOTP), wymagamy poprawnego kodu
        devices = TOTPDevice.objects.filter(user=self.user, confirmed=True)
        if devices.exists():
            otp_raw = (otp_token or "").strip().replace(" ", "")
            if not otp_raw:
                raise serializers.ValidationError({"otp_token": "Wymagany jest kod 2FA (TOTP)."})
            if not otp_raw.isdigit():
                raise serializers.ValidationError({"otp_token": "Kod 2FA musi zawierać tylko cyfry."})

            otp_is_valid = any(device.verify_token(otp_raw) for device in devices)
            if not otp_is_valid:
                raise serializers.ValidationError({"otp_token": "Nieprawidłowy kod 2FA."})

        # Logowanie do LogBooka
        ActivityLog.objects.create(
            user=self.user,
            action=ActivityLog.ActionType.USER_LOGIN,
            details=f"Użytkownik {self.user.username} zalogował się pomyślnie."
        )
        return data

# --- WIDOKI ---

class CustomTokenObtainPairView(TokenObtainPairView):
    # Używamy naszego ulepszonego serializera
    serializer_class = CustomTokenObtainPairSerializer

class UserRegisterView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny] 
    # Zakładam, że UserRegisterSerializer jest w users/serializers.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """
    Zwraca listę wszystkich użytkowników (tylko dla adminów).
    Zwykli użytkownicy otrzymają pustą listę.
    """
    User = get_user_model()
    
    # Tylko administratorzy mogą widzieć listę użytkowników
    if not (request.user.is_staff or request.user.is_superuser):
        return Response([], status=status.HTTP_200_OK)
    
    users = User.objects.all().order_by('username')
    user_list = [{'username': user.username, 'id': user.id} for user in users]
    
    return Response(user_list, status=status.HTTP_200_OK)

class ToggleStaffStatusView(APIView):
    
    def post(self, request, username, format=None):
        """
        Zmienia status is_staff dla danego użytkownika (nadaje/odbiera uprawnienia admina).
        """
        User = get_user_model()
        try:
            user_to_update = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": f"Użytkownik '{username}' nie znaleziony."}, status=status.HTTP_404_NOT_FOUND)
            
        # Zmień status na przeciwny (jeśli True, to False i odwrotnie)
        user_to_update.is_staff = not user_to_update.is_staff
        # Upewnij się, że is_superuser pozostaje False, chyba że to jest superuser
        if not user_to_update.is_superuser:
            user_to_update.is_superuser = False
            
        user_to_update.save()
        
        new_status = "Administratorem" if user_to_update.is_staff else "Zwykłym użytkownikiem"

        # Zapisz log (jeśli chcesz mieć logi na poziomie LogBooka)
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ActionType.USER_STATUS_CHANGE, # Musisz dodać ten typ do logs/models.py!
            details=f"Zmieniono status użytkownika {username} na: {new_status}."
        )

        return Response({"message": f"Status użytkownika '{username}' zmieniony na: {new_status}"}, status=status.HTTP_200_OK)


class TOTPSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Tworzy nowe urządzenie TOTP (niezatwierdzone) i zwraca dane do skanowania.
        """
        user = request.user

        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            return Response(
                {"detail": "2FA jest już włączone dla tego użytkownika."},
                status=status.HTTP_200_OK,
            )

        # Czyścimy poprzednie niepotwierdzone urządzenia, aby uniknąć starych sekretów
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()

        device = TOTPDevice.objects.create(
            user=user,
            name="TOTP",
            confirmed=False,
        )

        issuer = getattr(settings, "OTP_TOTP_ISSUER", "SPC")
        secret = base64.b32encode(bytes.fromhex(device.key)).decode("utf-8").replace("=", "")
        label = f"{issuer}:{user.get_username()}"
        otp_uri = (
            f"otpauth://totp/{urllib.parse.quote(label)}"
            f"?secret={secret}&issuer={urllib.parse.quote(issuer)}"
            f"&digits={device.digits}&period={device.step}"
        )

        # Generujemy bazowy QR w base64, by klient mógł go wyświetlić bezpośrednio
        qr_image = qrcode.make(otp_uri)
        buffer = io.BytesIO()
        qr_image.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return Response(
            {
                "otpauth_url": otp_uri,
                "secret": secret,
                "qr_code_base64": qr_base64,
            },
            status=status.HTTP_201_CREATED,
        )


class TOTPConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Potwierdza kodem TOTP i aktywuje urządzenie.
        """
        otp_token = request.data.get("otp_token")
        if not otp_token:
            return Response(
                {"otp_token": "Podaj kod z aplikacji (6 cyfr)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device = (
            TOTPDevice.objects.filter(user=request.user, confirmed=False)
            .order_by("-id")
            .first()
        )

        if not device:
            return Response(
                {"detail": "Brak oczekującego urządzenia TOTP. Utwórz je najpierw."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not device.verify_token(otp_token):
            return Response(
                {"otp_token": "Kod nieprawidłowy lub wygasł."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.confirmed = True
        device.save(update_fields=["confirmed"])

        return Response({"detail": "2FA (TOTP) zostało włączone."}, status=status.HTTP_200_OK)


class TOTPDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Wyłącza i usuwa wszystkie urządzenia TOTP użytkownika.
        """
        TOTPDevice.objects.filter(user=request.user).delete()
        return Response({"detail": "2FA zostało wyłączone."}, status=status.HTTP_200_OK)


class TOTPStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        enabled = TOTPDevice.objects.filter(user=request.user, confirmed=True).exists()
        return Response({"enabled": enabled}, status=status.HTTP_200_OK)