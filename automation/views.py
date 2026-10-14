from django.core.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.bulk_imports import get_request_school

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        school = get_request_school(request)
        if school is None:
            raise PermissionDenied("Your account is not associated with a school.")

        notifications = Notification.objects.filter(
            school=school, recipient=request.user
        )
        unread_only = request.query_params.get("unread", "").lower()
        if unread_only in {"1", "true", "yes"}:
            notifications = notifications.filter(read_at__isnull=True)
        elif unread_only not in {"", "0", "false", "no"}:
            return Response(
                {"unread": ["Use true or false."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        page = notifications[:100]
        return Response(
            {
                "unread_count": notifications.filter(read_at__isnull=True).count(),
                "results": NotificationSerializer(page, many=True).data,
            }
        )


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        school = get_request_school(request)
        if school is None:
            raise PermissionDenied("Your account is not associated with a school.")
        notification = Notification.objects.filter(
            pk=pk, school=school, recipient=request.user
        ).first()
        if notification is None:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=("read_at",))
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        school = get_request_school(request)
        if school is None:
            raise PermissionDenied("Your account is not associated with a school.")
        updated = Notification.objects.filter(
            school=school,
            recipient=request.user,
            read_at__isnull=True,
        ).update(read_at=timezone.now())
        return Response({"marked_read": updated})


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request):
        school = get_request_school(request)
        if school is None:
            raise PermissionDenied("Your account is not associated with a school.")
        preference, _ = NotificationPreference.objects.get_or_create(
            school=school,
            user=request.user,
        )
        return preference

    def get(self, request):
        return Response(
            NotificationPreferenceSerializer(self.get_object(request)).data
        )

    def patch(self, request):
        preference = self.get_object(request)
        serializer = NotificationPreferenceSerializer(
            preference, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
