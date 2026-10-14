from collections import defaultdict
from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone

from academic.models import Student
from administration.models import SchoolEvent
from attendance.models import PeriodAttendance
from examination.models import ExaminationListHandler
from finance.models import DebtRecord
from schedule.models import Period
from users.models import CustomUser

from .models import Notification, SchoolAutomationSettings
from .services import create_notification


def process_school_automation(school, today=None):
    today = today or timezone.localdate()
    automation_settings = SchoolAutomationSettings.unfiltered_objects.filter(
        school=school,
        enabled=True,
    ).first()
    if automation_settings is None:
        return {"attendance": 0, "fees": 0, "events": 0, "timetable": 0}

    totals = {"attendance": 0, "fees": 0, "events": 0, "timetable": 0}
    if automation_settings.attendance_alerts_enabled:
        totals["attendance"] = _process_attendance_alerts(
            school,
            today,
            automation_settings.consecutive_absence_threshold,
        )
    if automation_settings.fee_reminders_enabled:
        totals["fees"] = _process_fee_reminders(
            school,
            today,
            automation_settings.fee_reminder_interval_days,
        )
    if automation_settings.event_reminders_enabled:
        totals["events"] = _process_event_reminders(
            school,
            today,
            automation_settings.event_reminder_days_before,
        )
    if automation_settings.timetable_checks_enabled:
        totals["timetable"] = _process_timetable_conflicts(school, today)
    return totals


def _parent_students(school):
    return (
        Student.objects.filter(
            school=school,
            parent_guardian__user__isnull=False,
        )
        .select_related("parent_guardian__user")
        .distinct()
    )


def _process_attendance_alerts(school, today, threshold):
    if threshold < 1:
        return 0

    lookback_start = today - timedelta(days=365)
    holiday_events = SchoolEvent.objects.filter(
        term__academic_year__school=school,
        event_type="holiday",
        start_date__lte=today,
    ).filter(Q(end_date__gte=lookback_start) | Q(end_date__isnull=True)).values_list(
        "start_date", "end_date"
    )
    holidays = [
        (start_date, end_date or start_date)
        for start_date, end_date in holiday_events
    ]

    attendance_by_student = defaultdict(lambda: defaultdict(list))
    attendance_rows = PeriodAttendance.objects.filter(
        student__school=school,
        date__gte=lookback_start,
        date__lte=today,
    ).values_list(
        "student_id",
        "date",
        "status__absent",
        "status__excused",
    )
    for student_id, attendance_date, is_absent, is_excused in attendance_rows:
        attendance_by_student[student_id][attendance_date].append(
            bool(is_absent) and not bool(is_excused)
        )

    created_count = 0
    for student in _parent_students(school).iterator():
        daily_statuses = attendance_by_student.get(student.pk, {})
        streak_dates = []
        current_date = today
        while current_date >= lookback_start:
            if current_date.weekday() >= 5 or any(
                start <= current_date <= end for start, end in holidays
            ):
                current_date -= timedelta(days=1)
                continue

            statuses = daily_statuses.get(current_date)
            if not statuses or not all(statuses):
                break
            streak_dates.append(current_date)
            current_date -= timedelta(days=1)

        if len(streak_dates) < threshold:
            continue

        streak_start = min(streak_dates)
        parent_user = student.parent_guardian.user
        _, created = create_notification(
            school=school,
            recipient=parent_user,
            category=Notification.Category.ATTENDANCE,
            title="Attendance follow-up needed",
            message=(
                f"{student.full_name} has been recorded absent for "
                f"{len(streak_dates)} consecutive school days, through "
                f"{streak_dates[0].isoformat()}."
            ),
            idempotency_key=(
                f"attendance-absence:{student.pk}:{streak_start.isoformat()}"
            ),
        )
        created_count += int(created)
    return created_count


