# files/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse
from urllib.parse import quote

# Importujemy funkcję 'upload_to' z modelu, aby móc generować nowe ścieżki
from .models import UserFile, user_directory_path 
from .serializers import UserFileSerializer
from logs.models import ActivityLog 
import mimetypes

class UserFileViewSet(viewsets.ModelViewSet):
    serializer_class = UserFileSerializer

    # --- KONTROLA DOSTĘPU I SORTOWANIE (Bez zmian, jest poprawne) ---
    def get_queryset(self):
        user = self.request.user
        queryset = UserFile.objects.all()
        
        sort_by = self.request.query_params.get('ordering', '-uploaded_at')
        user_filter = self.request.query_params.get('owner_username', None)
        all_files_flag = self.request.query_params.get('all_files', 'false').lower() == 'true'

        if not user.is_authenticated:
            return queryset.none() 
            
        if (user.is_superuser or user.is_staff) and all_files_flag:
            if user_filter:
                try:
                    target_user = get_user_model().objects.get(username__iexact=user_filter)
                    queryset = queryset.filter(owner=target_user)
                except get_user_model().DoesNotExist:
                    return queryset.none()
        else:
            queryset = queryset.filter(owner=user)

        if sort_by:
            if 'owner' in sort_by:
                sort_by = sort_by.replace('owner', 'owner__username')
            return queryset.order_by(sort_by)
        return queryset

    def get_object(self):
        obj = get_object_or_404(UserFile, pk=self.kwargs.get('pk'))
        user = self.request.user
        
        if obj.owner != user and not (user.is_staff or user.is_superuser):
            raise PermissionDenied("Nie masz uprawnień do tego pliku.")
        return obj

    # --- UPLOAD (Bez zmian) ---
    def perform_create(self, serializer):
        uploaded_file = self.request.data.get('file')
        
        if not uploaded_file:
            return
        
        user_file = serializer.save(
            owner=self.request.user,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            is_zip=uploaded_file.name.endswith('.zip')
        )
        
        ActivityLog.objects.create(
            user=self.request.user,
            action=ActivityLog.ActionType.FILE_UPLOAD,
            details=f"Wgrano plik: {user_file.original_filename}"
        )

    # --- AKCJE (Bez zmian) ---
    @action(detail=True, methods=['get'])
    def view(self, request, pk=None):
        user_file = self.get_object()
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ActionType.FILE_VIEW,
            details=f"Wyświetlono plik: {user_file.original_filename}"
        )
        view_url = user_file.file.url
        return Response({'url': view_url, 'filename': user_file.original_filename})


    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """ Zwraca URL wymuszający pobranie (wymaga poprawnego zegara) """
        user_file = self.get_object()
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ActionType.FILE_DOWNLOAD,
            details=f"Pobrano plik: {user_file.original_filename}"
        )
        
        # 1. Pobieramy bazowy URL z poprawnym podpisem SAS
        # (Zakładając, że zegar jest naprawiony)
        base_url = user_file.file.url
        
        # 2. Przygotowujemy parametr 'rscd', który Azure rozumie
        content_disposition = f'attachment; filename="{user_file.original_filename}"'
        encoded_disposition = quote(content_disposition, safe='')
        separator = '&' if '?' in base_url else '?'
        
        # 3. Dodajemy parametr DO gotowego URL. To jest wspierane przez Azure.
        final_url = f"{base_url}{separator}rscd={encoded_disposition}"

        return Response({'url': final_url, 'filename': user_file.original_filename})    

    def perform_destroy(self, instance):
        file_name = instance.original_filename
        storage = instance.file.storage  # Pobieramy backend (np. AzureStorage)
        file_path = instance.file.name   # Pobieramy ścieżkę (np. 'user_uploads/8/komendki.txt')

        try:
            # Krok 1: Jawnie usuń plik z Azure Blob Storage
            # To jest najważniejsza zmiana!
            storage.delete(file_path)
            
            # Krok 2: Jeśli powyższe się udało, usuń rekord z bazy danych
            instance.delete() 
            
            # Krok 3: Logowanie sukcesu
            ActivityLog.objects.create(
                user=self.request.user,
                action=ActivityLog.ActionType.FILE_DELETE,
                details=f"Usunięto plik: {file_name} (z DB i Azure)"
            )
            
        except Exception as e:
            # Krok 4: Jeśli usuwanie z Azure się nie udało, NIE usuwaj z DB
            # i zwróć błąd 500
            ActivityLog.objects.create(
                user=self.request.user,
                action=ActivityLog.ActionType.ERROR, # Załóżmy, że masz taki typ logu
                details=f"Błąd podczas usuwania pliku '{file_name}': {str(e)}"
            )
            # Zgłoś wyjątek, aby DRF zwrócił błąd 500 zamiast 204
            raise PermissionDenied(f"Nie można usunąć pliku z Azure. Błąd: {str(e)}")

    # --- NOWA AKCJA: ZMIANA NAZWY ---
    @action(detail=True, methods=['patch'], url_path='rename')
    def rename(self, request, pk=None):
        """
        Zmienia nazwę pliku (zarówno w bazie danych, jak i w Blob Storage).
        Oczekuje {'new_filename': 'nowa_nazwa.pdf'} w ciele żądania.
        """
        user_file = self.get_object() # Sprawdza uprawnienia (właściciel lub admin)
        new_filename = request.data.get('new_filename')

        if not new_filename:
            return Response(
                {'error': 'Brak wymaganego pola "new_filename".'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_original_name = user_file.original_filename
        if new_filename == old_original_name:
             return Response(
                {'error': 'Nowa nazwa jest taka sama jak stara.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        storage = user_file.file.storage
        old_name_path = user_file.file.name
        
        # Generujemy nową ścieżkę używając tej samej funkcji 'upload_to' z modelu
        new_name_path = user_directory_path(user_file, new_filename)

        try:
            # Krok 1: Kopia w Blob Storage
            # Otwieramy stary plik i zapisujemy go pod nową ścieżką
            with storage.open(old_name_path, 'rb') as old_file_content:
                storage.save(new_name_path, old_file_content)
            
            # Krok 2: Aktualizacja Bazy Danych
            user_file.original_filename = new_filename
            user_file.file.name = new_name_path # Kluczowe: aktualizujemy ścieżkę w FileField
            user_file.save()

            # Krok 3: Usunięcie starego pliku (dopiero po sukcesie zapisu w DB)
            storage.delete(old_name_path)

            # Krok 4: Logowanie
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.ActionType.FILE_RENAME,
                details=f"Zmieniono nazwę pliku z '{old_original_name}' na '{new_filename}'"
            )

            # Krok 5: Zwróć zaktualizowany obiekt
            serializer = self.get_serializer(user_file)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            # Obsługa błędu: Jeśli coś pójdzie nie tak (np. krok 2 lub 3 się nie uda),
            # możemy mieć zduplikowany plik (nowy) bez wpisu w DB.
            # W ramach bezpieczeństwa usuwamy nowy plik, jeśli już powstał.
            try:
                if storage.exists(new_name_path):
                     storage.delete(new_name_path)
            except Exception as cleanup_e:
                # Logujemy błąd czyszczenia, ale główny błąd jest ważniejszy
                print(f"Błąd podczas czyszczenia po nieudanej zmianie nazwy: {cleanup_e}")

            return Response(
                {'error': f'Nie udało się zmienić nazwy pliku. Błąd: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_SERVICE_ERROR
            )