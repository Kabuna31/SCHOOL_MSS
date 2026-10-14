from django.urls import path

from .views import (
    NotificationListView,
    NotificationPreferenceView,
    NotificationReadAllView,
    NotificationReadView,
)


urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
    path("preferences/", NotificationPreferenceView.as_view(), name="notification-preferences"),
    path("<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
]
