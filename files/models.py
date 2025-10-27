from django.db import models
from django.conf import settings  
import os

def user_directory_path(instance, filename):
    return f'user_uploads/{instance.owner.id}/{filename}'

class UserFile(models.Model):
 
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='files'
    )

    file = models.FileField(upload_to=user_directory_path)
    
    # --- Pola dla "Przeglądania listy plików" ---
    
    # Oryginalna nazwa pliku (np. "raport.pdf")
    original_filename = models.CharField(max_length=255)
    
    # Data wgrania (ustawi się automatycznie)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Rozmiar pliku w bajtach
    file_size = models.BigIntegerField()

    # Flaga dla "Wysyłanie kilku plików na raz (np. ZIP)"
    is_zip = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at'] # Sortuj od najnowszych

    def __str__(self):
        return f"{self.original_filename} (Owner: {self.owner.username})"
    
    @property
    def filename(self):
        """ Zwraca samą nazwę pliku, bez całej ścieżki. """
        return os.path.basename(self.file.name)