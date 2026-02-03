from django.conf import settings
from django.db import models

from trips.models import Trip


class Message(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages"
    )
    message = models.TextField(blank=True)
    attachment = models.FileField(upload_to="chat_attachments/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Message #{self.id} for Trip {self.trip_id}"
