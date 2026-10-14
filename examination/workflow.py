from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from academic.models import StudentClassEnrollment
from .models import MarksManagement, MarksSubmission, MarksSubmissionEvent


def submission_readiness(submission):
    if submission.exam.term_id is None:
        raise ValidationError("Marks workflow requires an exam assigned to a term.")
    enrollments = StudentClassEnrollment.objects.filter(
        school=submission.school,
        classroom=submission.classroom,
        academic_year=submission.exam.term.academic_year,
        student__isnull=False,
        student__school=submission.school,
    ).select_related("student")
    enrollment_ids = list(enrollments.values_list("pk", flat=True))
    marks_by_enrollment = dict(
        MarksManagement.objects.filter(
            school=submission.school,
            exam_name=submission.exam,
            subject=submission.subject,
            student_id__in=enrollment_ids,
        )
        .values("student_id")
        .annotate(mark_count=Count("pk"))
        .values_list("student_id", "mark_count")
    )
    missing_ids = [
        enrollment_id
        for enrollment_id in enrollment_ids
        if marks_by_enrollment.get(enrollment_id, 0) == 0
    ]
    duplicate_ids = [
        enrollment_id
        for enrollment_id, count in marks_by_enrollment.items()
        if count > 1
    ]
    return {
        "enrolled_count": len(enrollment_ids),
        "marked_count": sum(count == 1 for count in marks_by_enrollment.values()),
        "missing_admission_numbers": list(
            enrollments.filter(pk__in=missing_ids).values_list(
                "student__admission_number", flat=True
            )
        ),
        "duplicate_admission_numbers": list(
            enrollments.filter(pk__in=duplicate_ids).values_list(
                "student__admission_number", flat=True
            )
        ),
        "ready": bool(enrollment_ids) and not missing_ids and not duplicate_ids,
    }


def ensure_submission(school, exam, classroom, subject, actor):
    submission, created = MarksSubmission.unfiltered_objects.get_or_create(
        school=school,
        exam=exam,
        classroom=classroom,
        subject=subject,
    )
    if created:
        MarksSubmissionEvent.objects.create(
            submission=submission,
            action=MarksSubmissionEvent.Action.CREATED,
            actor=actor,
        )
    return submission


@transaction.atomic
def transition_submission(submission_id, school, action, actor, note=""):
    submission = (
        MarksSubmission.unfiltered_objects.select_for_update()
        .select_related("exam", "classroom", "subject")
        .get(pk=submission_id, school=school)
    )
    now = timezone.now()

    if action == MarksSubmissionEvent.Action.SUBMITTED:
        if submission.status != MarksSubmission.Status.DRAFT:
            raise ValidationError("Only draft marks can be submitted.")
        readiness = submission_readiness(submission)
        if not readiness["ready"]:
            raise ValidationError(
                {
                    "readiness": readiness,
                    "detail": "Enter exactly one mark for every enrolled learner "
                    "before submitting.",
                }
            )
        submission.status = MarksSubmission.Status.SUBMITTED
        submission.submitted_by = actor
        submission.submitted_at = now
    elif action == MarksSubmissionEvent.Action.APPROVED:
        if submission.status != MarksSubmission.Status.SUBMITTED:
            raise ValidationError("Only submitted marks can be approved.")
        readiness = submission_readiness(submission)
        if not readiness["ready"]:
            raise ValidationError(
                {
                    "readiness": readiness,
                    "detail": "Marks are no longer complete and cannot be approved.",
                }
            )
        submission.status = MarksSubmission.Status.APPROVED
        submission.approved_by = actor
        submission.approved_at = now
    elif action == MarksSubmissionEvent.Action.RELEASED:
        if submission.status != MarksSubmission.Status.APPROVED:
            raise ValidationError("Only approved marks can be released.")
        submission.status = MarksSubmission.Status.RELEASED
        submission.released_at = now
    elif action == MarksSubmissionEvent.Action.REOPENED:
        if submission.status == MarksSubmission.Status.DRAFT:
            raise ValidationError("Draft marks are already open for editing.")
        submission.status = MarksSubmission.Status.DRAFT
        submission.submitted_by = None
        submission.submitted_at = None
        submission.approved_by = None
        submission.approved_at = None
        submission.released_at = None
    else:
        raise ValidationError("Unsupported marks workflow action.")

    submission.save()
    event = MarksSubmissionEvent.objects.create(
        submission=submission,
        action=action,
        actor=actor,
        note=note,
    )
    return submission, event
