from django.db import models
from django.conf import settings

class ActivityLog(models.Model):
    """
    Model LogBooka - rejestruje kluczowe działania użytkowników.
    """

    class ActionType(models.TextChoices):
        USER_LOGIN = 'LOGIN', 'Logowanie'
        USER_LOGOUT = 'LOGOUT', 'Wylogowanie'
        FILE_UPLOAD = 'UPLOAD', 'Przesłanie pliku'
        FILE_VIEW = 'VIEW', 'Podgląd pliku'
        FILE_DOWNLOAD = 'DOWNLOAD', 'Pobranie pliku'
        FILE_DELETE = 'DELETE', 'Usunięcie pliku'
        USER_STATUS_CHANGE = 'STATUS_CHANGE', 'Zmiana statusu użytkownika'
        
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, 
        related_name='activity_logs'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    action = models.CharField(
        max_length=20,
        choices=ActionType.choices
    )
    
    # Dodatkowe szczegóły, np. nazwa pliku, IP itp.
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp'] # Sortuj od najnowszych

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.timestamp}] {user_str} - {self.get_action_display()}"