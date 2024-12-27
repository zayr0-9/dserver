from django.db import models

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta


class FileSearchMetadata(models.Model):
    file_name = models.CharField(max_length=255)
    file_path = models.TextField()
    is_dir = models.BooleanField(default=False)  # True if it's a directory
    file_size = models.BigIntegerField(
        null=True, blank=True)  # Allow null for directories
    last_modified = models.DateTimeField()


class Directory(models.Model):
    # Tracks only public directories
    path = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True)
    pin = models.CharField(max_length=6, blank=True,
                           null=True)  # PIN for private access
    allow_sub_dir = models.BooleanField(default=False)


class Movie(models.Model):
    file_name = models.CharField(max_length=255)
    movie_name = models.CharField(max_length=255)
    file_path = models.TextField()  # Path to the video file on the server
    length = models.DurationField()  # Store the video length in HH:MM:SS format
    added_to_favorites = models.BooleanField(default=False)
    thumbnail = models.ImageField(
        upload_to='thumbnails/', null=True, blank=True)

    # Last watched position in seconds
    last_position = models.DurationField(default=timedelta(seconds=0))
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True)


class FileTypeCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    extensions = models.TextField(
        help_text="Comma-separated list of file extensions, e.g., .jpg,.png,.gif"
    )

    def get_extensions_list(self):
        return [ext.strip().lower() for ext in self.extensions.split(',')]

    def __str__(self):
        return self.name


class FileLock(models.Model):
    file_path = models.CharField(max_length=1024, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now=True)


class FileMetadata(models.Model):
    name = models.CharField(max_length=255)
    relative_path = models.CharField(max_length=1024, unique=True)
    absolute_path = models.CharField(max_length=2048, unique=True)
    is_dir = models.BooleanField(default=False)
    size = models.BigIntegerField(null=True, blank=True)
    modified = models.DateTimeField()
    created = models.DateTimeField()
    file_type = models.ForeignKey(
        FileTypeCategory, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.relative_path


def __str__(self):
    return self.movie_name
