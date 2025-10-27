# files/views.py

from rest_framework import viewsets
from .models import UserFile
from .serializers import UserFileSerializer
from logs.models import ActivityLog # Do logowania działań
from rest_framework.decorators import action
from django.http import FileResponse
import mimetypes

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
        Specjalna akcja do wymuszonego pobierania pliku
        i logowania tego faktu.
        """
        # 1. Pobierz obiekt pliku (np. /api/files/5/download/)
        user_file = self.get_object() 
        
        # 2. Zaloguj akcję do LogBooka
        ActivityLog.objects.create(
            user=self.request.user,
            action=ActivityLog.ActionType.FILE_DOWNLOAD,
            details=f"Pobrano plik: {user_file.original_filename}"
        )

        # 3. Otwórz plik (z dysku lokalnego lub Azure)
        # 'rb' = read binary (czytaj jako plik binarny)
        file_handle = user_file.file.open('rb')
        
        # 4. Zgadnij typ pliku (np. 'application/pdf')
        mime_type, _ = mimetypes.guess_type(user_file.original_filename)

        # 5. Stwórz odpowiedź, która zmusi do pobrania
        response = FileResponse(file_handle, content_type=mime_type)
        response['Content-Length'] = user_file.file_size
        
        # To jest kluczowy nagłówek, który mówi "pobierz" zamiast "wyświetl"
        response['Content-Disposition'] = f'attachment; filename="{user_file.original_filename}"'
        
        return response