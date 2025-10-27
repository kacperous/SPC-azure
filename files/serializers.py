from rest_framework import serializers
from .models import UserFile

class UserFileSerializer(serializers.ModelSerializer):
    # To pole doda nazwę właściciela (np. "admin") do JSONa
    owner = serializers.ReadOnlyField(source='owner.username')
    file_url = serializers.CharField(source='file.url', read_only=True)

    class Meta:
        model = UserFile
        # Pola, które "tłumacz" ma pokazywać w JSONie
        # 'file' jest potrzebne do uploadu (POST)
        fields = ['id', 'owner', 'original_filename', 'uploaded_at', 'file_size', 'file', 'is_zip','file_url']
        
        # Tych pól nie da się edytować przy wysyłaniu (ustawią się same)
        read_only_fields = ['owner', 'uploaded_at', 'file_size', 'is_zip','original_filename','file_url']
        
        # To sprawia, że pole 'file' jest wymagane tylko przy tworzeniu (POST)
        # ale nie jest pokazywane przy listowaniu (GET)
        extra_kwargs = {
            'file': {'write_only': True}
        }