from rest_framework import serializers
from .models import UserFile, UserFileVersion


class UserFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    latest_version = serializers.SerializerMethodField()
    versions_count = serializers.SerializerMethodField()

    class Meta:
        model = UserFile
        fields = [
            "id",
            "file",
            "file_url",
            "original_filename",
            "file_size",
            "uploaded_at",
            "is_zip",
            "owner",
            "owner_username",
            "latest_version",
            "versions_count",
        ]
        read_only_fields = [
            "id",
            "uploaded_at",
            "owner",
            "file_url",
            "owner_username",
            "original_filename",
            "file_size",
            "latest_version",
            "versions_count",
        ]

    def get_file_url(self, obj):
        """Zwróć pełny URL do pliku w Azure Blob Storage"""
        if obj.file:
            try:
                return obj.file.url
            except Exception:
                return None
        return None

    def get_latest_version(self, obj):
        latest = obj.versions.order_by("-version_number").first()
        if latest:
            return latest.version_number
        # Jeśli z jakiegoś powodu nie ma wpisu w historii, traktujemy to jako V1
        return 1

    def get_versions_count(self, obj):
        return obj.versions.count()


class UserFileVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFileVersion
        fields = [
            "id",
            "version_number",
            "original_filename",
            "file_size",
            "created_at",
            "restored_from_version",
        ]
