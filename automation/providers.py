import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.mail import send_mail


class NotificationProviderError(Exception):
    pass


def send_email_delivery(delivery):
    notification = delivery.notification
    if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL:
        raise NotificationProviderError("Email delivery is not configured.")
    sent_count = send_mail(
        subject=notification.title,
        message=notification.message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[delivery.destination],
        fail_silently=False,
    )
    if sent_count != 1:
        raise NotificationProviderError("The email backend did not accept the message.")
    return ""


def send_sms_delivery(delivery):
    username = settings.AFRICASTALKING_USERNAME
    api_key = settings.AFRICASTALKING_API_KEY
    if not username or not api_key:
        raise NotificationProviderError("Africa's Talking SMS is not configured.")

    payload = {
        "username": username,
        "to": delivery.destination,
        "message": delivery.notification.message,
    }
    if settings.AFRICASTALKING_SENDER_ID:
        payload["from"] = settings.AFRICASTALKING_SENDER_ID
    request = urllib.request.Request(
        "https://api.africastalking.com/version1/messaging",
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "apiKey": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NotificationProviderError("Africa's Talking SMS request failed.") from exc

    if not isinstance(data, dict):
        raise NotificationProviderError("Africa's Talking returned an invalid response.")
    message_data = data.get("SMSMessageData")
    recipients = message_data.get("Recipients") if isinstance(message_data, dict) else None
    if not isinstance(recipients, list):
        raise NotificationProviderError("Africa's Talking returned an invalid response.")
    result = next(
        (
            item
            for item in recipients
            if isinstance(item, dict) and item.get("number") == delivery.destination
        ),
        None,
    )
    if result is None or result.get("status") != "Success":
        raise NotificationProviderError("Africa's Talking rejected the SMS.")
    return str(result.get("messageId", ""))[:120]
