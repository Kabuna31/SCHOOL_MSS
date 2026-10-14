from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from administration.managers import SchoolScopedManager
from administration.models import School


class Notification(models.Model):
    class Category(models.TextChoices):
        ACADEMIC = "academic", "Academic"
        ATTENDANCE = "attendance", "Attendance"
        FINANCE = "finance", "Finance"
        SCHEDULE = "schedule", "Schedule"
        SYSTEM = "system", "System"

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="notifications"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="school_notifications",
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.SYSTEM
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    idempotency_key = models.CharField(max_length=180, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    read_at = models.DateTimeField(blank=True, null=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        ordering = ("-created_at", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=("school", "idempotency_key"),
                condition=Q(idempotency_key__isnull=False),
                name="unique_school_notification_idempotency",
            )
        ]
        indexes = [
            models.Index(fields=("school", "recipient", "read_at", "-created_at")),
        ]

    def __str__(self):
        return f"{self.title} — {self.recipient}"


class NotificationPreference(models.Model):
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="school_notification_preferences",
    )
    email_enabled = models.BooleanField(default=False)
    sms_enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("school", "user"),
                name="unique_school_notification_preference",
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.school}"


class NotificationDelivery(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="deliveries"
    )
    channel = models.CharField(max_length=10, choices=Channel.choices)
    destination = models.CharField(max_length=254)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    processing_started_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    last_error = models.CharField(max_length=500, blank=True)
    provider_reference = models.CharField(max_length=120, blank=True)

    objects = models.Manager()
    unfiltered_objects = models.Manager()

    class Meta:
        ordering = ("next_attempt_at", "pk")
        constraints = [
            models.UniqueConstraint(
                fields=("notification", "channel"),
                name="unique_notification_delivery_channel",
            )
        ]
        indexes = [
            models.Index(fields=("status", "next_attempt_at")),
        ]

    def __str__(self):
        return f"{self.channel} delivery for notification {self.notification_id}"


class SchoolAutomationSettings(models.Model):
    school = models.OneToOneField(
        School, on_delete=models.CASCADE, related_name="automation_settings"
    )
    enabled = models.BooleanField(
        default=False,
        help_text="Enable scheduled parent/staff automation after reviewing settings.",
    )
    attendance_alerts_enabled = models.BooleanField(default=False)
    consecutive_absence_threshold = models.PositiveSmallIntegerField(default=1)
    fee_reminders_enabled = models.BooleanField(default=False)
    fee_reminder_interval_days = models.PositiveSmallIntegerField(default=7)
    event_reminders_enabled = models.BooleanField(default=False)
    event_reminder_days_before = models.PositiveSmallIntegerField(default=1)
    timetable_checks_enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return f"Automation settings — {self.school}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.consecutive_absence_threshold < 1:
            raise ValidationError(
                {"consecutive_absence_threshold": "Must be at least one day."}
            )
        if self.fee_reminder_interval_days < 1:
            raise ValidationError({"fee_reminder_interval_days": "Must be at least one day."})
