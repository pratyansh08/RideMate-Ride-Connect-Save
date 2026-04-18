from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField(max_length=15, null=True, blank=True, unique=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    rating = models.FloatField(default=0.0)
    rating_count = models.PositiveIntegerField(default=0)
    rating_sum = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username


class RegistrationOTP(models.Model):
    CHANNEL_CHOICES = (
        ("email", "Email"),
        ("phone", "Phone"),
    )

    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    target = models.CharField(max_length=255)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["channel", "target", "created_at"]),
        ]

    def __str__(self):
        return f"{self.channel}:{self.target}"
