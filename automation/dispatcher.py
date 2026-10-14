import logging
import smtplib
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import NotificationDelivery
from .providers import (
    NotificationProviderError,
    send_email_delivery,
    send_sms_delivery,
)


logger = logging.getLogger(__name__)
MAX_DELIVERY_ATTEMPTS = 5
PROCESSING_TIMEOUT = timedelta(minutes=15)


def claim_next_delivery(school_id=None):
    now = timezone.now()
    stale_before = now - PROCESSING_TIMEOUT
    with transaction.atomic():
        deliveries = NotificationDelivery.unfiltered_objects.select_for_update(
            skip_locked=True
        ).filter(
            attempts__lt=MAX_DELIVERY_ATTEMPTS,
            next_attempt_at__lte=now,
        ).filter(models_q_queued_or_retryable(stale_before))
        if school_id is not None:
            deliveries = deliveries.filter(notification__school_id=school_id)
        delivery = deliveries.order_by("next_attempt_at", "pk").first()
        if delivery is None:
            return None
        delivery.status = NotificationDelivery.Status.PROCESSING
        delivery.processing_started_at = now
        delivery.attempts += 1
        delivery.save(
            update_fields=("status", "processing_started_at", "attempts")
        )
        return delivery


def models_q_queued_or_retryable(stale_before):
    from django.db.models import Q

    return (
        Q(status__in=(NotificationDelivery.Status.QUEUED, NotificationDelivery.Status.FAILED))
        | Q(
            status=NotificationDelivery.Status.PROCESSING,
            processing_started_at__lt=stale_before,
        )
    )


def deliver_one(delivery):
    try:
        if delivery.channel == NotificationDelivery.Channel.EMAIL:
            provider_reference = send_email_delivery(delivery)
        elif delivery.channel == NotificationDelivery.Channel.SMS:
            provider_reference = send_sms_delivery(delivery)
        else:
            raise NotificationProviderError("Unsupported notification channel.")
    except (NotificationProviderError, OSError, smtplib.SMTPException, ValueError) as exc:
        delay = min(2 ** max(delivery.attempts - 1, 0), 1440)
        delivery.status = NotificationDelivery.Status.FAILED
        delivery.last_error = str(exc)[:500]
        delivery.next_attempt_at = timezone.now() + timedelta(minutes=delay)
        delivery.processing_started_at = None
        delivery.save(
            update_fields=(
                "status",
                "last_error",
                "next_attempt_at",
                "processing_started_at",
            )
        )
        logger.warning(
            "Notification delivery %s failed on attempt %s: %s",
            delivery.pk,
            delivery.attempts,
            delivery.last_error,
        )
        return False

    delivery.status = NotificationDelivery.Status.SENT
    delivery.sent_at = timezone.now()
    delivery.last_error = ""
    delivery.provider_reference = provider_reference
    delivery.processing_started_at = None
    delivery.save(
        update_fields=(
            "status",
            "sent_at",
            "last_error",
            "provider_reference",
            "processing_started_at",
        )
    )
    return True


def process_outbox(limit=100, school_id=None):
    processed = sent = failed = 0
    for _ in range(limit):
        delivery = claim_next_delivery(school_id=school_id)
        if delivery is None:
            break
        processed += 1
        if deliver_one(delivery):
            sent += 1
        else:
            failed += 1
    return {"processed": processed, "sent": sent, "failed": failed}
