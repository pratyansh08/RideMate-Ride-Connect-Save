from django.contrib import admin

from .models import Booking, Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source",
        "destination",
        "date",
        "time",
        "available_seats",
        "price",
        "driver",
        "is_completed",
    )
    list_filter = ("date", "source", "destination")
    search_fields = ("source", "destination", "driver__username", "driver__email")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "rider", "seats", "created_at")
    list_filter = ("created_at",)
    search_fields = ("rider__username", "rider__email")
