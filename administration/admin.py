from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from .models import *
from school.admin_utils import enable_import_export


# ---------- Simple models: one-line import/export ----------
enable_import_export(Article)
enable_import_export(CarouselImage)
enable_import_export(School)
enable_import_export(Day)
enable_import_export(AcademicYear)
enable_import_export(Term)


# ---------- SchoolEvent (has a custom admin already) ----------
class SchoolEventResource(resources.ModelResource):
    term = fields.Field(
        column_name="term",
        attribute="term",
        widget=ForeignKeyWidget(Term, field="name"),
    )

    class Meta:
        model = SchoolEvent
        import_id_fields = ("id",)
        fields = (
            "id",
            "name",
            "event_type",
            "term",
            "start_date",
            "end_date",
            "description",
        )
        export_order = fields


@admin.register(SchoolEvent)
class SchoolEventAdmin(ImportExportModelAdmin):
    resource_class = SchoolEventResource
    change_list_template = "admin/import_export/change_list_import_export.html"
    list_display = ("name", "event_type", "term", "start_date", "end_date")
    list_filter = ("event_type", "term__academic_year")
    search_fields = ("name", "description")