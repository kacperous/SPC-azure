import os
import re
from datetime import datetime
from django.db import models
from django.conf import settings
import logging

# Stwórz logger
logger = logging.getLogger(__name__)


def sanitize_filename(filename):
    """
    Oczyszcza nazwę pliku dla Azure Blob Storage.
    Usuwa polskie znaki, spacje, znaki specjalne.
    """
    logger.info(f"[SANITIZE] Oryginalna nazwa: {filename}")

    # Rozdziel nazwę i rozszerzenie
    name, ext = os.path.splitext(filename)
    logger.info(f"[SANITIZE] Nazwa: {name}, Rozszerzenie: {ext}")

    # Usuń znaki nie-ASCII (polskie znaki, emoji, etc.)
    name = name.encode("ascii", "ignore").decode("ascii")
    logger.info(f"[SANITIZE] Po usunięciu non-ASCII: {name}")

    # Zamień spacje i myślniki na podkreślniki
    name = name.replace(" ", "_").replace("-", "_")
    logger.info(f"[SANITIZE] Po zamianie spacji: {name}")

    # Usuń wszystko oprócz liter, cyfr i podkreślników
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)
    logger.info(f"[SANITIZE] Po usunięciu znaków specjalnych: {name}")

    # Zamień na lowercase
    name = name.lower()
    logger.info(f"[SANITIZE] Po lowercase: {name}")

    # Jeśli nazwa jest pusta (np. był tylko emoji), użyj domyślnej
    if not name:
        name = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"[SANITIZE] Nazwa była pusta, użyto: {name}")

    # Ogranicz długość do 100 znaków
    name = name[:100]

    result = f"{name}{ext.lower()}"
    logger.info(f"[SANITIZE] FINALNA nazwa: {result}")

    return result


def user_directory_path(instance, filename):
    """
    Generuje bezpieczną ścieżkę dla uploadu.
    Format: user_uploads/user_id/sanitized_filename
    """
    logger.info(
        f"[UPLOAD_PATH] Wejście - filename: {filename}, user: {instance.owner.username}, user_id: {instance.owner.id}"
    )

    sanitized = sanitize_filename(filename)
    path = f"user_uploads/{instance.owner.id}/{sanitized}"

    logger.info(f"[UPLOAD_PATH] FINALNA ścieżka: {path}")

    return path


class UserFile(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="files"
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
        ordering = ["-uploaded_at"]  # Sortuj od najnowszych

    def create_version_snapshot(self, restored_from_version: int | None = None):
        """
        Tworzy nowy wpis wersji na podstawie aktualnego stanu pliku.
        Używane przy pierwszym uploadzie, tworzeniu nowej wersji oraz przy przywracaniu.
        """
        latest = self.versions.order_by("-version_number").first()
        next_number = (latest.version_number + 1) if latest else 1

        return UserFileVersion.objects.create(
            user_file=self,
            version_number=next_number,
            file_path=self.file.name,
            original_filename=self.original_filename,
            file_size=self.file_size,
            restored_from_version=restored_from_version,
        )

    def save(self, *args, **kwargs):
        """Automatycznie ustaw rozmiar i oryginalną nazwę przy tworzeniu"""
        logger.info(f"[MODEL SAVE] Rozpoczynam save(), pk: {self.pk}")

        if not self.pk:  # Tylko przy pierwszym zapisie
            if self.file:
                self.file_size = self.file.size
                logger.info(f"[MODEL SAVE] Ustawiono file_size: {self.file_size}")

                if not self.original_filename:
                    self.original_filename = self.file.name
                    logger.info(
                        f"[MODEL SAVE] Ustawiono original_filename: {self.original_filename}"
                    )

        logger.info("[MODEL SAVE] Wywołuję super().save()")
        super().save(*args, **kwargs)
        logger.info("[MODEL SAVE] Zakończono super().save() - plik zapisany w Azure")

    def __str__(self):
        return f"{self.original_filename} (Owner: {self.owner.username})"

    @property
    def filename(self):
        """Zwraca samą nazwę pliku, bez całej ścieżki."""
        return os.path.basename(self.file.name)


class UserFileVersion(models.Model):
    """
    Historia wersji pliku użytkownika.

    - version_number: V1, V2, ...
    - file_path: ścieżka w Azure Blob (backup konkretnego bloba)
    - created_at: data utworzenia danej wersji
    """

    user_file = models.ForeignKey(
        UserFile, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    file_path = models.CharField(max_length=512)
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    # Jeśli wersja powstała w wyniku przywrócenia starszej wersji,
    # tutaj zapisujemy numer wersji źródłowej (np. 1, gdy przywrócono V1).
    restored_from_version = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = ("user_file", "version_number")

    def __str__(self):
        return f"{self.user_file.original_filename} - V{self.version_number}"
