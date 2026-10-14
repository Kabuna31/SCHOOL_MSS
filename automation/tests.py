from datetime import date, time, timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from academic.models import (
    ClassLevel,
    ClassRoom,
    Parent,
    Stream,
    Student,
    StudentClassEnrollment,
    Teacher,
)
from administration.models import AcademicYear, School, SchoolEvent, Term
from attendance.models import AttendanceStatus, PeriodAttendance
from examination.models import ExaminationListHandler
from finance.models import DebtRecord
from schedule.models import Period
from users.models import CustomUser

from .dispatcher import deliver_one
from .models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    SchoolAutomationSettings,
)
from .providers import (
    NotificationProviderError,
    send_email_delivery,
    send_sms_delivery,
)
from .rules import process_school_automation
from .services import create_notification
from .views import (
    NotificationListView,
    NotificationPreferenceView,
    NotificationReadView,
)


class NotificationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", address="Kampala")
        self.other_school = School.objects.create(
            name="South School", address="Entebbe"
        )
        self.user = CustomUser.objects.create_user(
            email="parent@north.test", password="test-password", school=self.school
        )
        self.other_user = CustomUser.objects.create_user(
            email="parent@south.test",
            password="test-password",
            school=self.other_school,
        )
        self.factory = APIRequestFactory()

    def make_notification(self, recipient=None, **kwargs):
        return create_notification(
            school=self.school,
            recipient=recipient or self.user,
            title="School update",
            message="A school update is available.",
            **kwargs,
        )

    def test_idempotency_key_creates_only_one_notification_and_delivery(self):
        NotificationPreference.objects.create(
            school=self.school,
            user=self.user,
            email_enabled=True,
        )

        first, created_first = self.make_notification(idempotency_key="term-1")
        second, created_second = self.make_notification(idempotency_key="term-1")

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_notification_cannot_be_created_for_another_schools_user(self):
        with self.assertRaisesMessage(
            ValueError, "The notification recipient belongs to another school."
        ):
            self.make_notification(recipient=self.other_user)

        self.assertFalse(Notification.unfiltered_objects.exists())

    def test_delivery_is_marked_sent_after_provider_success(self):
        notification, _ = self.make_notification()
        delivery = NotificationDelivery.unfiltered_objects.create(
            notification=notification,
            channel=NotificationDelivery.Channel.EMAIL,
            destination=self.user.email,
            status=NotificationDelivery.Status.PROCESSING,
            attempts=1,
        )

        with patch(
            "automation.dispatcher.send_email_delivery", return_value=""
        ):
            sent = deliver_one(delivery)

        delivery.refresh_from_db()
        self.assertTrue(sent)
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)
        self.assertIsNotNone(delivery.sent_at)
        self.assertEqual(delivery.last_error, "")

    def test_delivery_failure_is_recorded_for_retry(self):
        notification, _ = self.make_notification()
        delivery = NotificationDelivery.unfiltered_objects.create(
            notification=notification,
            channel=NotificationDelivery.Channel.SMS,
            destination="+256700000000",
            status=NotificationDelivery.Status.PROCESSING,
            attempts=2,
        )
        failed_at = timezone.now()

        with (
            patch(
                "automation.dispatcher.send_sms_delivery",
                side_effect=NotificationProviderError("Provider unavailable."),
            ),
            patch("automation.dispatcher.timezone.now", return_value=failed_at),
        ):
            sent = deliver_one(delivery)

        delivery.refresh_from_db()
        self.assertFalse(sent)
        self.assertEqual(delivery.status, NotificationDelivery.Status.FAILED)
        self.assertEqual(delivery.last_error, "Provider unavailable.")
        self.assertEqual(delivery.next_attempt_at, failed_at + timedelta(minutes=2))
        self.assertIsNone(delivery.processing_started_at)

    @override_settings(EMAIL_HOST="", DEFAULT_FROM_EMAIL="noreply@example.test")
    def test_email_provider_reports_missing_configuration(self):
        notification, _ = self.make_notification()
        delivery = NotificationDelivery(
            notification=notification,
            channel=NotificationDelivery.Channel.EMAIL,
            destination=self.user.email,
        )

        with self.assertRaisesMessage(
            NotificationProviderError, "Email delivery is not configured."
        ):
            send_email_delivery(delivery)

    @override_settings(AFRICASTALKING_USERNAME="", AFRICASTALKING_API_KEY="")
    def test_sms_provider_reports_missing_configuration(self):
        notification, _ = self.make_notification()
        delivery = NotificationDelivery(
            notification=notification,
            channel=NotificationDelivery.Channel.SMS,
            destination="+256700000000",
        )

        with self.assertRaisesMessage(
            NotificationProviderError, "Africa's Talking SMS is not configured."
        ):
            send_sms_delivery(delivery)

    def test_notification_api_only_returns_the_requesting_users_notifications(self):
        notification, _ = self.make_notification()
        other_notification, _ = create_notification(
            school=self.other_school,
            recipient=self.other_user,
            title="Other update",
            message="Private update.",
        )
        request = self.factory.get("/api/notifications/")
        force_authenticate(request, user=self.user)

        response = NotificationListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [notification.pk])
        self.assertNotIn(other_notification.pk, [item["id"] for item in response.data["results"]])

    def test_read_endpoint_does_not_mark_another_schools_notification(self):
        notification, _ = create_notification(
            school=self.other_school,
            recipient=self.other_user,
            title="Other update",
            message="Private update.",
        )
        request = self.factory.post(f"/api/notifications/{notification.pk}/read/")
        force_authenticate(request, user=self.user)

        response = NotificationReadView.as_view()(request, pk=notification.pk)

        notification.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertIsNone(notification.read_at)

    def test_preferences_endpoint_creates_and_updates_only_the_current_school_record(self):
        request = self.factory.patch(
            "/api/notifications/preferences/",
            {"email_enabled": True, "sms_enabled": True},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = NotificationPreferenceView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        preference = NotificationPreference.unfiltered_objects.get(
            school=self.school, user=self.user
        )
        self.assertTrue(preference.email_enabled)
        self.assertTrue(preference.sms_enabled)


class SchoolAutomationRuleTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Automation School", address="Kampala")
        self.parent = Parent.objects.create(
            school=self.school,
            first_name="Morgan",
            last_name="Guardian",
            email="guardian@automation.test",
            phone_number="1000099",
        )
        self.student = Student.objects.create(
            school=self.school,
            first_name="Casey",
            last_name="Learner",
            admission_number="AUTO001",
            parent_guardian=self.parent,
            parent_contact=self.parent.phone_number,
        )
        self.year = AcademicYear.objects.create(
            school=self.school,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            active_year=True,
        )
        self.term = Term.objects.create(
            name="Term One",
            academic_year=self.year,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 31),
        )
        self.settings = SchoolAutomationSettings.objects.create(
            school=self.school,
            enabled=True,
        )

    def test_fee_reminders_start_at_term_date_and_repeat_at_the_interval(self):
        self.settings.fee_reminders_enabled = True
        self.settings.fee_reminder_interval_days = 7
        self.settings.save()
        debt = DebtRecord.objects.create(
            school=self.school,
            student=self.student,
            term=self.term,
            amount_added=1000,
        )

        self.assertEqual(
            process_school_automation(self.school, date(2026, 5, 31))["fees"],
            0,
        )
        self.assertEqual(
            process_school_automation(self.school, date(2026, 6, 1))["fees"],
            1,
        )
        with patch(
            "automation.rules.timezone.localdate",
            return_value=date(2026, 6, 1),
        ):
            self.assertEqual(
                process_school_automation(self.school, date(2026, 6, 7))["fees"],
                0,
            )
            self.assertEqual(
                process_school_automation(self.school, date(2026, 6, 8))["fees"],
                1,
            )

        debt.amount_paid = 1000
        debt.save()
        self.assertEqual(
            process_school_automation(self.school, date(2026, 6, 15))["fees"],
            0,
        )

    def test_event_reminder_is_created_once_on_the_configured_day(self):
        self.settings.event_reminders_enabled = True
        self.settings.event_reminder_days_before = 1
        self.settings.save()
        SchoolEvent.objects.create(
            term=self.term,
            name="Sports Day",
            event_type="other",
            start_date=date(2026, 6, 3),
        )

        self.assertEqual(
            process_school_automation(self.school, date(2026, 6, 2))["events"],
            1,
        )
        self.assertEqual(
            process_school_automation(self.school, date(2026, 6, 2))["events"],
            0,
        )

    def test_exam_reminder_targets_parents_of_enrolled_learners(self):
        self.settings.event_reminders_enabled = True
        self.settings.event_reminder_days_before = 1
        self.settings.save()
        teacher = Teacher.objects.create(
            school=self.school,
            user=self.parent.user,
            first_name="Alex",
            last_name="Teacher",
            empId="AUTO-T1",
        )
        level = ClassLevel.objects.create(school=self.school, name="Senior One")
        stream = Stream.objects.create(school=self.school, name="A")
        classroom = ClassRoom.objects.create(
            school=self.school,
            name=level,
            stream=stream,
            class_teacher=teacher,
        )
        StudentClassEnrollment.objects.create(
            school=self.school,
            classroom=classroom,
            academic_year=self.year,
            student=self.student,
        )
        exam = ExaminationListHandler.objects.create(
            school=self.school,
            name="Mid-term exams",
            term=self.term,
            start_date=date(2026, 6, 3),
            ends_date=date(2026, 6, 5),
            out_of=100,
            created_by=teacher,
        )
        exam.classrooms.add(classroom)

        self.assertEqual(
            process_school_automation(self.school, date(2026, 6, 2))["events"],
            1,
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.parent.user,
                title="Upcoming examination: Mid-term exams",
            ).exists()
        )

    def test_attendance_alert_requires_consecutive_absent_school_days(self):
        self.settings.attendance_alerts_enabled = True
        self.settings.consecutive_absence_threshold = 2
        self.settings.save()
        absent = AttendanceStatus.objects.create(
            name="Absent", code="A", absent=True
        )
        PeriodAttendance.objects.create(
            student=self.student,
            date=date(2026, 6, 2),
            period=1,
            status=absent,
        )
        PeriodAttendance.objects.create(
            student=self.student,
            date=date(2026, 6, 3),
            period=1,
            status=absent,
        )

        self.assertEqual(
            process_school_automation(self.school, date(2026, 6, 3))[
                "attendance"
            ],
            1,
        )
        self.assertEqual(
            process_school_automation(self.school, date(2026, 6, 3))[
                "attendance"
            ],
            0,
        )

    def test_management_command_accepts_school_and_date_filters(self):
        output = StringIO()

        call_command(
            "run_school_automation",
            school_id=self.school.pk,
            run_date="2026-06-02",
            stdout=output,
        )

        self.assertIn(
            "Automation School: {'attendance': 0, 'fees': 0, 'events': 0, "
            "'timetable': 0}",
            output.getvalue(),
        )

    def test_timetable_conflicts_are_notified_once_per_staff_member_per_day(self):
        staff = CustomUser.objects.create_user(
            email="admin@automation.test",
            password="testing",
            phone_number="1000088",
            school=self.school,
            is_staff=True,
        )
        self.settings.timetable_checks_enabled = True
        self.settings.save()
        first = SimpleNamespace(
            pk=1,
            day_of_week="Monday",
            start_time=time(8, 0),
            end_time=time(9, 0),
            classroom_id=10,
            classroom="Senior One A",
            teacher_id=20,
        )
        second = SimpleNamespace(
            pk=2,
            day_of_week="Monday",
            start_time=time(8, 30),
            end_time=time(9, 30),
            classroom_id=11,
            classroom="Senior One B",
            teacher_id=20,
        )
        with patch("automation.rules.Period.objects.filter") as period_filter:
            period_filter.return_value.select_related.return_value.order_by.return_value = [
                first,
                second,
            ]
            self.assertEqual(
                process_school_automation(self.school, date(2026, 6, 1))[
                    "timetable"
                ],
                1,
            )
            self.assertEqual(
                process_school_automation(self.school, date(2026, 6, 1))[
                    "timetable"
                ],
                0,
            )

        self.assertTrue(
            Notification.objects.filter(
                recipient=staff,
                title="Timetable conflict detected",
            ).exists()
        )
