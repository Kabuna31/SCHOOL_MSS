from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from utils.bulk_imports import get_request_school

from .models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    SchoolAutomationSettings,
)


class SchoolScopedAdminMixin:
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        school = get_request_school(request)
        if school is None:
            return queryset.none()
        return queryset.filter(school=school)


@admin.register(Notification)
class NotificationAdmin(SchoolScopedAdminMixin, admin.ModelAdmin):
    list_display = ("title", "recipient", "category", "created_at", "read_at")
    list_filter = ("category", "created_at", "read_at")
    search_fields = ("title", "message", "recipient__email")
    readonly_fields = (
        "school",
        "recipient",
        "category",
        "title",
        "message",
        "idempotency_key",
        "created_at",
        "read_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "notification",
        "channel",
        "status",
        "attempts",
        "next_attempt_at",
        "sent_at",
    )
    list_filter = ("channel", "status", "next_attempt_at")
    search_fields = ("notification__title", "destination")
    readonly_fields = (
        "notification",
        "channel",
        "destination",
        "status",
        "attempts",
        "next_attempt_at",
        "processing_started_at",
        "sent_at",
        "last_error",
        "provider_reference",
    )
    actions = ("retry_failed_deliveries",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related(
            "notification", "notification__school", "notification__recipient"
        )
        school = get_request_school(request)
        if school is None:
            return queryset.none()
        return queryset.filter(notification__school=school)

    def retry_failed_deliveries(self, request, queryset):
        updated = queryset.filter(status=NotificationDelivery.Status.FAILED).update(
            status=NotificationDelivery.Status.QUEUED,
            attempts=0,
            next_attempt_at=timezone.now(),
            processing_started_at=None,
            last_error="",
        )
        self.message_user(request, f"Queued {updated} delivery(s) for retry.")

    retry_failed_deliveries.short_description = "Retry failed deliveries"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(SchoolScopedAdminMixin, admin.ModelAdmin):
    list_display = ("user", "email_enabled", "sms_enabled", "updated_at")
    list_filter = ("email_enabled", "sms_enabled")
    search_fields = ("user__email", "user__phone_number")
    readonly_fields = ("school", "user", "updated_at")


@admin.register(SchoolAutomationSettings)
class SchoolAutomationSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "enabled",
        "attendance_alerts_enabled",
        "fee_reminders_enabled",
        "event_reminders_enabled",
        "timetable_checks_enabled",
        "updated_at",
    )
    list_filter = (
        "enabled",
        "attendance_alerts_enabled",
        "fee_reminders_enabled",
        "event_reminders_enabled",
        "timetable_checks_enabled",
    )
    readonly_fields = ("updated_at",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        school = get_request_school(request)
        if school is None:
            return queryset.none()
        return queryset.filter(school=school)

    def save_model(self, request, obj, form, change):
        school = get_request_school(request)
        if school is None:
            raise PermissionDenied("Your account is not associated with a school.")
        obj.school = school
        super().save_model(request, obj, form, change)
