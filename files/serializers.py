from rest_framework import serializers
from .models import UserFile

class UserFileSerializer(serializers.ModelSerializer):
    # To pole doda nazwę właściciela (np. "admin") do JSONa
    owner = serializers.ReadOnlyField(source='owner.username')
    # Usunięto file_url dla bezpieczeństwa - dostęp do plików tylko przez endpointy view/download

    class Meta:
        model = UserFile
        # Pola, które "tłumacz" ma pokazywać w JSONie
        # 'file' jest potrzebne do uploadu (POST)
        fields = ['id', 'owner', 'original_filename', 'uploaded_at', 'file_size', 'file', 'is_zip']
        
        # Tych pól nie da się edytować przy wysyłaniu (ustawią się same)
        read_only_fields = ['owner', 'uploaded_at', 'file_size', 'is_zip','original_filename']
        
        # To sprawia, że pole 'file' jest wymagane tylko przy tworzeniu (POST)
        # ale nie jest pokazywane przy listowaniu (GET)
        extra_kwargs = {
            'file': {'write_only': True}
        }