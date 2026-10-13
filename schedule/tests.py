from django.contrib import admin
from django.test import SimpleTestCase

from .models import Period


class TimetableAdminTests(SimpleTestCase):
    def test_periods_are_registered_under_timetable_section(self):
        self.assertIn(Period, admin.site._registry)
        self.assertEqual(Period._meta.app_config.verbose_name, "Timetable")

    def test_period_list_shows_timetable_details(self):
        period_admin = admin.site._registry[Period]

        self.assertEqual(
            period_admin.get_list_display(None),
            (
                "day_of_week",
                "start_time",
                "end_time",
                "classroom",
                "subject",
                "teacher",
            ),
        )
