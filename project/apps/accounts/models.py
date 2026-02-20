from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    extra = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.username}"
