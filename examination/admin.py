from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.http import urlencode

from academic.models import (
    ClassRoom,
    StudentClassEnrollment,
    Subject,
    Teacher,
)
from administration.models import Term
from utils.bulk_imports import decimal_value, get_request_school

from .models import (
    ExaminationListHandler,
    GradeScale,
    GradeScaleRule,
    MarksManagement,
    Result,
)

admin.site.register(GradeScale)
admin.site.register(GradeScaleRule)
admin.site.register(Result)


@admin.register(ExaminationListHandler)
class ExaminationListHandlerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "term",
        "assessment_type",
        "start_date",
        "ends_date",
        "school",
    )
    list_filter = ("assessment_type", "term__academic_year", "school")
    search_fields = ("name", "term__name")
    filter_horizontal = ("classrooms",)


@admin.register(MarksManagement)
class MarksManagementAdmin(admin.ModelAdmin):
    list_display = (
        "exam_name",
        "student",
        "subject",
        "points_scored",
        "created_by",
    )
    list_filter = ("exam_name__term", "exam_name__assessment_type", "subject")
    search_fields = (
        "student__student__admission_number",
        "student__student__first_name",
        "student__student__last_name",
        "subject__name",
    )
    change_list_template = "admin/examination/marksmanagement/change_list.html"

    def get_urls(self):
        custom_urls = [
            path(
                "enter-marks/",
                self.admin_site.admin_view(self.enter_marks_view),
                name="examination_marksmanagement_enter_marks",
            )
        ]
        return custom_urls + super().get_urls()

    def enter_marks_view(self, request):
        if not (
            self.has_add_permission(request) or self.has_change_permission(request)
        ):
            raise PermissionDenied

        school = get_request_school(request)
        if school is None:
            raise PermissionDenied("Your account is not associated with a school.")

        source = request.POST if request.method == "POST" else request.GET

        def selected_object(queryset, key):
            try:
                object_id = int(source.get(key, ""))
            except (TypeError, ValueError):
                return None
            return queryset.filter(pk=object_id).first()

        terms = (
            Term.objects.filter(academic_year__school=school)
            .select_related("academic_year")
            .order_by("-academic_year__start_date", "start_date")
        )
        selected_term = selected_object(terms, "term_id")
        exams = (
            ExaminationListHandler.objects.filter(school=school, term=selected_term)
            .order_by("name")
            if selected_term
            else ExaminationListHandler.objects.none()
        )
        selected_exam = selected_object(exams, "exam_id")
        classrooms = (
            selected_exam.classrooms.filter(school=school)
            .select_related("name", "stream")
            .order_by("name__name", "stream__name")
            if selected_exam
            else ClassRoom.objects.none()
        )
        selected_classroom = selected_object(classrooms, "classroom_id")
        subjects = Subject.objects.filter(school=school).order_by("name")
        selected_subject = selected_object(subjects, "subject_id")
        selected_year = selected_term.academic_year if selected_term else None

        teachers = Teacher.objects.filter(school=school, inactive=False).order_by(
            "first_name", "last_name"
        )
        selected_teacher = selected_object(teachers, "teacher_id")
        if selected_teacher is None:
            selected_teacher = teachers.filter(user=request.user).first()

        errors = []
        entered_scores = {}
        enrollments = []
        enrollment_by_id = {}
        marks_by_enrollment = {}
        duplicates = set()
        if (
            selected_exam
            and selected_classroom
            and selected_subject
            and selected_term
            and selected_year
        ):
            enrollments = list(
                StudentClassEnrollment.objects.filter(
                    school=school,
                    classroom=selected_classroom,
                    academic_year=selected_year,
                    student__isnull=False,
                    student__school=school,
                )
                .select_related("student")
                .order_by(
                    "student__last_name",
                    "student__first_name",
                    "student__admission_number",
                )
            )
            enrollment_by_id = {enrollment.pk: enrollment for enrollment in enrollments}
            existing_marks = MarksManagement.objects.filter(
                school=school,
                exam_name=selected_exam,
                subject=selected_subject,
                student_id__in=[enrollment.pk for enrollment in enrollments],
            ).order_by("pk")
            for mark in existing_marks:
                if mark.student_id in marks_by_enrollment:
                    duplicates.add(mark.student_id)
                else:
                    marks_by_enrollment[mark.student_id] = mark

        if request.method == "POST":
            if not all(
                (
                    selected_term,
                    selected_exam,
                    selected_classroom,
                    selected_subject,
                    selected_year,
                )
            ):
                errors.append(
                    "Select a valid term, exam, class, and subject before saving."
                )
            if not selected_teacher:
                errors.append("Select the teacher responsible for these marks.")
            for enrollment_id in duplicates:
                errors.append(
                    f"{enrollment_by_id[enrollment_id].student} "
                    "has multiple saved marks for this exam and subject. Resolve the duplicate "
                    "records before using the sheet."
                )

            pending_marks = []
            for enrollment in enrollments:
                field_name = f"score_{enrollment.pk}"
                raw_score = str(source.get(field_name, "")).strip()
                entered_scores[enrollment.pk] = raw_score
                if not raw_score:
                    continue

                try:
                    score = decimal_value(raw_score, "Points scored")
                    if (
                        not score.is_finite()
                        or score < 0
                        or score > selected_exam.out_of
                    ):
                        raise ValueError(
                            f"Enter a score from 0 to {selected_exam.out_of}."
                        )
                except ValueError as exc:
                    errors.append(f"{enrollment.student}: {exc}")
                    continue

                mark = marks_by_enrollment.get(enrollment.pk)
                is_update = mark is not None
                if is_update and not self.has_change_permission(request, mark):
                    errors.append(
                        f"You do not have permission to update {enrollment.student}'s mark."
                    )
                    continue
                if not is_update and not self.has_add_permission(request):
                    errors.append(
                        f"You do not have permission to add {enrollment.student}'s mark."
                    )
                    continue
                if mark is None:
                    mark = MarksManagement(
                        school=school,
                        exam_name=selected_exam,
                        subject=selected_subject,
                        student=enrollment,
                    )
                mark.points_scored = float(score)
                mark.created_by = selected_teacher
                try:
                    mark.full_clean()
                except ValidationError as exc:
                    errors.append(f"{enrollment.student}: {exc}")
                    continue
                pending_marks.append(mark)

            if not errors:
                with transaction.atomic():
                    for mark in pending_marks:
                        mark.save()
                messages.success(
                    request,
                    f"Saved marks for {len(pending_marks)} learner(s). "
                    "Blank scores were left unchanged.",
                )
                query = urlencode(
                    {
                        "exam_id": selected_exam.pk,
                        "term_id": selected_term.pk,
                        "classroom_id": selected_classroom.pk,
                        "subject_id": selected_subject.pk,
                        "teacher_id": selected_teacher.pk,
                    }
                )
                return HttpResponseRedirect(
                    f"{reverse('admin:examination_marksmanagement_enter_marks')}?{query}"
                )

            for error in errors:
                messages.error(request, error)

        entry_rows = [
            {
                "enrollment": enrollment,
                "mark": marks_by_enrollment.get(enrollment.pk),
                "score": (
                    entered_scores[enrollment.pk]
                    if enrollment.pk in entered_scores
                    else (
                        marks_by_enrollment[enrollment.pk].points_scored
                        if enrollment.pk in marks_by_enrollment
                        else ""
                    )
                ),
            }
            for enrollment in enrollments
        ]
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Enter marks for a class",
            "exams": exams,
            "terms": terms,
            "selected_term": selected_term,
            "selected_exam": selected_exam,
            "classrooms": classrooms,
            "selected_classroom": selected_classroom,
            "subjects": subjects,
            "selected_subject": selected_subject,
            "selected_year": selected_year,
            "teachers": teachers,
            "selected_teacher": selected_teacher,
            "enrollments": enrollments,
            "entry_rows": entry_rows,
            "marks_by_enrollment": marks_by_enrollment,
            "entered_scores": entered_scores,
            "errors": errors,
            "out_of": selected_exam.out_of if selected_exam else None,
        }
        return render(
            request,
            "admin/examination/marksmanagement/enter_marks.html",
            context,
        )
