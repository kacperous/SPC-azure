# files/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from urllib.parse import quote
import logging
import zipfile
import os
from io import BytesIO
# Importujemy funkcję 'upload_to' z modelu, aby móc generować nowe ścieżki
from .models import UserFile, user_directory_path
from .serializers import UserFileSerializer
from logs.models import ActivityLog

logger = logging.getLogger(__name__)

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

    # --- UPLOAD (Zmodyfikowany dla rozpakowywania ZIP) ---
    def create(self, request, *args, **kwargs):
        uploaded_file = request.data.get('file')

        if not uploaded_file:
            return Response({'error': 'Brak pliku do wgrania'}, status=status.HTTP_400_BAD_REQUEST)

        # Sprawdź czy to plik ZIP
        if uploaded_file.name.lower().endswith('.zip'):
            # Rozpakuj ZIP i zapisz poszczególne pliki
            try:
                extracted_files = self._handle_zip_upload(uploaded_file)
                return Response({
                    'message': f'Pomyślnie rozpakowano {len(extracted_files)} plików z archiwum ZIP',
                    'extracted_files': extracted_files
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"[ZIP UPLOAD] Błąd podczas przetwarzania ZIP: {str(e)}")
                return Response({
                    'error': f'Błąd podczas rozpakowywania ZIP: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Zwykły upload pojedynczego pliku - użyj standardowej logiki
            return super().create(request, *args, **kwargs)

    def _handle_zip_upload(self, uploaded_file):
        """
        Rozpakowuje plik ZIP i zapisuje poszczególne pliki do S3.
        Zwraca listę informacji o rozpakowanych plikach.
        """
        extracted_files = []

        try:
            # Zapisz ZIP tymczasowo w pamięci
            zip_buffer = BytesIO(uploaded_file.read())
            zip_buffer.seek(0)

            # Otwórz ZIP
            with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                # Pobierz listę plików w ZIP-ie
                file_list = zip_ref.namelist()

                # Filtruj tylko pliki (nie katalogi)
                files_to_extract = [f for f in file_list if not f.endswith('/')]

                if not files_to_extract:
                    raise ValueError("ZIP nie zawiera żadnych plików")

                logger.info(f"[ZIP UPLOAD] Rozpakowywanie {len(files_to_extract)} plików z ZIP: {uploaded_file.name}")

                # Rozpakuj i zapisz każdy plik
                for zip_file_path in files_to_extract:
                    try:
                        # Wyciągnij zawartość pliku
                        with zip_ref.open(zip_file_path) as file_in_zip:
                            file_content = file_in_zip.read()
                            file_size = len(file_content)

                        # Przygotuj dane dla nowego pliku
                        original_filename = os.path.basename(zip_file_path)  # Tylko nazwa pliku, bez ścieżki

                        # Utwórz instancję UserFile bez zapisywania jeszcze
                        user_file = UserFile(
                            owner=self.request.user,
                            original_filename=original_filename,
                            file_size=file_size,
                            is_zip=False
                        )

                        # Wygeneruj ścieżkę dla pliku
                        file_path = user_directory_path(user_file, original_filename)

                        # Zapisz plik do storage (S3/Azure)
                        from django.core.files.base import ContentFile
                        storage = user_file.file.storage
                        storage.save(file_path, ContentFile(file_content))

                        # Ustaw ścieżkę pliku i zapisz w bazie
                        user_file.file.name = file_path
                        user_file.save()

                        logger.info(f"[ZIP UPLOAD] Zapisano plik: {original_filename}")

                        # Dodaj do listy rozpakowanych plików
                        extracted_files.append({
                            'id': user_file.id,
                            'original_filename': user_file.original_filename,
                            'file_size': user_file.file_size,
                            'uploaded_at': user_file.uploaded_at.isoformat()
                        })

                        # Loguj każdy rozpakowany plik
                        ActivityLog.objects.create(
                            user=self.request.user,
                            action=ActivityLog.ActionType.FILE_UPLOAD,
                            details=f"Rozpakowano z ZIP '{uploaded_file.name}': {original_filename}"
                        )

                    except Exception as e:
                        logger.error(f"[ZIP UPLOAD] Błąd podczas rozpakowywania pliku {zip_file_path}: {str(e)}")
                        continue

            logger.info(f"[ZIP UPLOAD] Pomyślnie rozpakowano ZIP: {uploaded_file.name}")
            return extracted_files

        except Exception as e:
            logger.error(f"[ZIP UPLOAD] Błąd podczas przetwarzania ZIP {uploaded_file.name}: {str(e)}")
            # Loguj błąd
            ActivityLog.objects.create(
                user=self.request.user,
                action=ActivityLog.ActionType.FILE_UPLOAD,
                details=f"Błąd podczas rozpakowywania ZIP '{uploaded_file.name}': {str(e)}"
            )
            raise

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
        """
        Nadpisujemy perform_destroy, aby fizycznie usunąć plik z Azure Blob Storage.
        """
        try:
            # Usuń fizyczny plik z Azure Blob
            if instance.file:
                file_path = instance.file.name
                storage = instance.file.storage
                
                logger.info(f"[DELETE] Próba usunięcia: {file_path}")
                
                if storage.exists(file_path):
                    storage.delete(file_path)
                    logger.info(f"[DELETE] Usunięto blob: {file_path}")
                else:
                    logger.warning(f"[DELETE] Blob nie istnieje: {file_path}")
            
            # Usuń wpis z bazy
            instance.delete()
            logger.info(f"[DELETE] Usunięto z bazy: {instance.original_filename}")
            
            # Log sukcesu
            ActivityLog.objects.create(
                user=self.request.user,
                action=ActivityLog.ActionType.FILE_DELETE,  # ← POPRAWKA
                details=f'Deleted file: {instance.original_filename}'  # ← POPRAWKA: original_filename
            )
            
        except Exception as e:
            logger.error(f"[DELETE] Błąd podczas usuwania: {str(e)}")
            
            # Log błędu
            ActivityLog.objects.create(
                user=self.request.user,
                action=ActivityLog.ActionType.FILE_DELETE,  # ← POPRAWKA
                details=f'Failed to delete file: {instance.original_filename}. Error: {str(e)}'  # ← POPRAWKA
            )
            
            # Usuń z bazy nawet jeśli blob nie został usunięty
            instance.delete()


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