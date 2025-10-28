from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from logs.models import ActivityLog  # Importuj swój model LogBooka
from users.serializers import UserRegisterSerializer
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    
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
        data = super().validate(attrs)
        
        # Logowanie do LogBooka
        if self.user:
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