from django.db import models

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.contrib.auth.models import User


class FileMetadata(models.Model):
    file_name = models.CharField(max_length=255)
    file_path = models.TextField()
    is_dir = models.BooleanField(default=False)  # True if it's a directory
    file_size = models.BigIntegerField(
        null=True, blank=True)  # Allow null for directories
    last_modified = models.DateTimeField()


# class User(AbstractUser):
#     is_admin = models.BooleanField(default=False)

class Directory(models.Model):
    # Tracks only public directories
    path = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True)
    pin = models.CharField(max_length=6, blank=True,
                           null=True)  # PIN for private access
