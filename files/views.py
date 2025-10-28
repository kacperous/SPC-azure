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

from .models import UserFile
from .serializers import UserFileSerializer
from logs.models import ActivityLog 
import mimetypes

class UserFileViewSet(viewsets.ModelViewSet):
    serializer_class = UserFileSerializer

    # --- KONTROLA DOSTĘPU I SORTOWANIE ---
    def get_queryset(self):
        user = self.request.user
        queryset = UserFile.objects.all()
        
        # Parametry z frontendu
        sort_by = self.request.query_params.get('ordering', '-uploaded_at')
        user_filter = self.request.query_params.get('owner_username', None)
        all_files_flag = self.request.query_params.get('all_files', 'false').lower() == 'true'

        if not user.is_authenticated:
            return queryset.none() 
            
        if (user.is_superuser or user.is_staff) and all_files_flag:
            # Administrator widzi WSZYSTKO (bo all_files=true)
            
            # Filtrowanie Admina po nazwie użytkownika
            if user_filter:
                try:
                    target_user = get_user_model().objects.get(username__iexact=user_filter)
                    queryset = queryset.filter(owner=target_user)
                except get_user_model().DoesNotExist:
                    return queryset.none()
        else:
            # Zwykły użytkownik widzi tylko swoje pliki
            queryset = queryset.filter(owner=user)

        # 2. SORTOWANIE
        if sort_by:
            # Poprawne sortowanie po nazwie użytkownika
            if 'owner' in sort_by:
                sort_by = sort_by.replace('owner', 'owner__username')
            
            return queryset.order_by(sort_by)

        return queryset # Domyślne sortowanie zostało już ustalone przez ordering w Meta

    def get_object(self):
        """
        Nadpisana metoda get_object() aby sprawdzić uprawnienia dostępu do pojedynczego pliku.
        Tylko właściciel pliku lub administrator może uzyskać dostęp.
        """
        obj = get_object_or_404(UserFile, pk=self.kwargs.get('pk'))
        user = self.request.user
        
        # Sprawdź czy użytkownik jest właścicielem lub adminem
        if obj.owner != user and not (user.is_staff or user.is_superuser):
            raise PermissionDenied("Nie masz uprawnień do tego pliku.")
        
        return obj

    # --- UPLOAD (Bez zmian w logice) ---
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

    @action(detail=True, methods=['get'])
    def view(self, request, pk=None):
        """
        Pozwala przeglądać plik w przeglądarce (bez wymuszania pobrania).
        Sprawdza uprawnienia - tylko właściciel lub admin może zobaczyć plik.
        Zwraca URL jako JSON.
        """
        user_file = self.get_object()  # To sprawdzi uprawnienia
        
        # Logowanie
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ActionType.FILE_VIEW,
            details=f"Wyświetlono plik: {user_file.original_filename}"
        )

        # Generujemy URL z SAS token (bez content_disposition, bo Azure Storage nie wspiera tego argumentu)
        view_url = user_file.file.url
        
        # Zwracamy URL jako JSON
        return Response({'url': view_url, 'filename': user_file.original_filename})

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Loguje pobranie i zwraca URL do pliku z SAS token.
        Zwraca URL jako JSON.
        """
        user_file = self.get_object()  # To sprawdzi uprawnienia
        
        # Logowanie
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ActionType.FILE_DOWNLOAD,
            details=f"Pobrano plik: {user_file.original_filename}"
        )
        
        # Generujemy podstawowy URL z SAS token
        download_url = user_file.file.url
        
        # Dodajemy parametr rscd (response-content-disposition) do URL, aby wymusić pobranie
        # Azure Blob Storage wspiera ten parametr w query string
        separator = '&' if '?' in download_url else '?'
        content_disposition = f'attachment; filename="{user_file.original_filename}"'
        # URL-encode content_disposition
        encoded_disposition = quote(content_disposition, safe='')
        download_url = f"{download_url}{separator}rscd={encoded_disposition}"

        # Zwracamy URL jako JSON
        return Response({'url': download_url, 'filename': user_file.original_filename})

    # --- USUWANIE (Bez zmian) ---
    def perform_destroy(self, instance):
        file_name = instance.original_filename
        instance.delete() 
        
        ActivityLog.objects.create(
            user=self.request.user,
            action=ActivityLog.ActionType.FILE_DELETE,
            details=f"Usunięto plik: {file_name}"
        )