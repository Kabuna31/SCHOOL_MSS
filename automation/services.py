from django.db import IntegrityError, transaction

from .models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
)


def create_notification(
    *,
    school,
    recipient,
    title,
    message,
    category=Notification.Category.SYSTEM,
    idempotency_key=None,
):
    if recipient.school_id and recipient.school_id != school.pk:
        raise ValueError("The notification recipient belongs to another school.")

    with transaction.atomic():
        if idempotency_key:
            try:
                notification, created = Notification.unfiltered_objects.get_or_create(
                    school=school,
                    idempotency_key=idempotency_key,
                    defaults={
                        "recipient": recipient,
                        "title": title,
                        "message": message,
                        "category": category,
                    },
                )
            except IntegrityError:
                notification = Notification.unfiltered_objects.get(
                    school=school, idempotency_key=idempotency_key
                )
                created = False
        else:
            notification = Notification.unfiltered_objects.create(
                school=school,
                recipient=recipient,
                title=title,
                message=message,
                category=category,
            )
            created = True

        if not created:
            return notification, False

        preferences, _ = NotificationPreference.unfiltered_objects.get_or_create(
            school=school,
            user=recipient,
        )
        deliveries = []
        if preferences.email_enabled and recipient.email:
            deliveries.append(
                NotificationDelivery(
                    notification=notification,
                    channel=NotificationDelivery.Channel.EMAIL,
                    destination=recipient.email,
                )
            )
        if preferences.sms_enabled and recipient.phone_number:
            deliveries.append(
                NotificationDelivery(
                    notification=notification,
                    channel=NotificationDelivery.Channel.SMS,
                    destination=recipient.phone_number,
                )
            )
        NotificationDelivery.unfiltered_objects.bulk_create(deliveries)

    return notification, True
