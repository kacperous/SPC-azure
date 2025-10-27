# files/views.py

from rest_framework import viewsets
from .models import UserFile
from .serializers import UserFileSerializer
from logs.models import ActivityLog # Do logowania działań
from rest_framework.decorators import action
from django.shortcuts import redirect

class UserFileViewSet(viewsets.ModelViewSet):
    """
    To jest magiczny "Kierownik", który robi WSZYSTKO:
    - GET (listuje pliki)
    - POST (dodaje plik)
    - DELETE (usuwa plik)
    """
    serializer_class = UserFileSerializer

    # TA LINIA TO BEZPIECZEŃSTWO:
    # Użytkownik widzi TYLKO swoje pliki.
    def get_queryset(self):
        return UserFile.objects.filter(owner=self.request.user).order_by('-uploaded_at')

    # To jest Twoja "logika dodawania" (wywoływana przy POST)
    def perform_create(self, serializer):
        uploaded_file = self.request.data.get('file')
        
        if not uploaded_file:
            # Nie powinno się zdarzyć, jeśli serializer jest dobrze ustawiony
            return
        
        # Zapisz plik, ustawiając właściciela i metadane
        user_file = serializer.save(
            owner=self.request.user,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            is_zip=uploaded_file.name.endswith('.zip')
        )
        
        # Zapisz log w LogBooku
        ActivityLog.objects.create(
            user=self.request.user,
            action=ActivityLog.ActionType.FILE_UPLOAD,
            details=f"Wgrano plik: {user_file.original_filename}"
        )

    # To jest Twoja "logika usuwania" (wywoływana przy DELETE)
    def perform_destroy(self, instance):
        # Zapisujemy nazwę pliku, zanim go usuniemy
        file_name = instance.original_filename
        
        # Ta linia usuwa wpis z bazy (PostgreSQL)
        # i automatycznie usuwa plik fizyczny (z dysku lokalnie lub z Azure)
        instance.delete() 
        
        # Zapisz log w LogBooku
        ActivityLog.objects.create(
            user=self.request.user,
            action=ActivityLog.ActionType.FILE_DELETE,
            details=f"Usunięto plik: {file_name}"
        )
        
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Akcja logująca pobieranie i przekierowująca użytkownika
        do bezpiecznego linku SAS (Shared Access Signature) w Azure.
        """
        user_file = self.get_object() 
        
        # 1. Zapisz log do LogBooka (to robimy ZAWSZE na serwerze)
        ActivityLog.objects.create(
            user=self.request.user,
            action=ActivityLog.ActionType.FILE_DOWNLOAD,
            details=f"Wymuszone pobranie pliku: {user_file.original_filename}"
        )

        # 2. Wygeneruj bezpieczny URL z nagłówkiem 'attachment'
        # To jest kluczowe: to "zmusza" przeglądarkę do POBRANIA,
        # a nie tylko podglądu, nawet jeśli to PDF.
        # Wymaga to użycia metody storage.url()
        download_url = user_file.file.storage.url(
            user_file.file.name, 
            # Dodaj ten nagłówek Content-Disposition do URL
            # To jest "bilet", który wymusza pobranie
            params={'response-content-disposition': f'attachment; filename="{user_file.original_filename}"'}
        )

        # 3. Przekieruj użytkownika do bezpiecznego, tymczasowego linku w Azure
        return redirect(download_url)