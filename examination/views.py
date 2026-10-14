import openpyxl
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from academic.models import (
    AllocatedSubject,
    ClassRoom,
    Student,
    StudentClassEnrollment,
    Subject,
    Teacher,
)
from administration.models import AcademicYear
from utils.bulk_imports import (
    decimal_value,
    excel_response,
    get_request_school,
    iter_excel_rows,
    text_value,
)
from .models import ExaminationListHandler, MarksManagement
from .models import MarksSubmission, MarksSubmissionEvent
from .reports import (
    analysis_payload,
    analysis_pdf,
    build_class_report,
    marksheet_pdf,
    report_cards_pdf,
    report_scope,
)
from .serializers import (
    MarksSubmissionActionSerializer,
    MarksSubmissionListSerializer,
    MarksSubmissionSelectionSerializer,
    MarksSubmissionSerializer,
)
from .workflow import ensure_submission, submission_readiness, transition_submission
from automation.models import Notification
from automation.services import create_notification


class ClassReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get_report_data(self, request, mid_term=False):
        school, term, classroom, student_id = report_scope(request)
        return build_class_report(
            school,
            term,
            classroom,
            student_id,
            mid_term,
            published_only=(
                request.user.is_parent
                and not request.user.is_staff
                and not request.user.is_superuser
            ),
        )


class ReportCardsView(ClassReportView):
    def get(self, request):
        return report_cards_pdf(self.get_report_data(request))


class MidTermReportCardsView(ClassReportView):
    def get(self, request):
        return report_cards_pdf(
            self.get_report_data(request, mid_term=True),
            mid_term=True,
        )


class MarksheetView(ClassReportView):
    def get(self, request):
        return marksheet_pdf(self.get_report_data(request))


class ResultAnalysisView(ClassReportView):
    def get(self, request):
        return Response(analysis_payload(self.get_report_data(request)))


class ResultAnalysisPDFView(ClassReportView):
    def get(self, request):
        return analysis_pdf(self.get_report_data(request))


def _marks_workflow_scope(request, values):
    school, exam, classroom = _marks_class_scope(
        request, values["exam_id"], values["classroom_id"]
    )
    subject = Subject.objects.filter(
        pk=values["subject_id"], school=school
    ).first()
    if subject is None:
        raise NotFound("The subject was not found in your school.")
    return school, exam, classroom, subject


def _marks_class_scope(request, exam_id, classroom_id):
    school = get_request_school(request)
    if school is None:
        raise PermissionDenied("Your account is not associated with a school.")
    exam = (
        ExaminationListHandler.objects.select_related("term__academic_year")
        .filter(pk=exam_id, school=school)
        .first()
    )
    classroom = ClassRoom.objects.filter(
        pk=classroom_id, school=school
    ).first()
    if exam is None or classroom is None:
        raise NotFound("The exam or class was not found in your school.")
    if exam.term_id is None:
        raise ValidationError("Marks workflow requires an exam assigned to a term.")
    if not exam.classrooms.filter(pk=classroom.pk).exists():
        raise ValidationError("The exam is not assigned to the selected class.")
    return school, exam, classroom


def _teacher_has_subject_scope(user, school, exam, classroom, subject):
    if user.is_staff or user.is_superuser:
        return True
    teacher = Teacher.objects.filter(user=user, school=school).first()
    if teacher is None:
        return False
    return AllocatedSubject.objects.filter(
        school=school,
        teacher_name=teacher,
        class_room=classroom,
        subject=subject,
        academic_year=exam.term.academic_year,
    ).filter(Q(term__isnull=True) | Q(term=exam.term)).exists()


class MarksSubmissionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = MarksSubmissionListSerializer(
            data={
                "exam_id": request.query_params.get("exam_id"),
                "classroom_id": request.query_params.get("classroom_id"),
            }
        )
        params.is_valid(raise_exception=True)
        school, exam, classroom = _marks_class_scope(
            request,
            params.validated_data["exam_id"],
            params.validated_data["classroom_id"],
        )
        subjects = Subject.objects.filter(school=school).order_by("name")
        if not (request.user.is_staff or request.user.is_superuser):
            teacher = Teacher.objects.filter(user=request.user, school=school).first()
            if teacher is None:
                raise PermissionDenied(
                    "Only an assigned teacher or school administrator can view marks readiness."
                )
            subjects = subjects.filter(
                allocated_subjects__teacher_name=teacher,
                allocated_subjects__class_room=classroom,
                allocated_subjects__academic_year=exam.term.academic_year,
            ).distinct()
        results = []
        for subject in subjects:
            if not _teacher_has_subject_scope(
                request.user, school, exam, classroom, subject
            ):
                continue
            submission = MarksSubmission.objects.filter(
                school=school,
                exam=exam,
                classroom=classroom,
                subject=subject,
            ).first()
            probe = submission or MarksSubmission(
                school=school,
                exam=exam,
                classroom=classroom,
                subject=subject,
            )
            results.append(
                {
                    **(
                        MarksSubmissionSerializer(submission).data
                        if submission
                        else {
                            "id": None,
                            "exam": exam.pk,
                            "exam_name": exam.name,
                            "classroom": classroom.pk,
                            "classroom_name": str(classroom),
                            "subject": subject.pk,
                            "subject_name": subject.name,
                            "status": "not_started",
                            "submitted_at": None,
                            "approved_at": None,
                            "released_at": None,
                        }
                    ),
                    "readiness": submission_readiness(probe),
                }
            )
        return Response(results)

    def post(self, request):
        params = MarksSubmissionSelectionSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        school, exam, classroom, subject = _marks_workflow_scope(
            request, params.validated_data
        )
        if not _teacher_has_subject_scope(
            request.user, school, exam, classroom, subject
        ):
            raise PermissionDenied(
                "You are not assigned to enter marks for this class and subject."
            )
        submission = ensure_submission(
            school, exam, classroom, subject, request.user
        )
        submission, _ = transition_submission(
            submission.pk,
            school,
            MarksSubmissionEvent.Action.SUBMITTED,
            request.user,
        )
        return Response(
            {
                **MarksSubmissionSerializer(submission).data,
                "readiness": submission_readiness(submission),
            },
            status=status.HTTP_200_OK,
        )


class MarksSubmissionActionView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk, action):
        school = get_request_school(request)
        if school is None:
            raise PermissionDenied("Your account is not associated with a school.")
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied(
                "Only a school administrator can approve, release, or reopen marks."
            )
        action_map = {
            "approve": MarksSubmissionEvent.Action.APPROVED,
            "release": MarksSubmissionEvent.Action.RELEASED,
            "reopen": MarksSubmissionEvent.Action.REOPENED,
        }
        event_action = action_map.get(action)
        if event_action is None:
            raise NotFound("The requested marks workflow action does not exist.")
        serializer = MarksSubmissionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            submission, event = transition_submission(
                pk,
                school,
                event_action,
                request.user,
                serializer.validated_data.get("note", ""),
            )
        except MarksSubmission.DoesNotExist as exc:
            raise NotFound("Marks submission not found.") from exc
        if event_action == MarksSubmissionEvent.Action.RELEASED:
            tenant_prefix = request.path.split("/api/", maxsplit=1)[0]
            report_path = (
                f"{tenant_prefix}/api/examination/reports/report-cards/"
                if tenant_prefix
                else "/api/examination/reports/report-cards/"
            )
            enrollments = StudentClassEnrollment.objects.filter(
                school=school,
                classroom=submission.classroom,
                academic_year=submission.exam.term.academic_year,
                student__isnull=False,
                student__school=school,
                student__parent_guardian__user__isnull=False,
            ).select_related("student", "student__parent_guardian__user")
            for enrollment in enrollments:
                student = enrollment.student
                parent_user = student.parent_guardian.user
                create_notification(
                    school=school,
                    recipient=parent_user,
                    category=Notification.Category.ACADEMIC,
                    title="Marks have been released",
                    message=(
                        f"{student.full_name}'s {submission.subject.name} marks for "
                        f"{submission.exam.name} are now available in the report card: "
                        f"{report_path}?term_id="
                        f"{submission.exam.term_id}&classroom_id="
                        f"{submission.classroom_id}&student_id={student.pk}"
                    ),
                    idempotency_key=f"marks-release:{event.pk}:{parent_user.pk}",
                )
        return Response(
            {
                **MarksSubmissionSerializer(submission).data,
                "history_entry": event.pk,
            }
        )


class MarksBulkUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            requesting_teacher = request.user.academic_teacher
        except Teacher.DoesNotExist:
            requesting_teacher = None
        if requesting_teacher is None and not request.user.is_staff:
            return Response(
                {"error": "Only teachers or school administrators can import marks."},
                status=status.HTTP_403_FORBIDDEN,
            )

        columns = [
            "exam_name",
            "student_admission_number",
            "classroom_name",
            "stream_name",
            "academic_year",
            "subject_code",
            "points_scored",
            "created_by_emp_id",
        ]
        created_count = 0
        errors = []
        seen_marks = set()
        try:
            for row_number, data in iter_excel_rows(upload, columns):
                try:
                    exam_name = text_value(data["exam_name"])
                    admission_number = text_value(data["student_admission_number"])
                    classroom_name = text_value(data["classroom_name"])
                    stream_name = text_value(data["stream_name"])
                    year_name = text_value(data["academic_year"])
                    subject_key = text_value(data["subject_code"])
                    creator_emp_id = text_value(data["created_by_emp_id"])
                    if not all(
                        (
                            exam_name,
                            admission_number,
                            classroom_name,
                            stream_name,
                            year_name,
                            subject_key,
                        )
                    ):
                        raise ValueError(
                            "Exam, student admission number, classroom, stream, "
                            "academic year, and subject are required."
                        )

                    exam = ExaminationListHandler.objects.get(
                        school=school, name__iexact=exam_name
                    )
                    student = Student.objects.get(
                        school=school, admission_number=admission_number
                    )
                    classroom = ClassRoom.objects.get(
                        school=school,
                        name__name__iexact=classroom_name,
                        stream__name__iexact=stream_name,
                    )
                    academic_year = AcademicYear.objects.get(
                        school=school, name__iexact=year_name
                    )
                    enrollment = StudentClassEnrollment.objects.get(
                        school=school,
                        student=student,
                        classroom=classroom,
                        academic_year=academic_year,
                    )
                    if not exam.classrooms.filter(pk=classroom.pk).exists():
                        raise ValueError(
                            "The exam is not assigned to this student's classroom."
                        )
                    subject = Subject.objects.get(
                        Q(subject_code__iexact=subject_key)
                        | Q(name__iexact=subject_key),
                        school=school,
                    )

                    if requesting_teacher is not None:
                        teacher = requesting_teacher
                    elif creator_emp_id:
                        teacher = Teacher.objects.get(
                            school=school, empId=creator_emp_id
                        )
                    else:
                        raise ValueError(
                            "School administrators must provide created_by_emp_id."
                        )
                    if teacher.school_id != school.pk:
                        raise ValueError(
                            "The selected teacher belongs to another school."
                        )

                    points = decimal_value(data["points_scored"], "Points scored")
                    if not points.is_finite():
                        raise ValueError("Points scored must be a finite number.")
                    key = (exam.pk, enrollment.pk, subject.pk)
                    if key in seen_marks or MarksManagement.objects.filter(
                        school=school,
                        exam_name=exam,
                        student=enrollment,
                        subject=subject,
                    ).exists():
                        raise ValueError("Marks already exist for this exam and subject.")

                    with transaction.atomic():
                        mark = MarksManagement(
                            school=school,
                            exam_name=exam,
                            student=enrollment,
                            subject=subject,
                            points_scored=float(points),
                            created_by=teacher,
                        )
                        mark.full_clean()
                        mark.save()
                    seen_marks.add(key)
                    created_count += 1
                except (
                    ValueError,
                    ObjectDoesNotExist,
                    MultipleObjectsReturned,
                    ValidationError,
                    IntegrityError,
                    OverflowError,
                ) as exc:
                    errors.append(
                        {"row": row_number, "data": data, "error": str(exc)}
                    )

            return Response(
                {
                    "message": f"{created_count} marks successfully uploaded.",
                    "not_created": errors,
                },
                status=status.HTTP_201_CREATED,
            )
        except (
            openpyxl.utils.exceptions.InvalidFileException,
            OSError,
            ValueError,
        ) as exc:
            return Response(
                {"error": f"Invalid Excel file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MarksExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        marks = MarksManagement.objects.filter(school=school).select_related(
            "exam_name",
            "student__student",
            "student__classroom__name",
            "student__classroom__stream",
            "student__academic_year",
            "subject",
            "created_by",
        )
        rows = (
            (
                mark.exam_name.name,
                mark.student.student.admission_number if mark.student.student else "",
                mark.student.classroom.name.name,
                mark.student.classroom.stream.name,
                mark.student.academic_year.name,
                mark.subject.subject_code or mark.subject.name,
                mark.points_scored,
                mark.created_by.empId,
            )
            for mark in marks
        )
        return excel_response(
            "marks.xlsx",
            "Marks",
            [
                "exam_name",
                "student_admission_number",
                "classroom_name",
                "stream_name",
                "academic_year",
                "subject_code",
                "points_scored",
                "created_by_emp_id",
            ],
            rows,
        )
