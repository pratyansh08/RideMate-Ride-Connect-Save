from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.models import Booking, Trip

from .models import Message
from .serializers import MessageSerializer


def _is_trip_member(user, trip_id):
    trip = Trip.objects.filter(id=trip_id).first()
    if not trip:
        return None, False
    if trip.driver_id == user.id:
        return trip, True
    if Booking.objects.filter(trip_id=trip_id, rider_id=user.id).exists():
        return trip, True
    return trip, False


class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        trip_id = request.data.get("trip")
        trip, is_member = _is_trip_member(request.user, trip_id)
        if not trip:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)
        if not is_member:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        serializer = MessageSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            message = serializer.save(sender=request.user)
            return Response(
                MessageSerializer(message, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class TripMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        trip, is_member = _is_trip_member(request.user, trip_id)
        if not trip:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)
        if not is_member:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        try:
            limit = int(request.query_params.get("limit", 50))
            offset = int(request.query_params.get("offset", 0))
        except ValueError:
            return Response({"detail": "Invalid pagination parameters."}, status=status.HTTP_400_BAD_REQUEST)

        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        qs = Message.objects.filter(trip_id=trip_id).order_by("created_at")
        messages = qs[offset : offset + limit]
        serializer = MessageSerializer(messages, many=True, context={"request": request})
        return Response(serializer.data)
