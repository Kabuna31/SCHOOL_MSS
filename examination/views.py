import openpyxl
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from academic.models import (
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
from .reports import (
    analysis_payload,
    analysis_pdf,
    build_class_report,
    marksheet_pdf,
    report_cards_pdf,
    report_scope,
)


class ClassReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get_report_data(self, request, mid_term=False):
        school, term, classroom, student_id = report_scope(request)
        return build_class_report(school, term, classroom, student_id, mid_term)


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
