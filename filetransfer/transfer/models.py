from django.db import models

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    is_admin = models.BooleanField(default=False)


class Directory(models.Model):
    path = models.CharField(max_length=255, unique=True)
    is_public = models.BooleanField(default=False)
    # Owner is null for admin-created directories
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True)
