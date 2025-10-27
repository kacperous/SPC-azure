from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from logs.models import ActivityLog  # Importuj swój model LogBooka

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer, który przy pomyślnym logowaniu
    dodaje wpis do ActivityLog.
    """
    def validate(self, attrs):
        # Uruchom domyślną walidację (sprawdza login i hasło)
        data = super().validate(attrs)
        
        # 'self.user' jest automatycznie ustawiany przez bibliotekę
        # po poprawnym zalogowaniu
        if self.user:
            try:
                ActivityLog.objects.create(
                    user=self.user,
                    action=ActivityLog.ActionType.USER_LOGIN,
                    details=f"Użytkownik {self.user.username} zalogował się."
                )
            except Exception as e:
                # Logowanie do konsoli serwera, jeśli zapis do LogBooka się nie uda
                print(f"Błąd zapisu do LogBooka podczas logowania: {e}")

        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Używa naszego customowego serializera do logowania.
    """
    serializer_class = CustomTokenObtainPairSerializer