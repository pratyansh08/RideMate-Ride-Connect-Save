from django.conf import settings
from django.db import models

from trips.models import Trip


class Review(models.Model):
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "reviewer"], name="unique_review_per_trip_reviewer"
            )
        ]

    def __str__(self) -> str:
        return f"Review #{self.id} for Trip {self.trip_id}"
