# logs/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser # Klasa uprawnień dla admina
from .models import ActivityLog
from .serializers import ActivityLogSerializer

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API do przeglądania logów aktywności.
    Umożliwia dostęp tylko administratorom i sortowanie.
    """
    serializer_class = ActivityLogSerializer
    
    # Użyjemy domyślnej klasy uprawnień Django REST Framework:
    # Tylko użytkownicy z is_staff=True mogą to zobaczyć.
    # Jeśli chcesz, aby tylko Superuser widział, użyj IsAuthenticated
    # i dodaj ręczną weryfikację w get_queryset.
    permission_classes = [IsAdminUser] 
    
    # Baza dla wszystkich logów
    queryset = ActivityLog.objects.all()

    # Logika sortowania i filtrowania jest realizowana w get_queryset:
    def get_queryset(self):
        queryset = ActivityLog.objects.all()
        
        # --- FILTROWANIE PO UŻYTKOWNIKU ---
        # Sprawdź, czy w URL jest parametr 'user' (np. /api/logs/?user=admin)
        username = self.request.query_params.get('user', None)
        if username is not None:
            queryset = queryset.filter(user__username__iexact=username)
        
        # --- SORTOWANIE ---
        # Sortowanie domyślne to '-timestamp' (najnowsze na górze)
        sort_by = self.request.query_params.get('sort', '-timestamp')
        
        # Umożliwienie sortowania po nazwie użytkownika
        if sort_by == 'username':
            # Używamy user__username, aby sortować po polu z modelu User
            return queryset.order_by('user__username') 
        elif sort_by == '-username':
            return queryset.order_by('-user__username')
            
        return queryset.order_by(sort_by)