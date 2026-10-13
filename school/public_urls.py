from django.http import JsonResponse
from django.urls import path


def public_welcome(request):
    return JsonResponse(
        {
            "message": "Welcome to the School Management System",
            "detail": "Prefix school API and admin paths with /t/<school-slug>/.",
        }
    )


urlpatterns = [
    path("", public_welcome),
]
