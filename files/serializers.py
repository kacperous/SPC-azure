from rest_framework import serializers
from .models import UserFile


class UserFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = UserFile
        fields = ['id', 'file', 'file_url', 'original_filename', 'file_size', 'uploaded_at', 'is_zip', 'owner', 'owner_username']  # ← DODANE: 'file'
        read_only_fields = ['id', 'uploaded_at', 'owner', 'file_url', 'owner_username', 'original_filename', 'file_size']
    
    def get_file_url(self, obj):
        """Zwróć pełny URL do pliku w Azure Blob Storage"""
        if obj.file:
            try:
                return obj.file.url
            except Exception as e:
                return None
        return None
