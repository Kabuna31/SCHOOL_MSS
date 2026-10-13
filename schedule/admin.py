from django.contrib import admin

from .models import Period


@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = (
        "day_of_week",
        "start_time",
        "end_time",
        "classroom",
        "subject",
        "teacher",
    )
    list_filter = ("day_of_week", "classroom")
    ordering = ("day_of_week", "start_time", "classroom")
    list_select_related = ("classroom", "subject", "teacher")