def _process_fee_reminders(school, today, interval_days):
    if interval_days < 1:
        return 0

    debts = (
        DebtRecord.objects.filter(
            school=school,
            student__school=school,
            term__academic_year__school=school,
            is_reversed=False,
            term__start_date__lte=today,
            amount_paid__lt=F("amount_added"),
        )
        .select_related("student__parent_guardian__user", "term")
        .iterator()
    )
    created_count = 0
    for debt in debts:
        student = debt.student
        parent = student.parent_guardian
        if parent is None or parent.user_id is None or debt.balance <= 0:
            continue

        key_prefix = f"fee-reminder:{debt.pk}:"
        previous_reminder = Notification.unfiltered_objects.filter(
            school=school,
            idempotency_key__startswith=key_prefix,
        ).order_by("-created_at").first()
        if (
            previous_reminder
            and (today - timezone.localdate(previous_reminder.created_at)).days
            < interval_days
        ):
            continue

        _, created = create_notification(
            school=school,
            recipient=parent.user,
            category=Notification.Category.FINANCE,
            title="Outstanding school fees",
            message=(
                f"{student.full_name} has an outstanding balance of "
                f"{debt.balance} for {debt.term.name}. The term started "
                f"on {debt.term.start_date.isoformat()}."
            ),
            idempotency_key=f"{key_prefix}{today.isoformat()}",
        )
        created_count += int(created)
    return created_count


def _process_event_reminders(school, today, days_before):
    target_date = today + timedelta(days=days_before)
    events = SchoolEvent.objects.filter(
        term__academic_year__school=school,
        start_date=target_date,
    ).select_related("term")
    students = _parent_students(school)
    created_count = 0
    for event in events:
        for student in students.iterator():
            parent_user = student.parent_guardian.user
            _, created = create_notification(
                school=school,
                recipient=parent_user,
                category=Notification.Category.SCHEDULE,
                title=f"Upcoming school event: {event.name}",
                message=(
                    f"{event.name} is scheduled for {event.start_date.isoformat()}. "
                    f"{event.description}".strip()
                ),
                idempotency_key=f"school-event:{event.pk}:{parent_user.pk}",
            )
            created_count += int(created)
    created_count += _process_exam_reminders(school, target_date)
    return created_count


def _process_exam_reminders(school, target_date):
    exams = (
        ExaminationListHandler.objects.filter(
            school=school,
            term__academic_year__school=school,
            start_date=target_date,
            classrooms__school=school,
        )
        .select_related("term")
        .distinct()
    )
    created_count = 0
    for exam in exams:
        students = _parent_students(school).filter(
            student_classes__classroom__in=exam.classrooms.all(),
            student_classes__academic_year=exam.term.academic_year,
        )
        for student in students.iterator():
            parent_user = student.parent_guardian.user
            _, created = create_notification(
                school=school,
                recipient=parent_user,
                category=Notification.Category.SCHEDULE,
                title=f"Upcoming examination: {exam.name}",
                message=(
                    f"{exam.name} starts on {exam.start_date.isoformat()}."
                ),
                idempotency_key=f"exam-reminder:{exam.pk}:{parent_user.pk}",
            )
            created_count += int(created)
    return created_count


def _process_timetable_conflicts(school, today):
    periods = list(
        Period.objects.filter(
            classroom__school=school,
            teacher__school=school,
            subject__school=school,
        )
        .select_related("classroom", "teacher")
        .order_by("day_of_week", "start_time", "pk")
    )
    staff = CustomUser.objects.filter(school=school, is_staff=True)
    created_count = 0
    for index, period in enumerate(periods):
        for other in periods[index + 1 :]:
            if (
                period.day_of_week != other.day_of_week
                or period.start_time >= other.end_time
                or other.start_time >= period.end_time
            ):
                continue
            if (
                period.classroom_id != other.classroom_id
                and period.teacher_id != other.teacher_id
            ):
                continue

            conflict_types = []
            if period.classroom_id == other.classroom_id:
                conflict_types.append("classroom")
            if period.teacher_id == other.teacher_id:
                conflict_types.append("teacher")
            first_id, second_id = sorted((period.pk, other.pk))
            for recipient in staff:
                _, created = create_notification(
                    school=school,
                    recipient=recipient,
                    category=Notification.Category.SCHEDULE,
                    title="Timetable conflict detected",
                    message=(
                        f"{', '.join(conflict_types).capitalize()} conflict on "
                        f"{period.day_of_week}: {period.classroom} / {other.classroom} "
                        f"from {max(period.start_time, other.start_time):%H:%M} to "
                        f"{min(period.end_time, other.end_time):%H:%M}."
                    ),
                    idempotency_key=(
                        f"timetable-conflict:{first_id}:{second_id}:"
                        f"{recipient.pk}:{today.isoformat()}"
                    ),
                )
                created_count += int(created)
    return created_count
