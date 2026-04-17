from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def api_root(request):
    return Response({
        "login": "/api/login/",
        "signup": "/api/accounts/register/",
        "protected_test": "/api/accounts/protected/",
        "create_trip": "/api/trips/create/",
        "search_trips": "/api/trips/search/",
        "my_trips": "/api/trips/my/",
        "join_trip": "/api/trips/join/<trip_id>/",
        "create_review": "/api/reviews/create/",
        "chatbot": "/api/chatbot/",
        "send_message": "/api/chat/send/",
        "trip_messages": "/api/chat/trip/<trip_id>/",
    })
