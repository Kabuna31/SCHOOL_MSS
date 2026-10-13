from django.contrib import admin
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
