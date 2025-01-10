from rest_framework import serializers
from .models import FileMetadata


class FileMetaDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileMetadata
        fields = [
            'id',
            'name',
            'relative_path',
            'absolute_path',
            'is_dir',
            'size',
            'modified',
            'created',
            'file_type',
        ]
