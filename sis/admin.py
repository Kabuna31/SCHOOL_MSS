from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from academic.models import *


# ---------- Student ----------
class StudentResource(resources.ModelResource):
    school = fields.Field(
        column_name="school",
        attribute="school",
        widget=ForeignKeyWidget(School, field="name"),
    )
    class_level = fields.Field(
        column_name="class_level",
        attribute="class_level",
        widget=ForeignKeyWidget(ClassLevel, field="name"),
    )
    class_of_year = fields.Field(
        column_name="class_of_year",
        attribute="class_of_year",
        widget=ForeignKeyWidget(ClassYear, field="year"),
    )
    parent_guardian = fields.Field(
        column_name="parent_guardian",
        attribute="parent_guardian",
        widget=ForeignKeyWidget(Parent, field="phone_number"),
    )

    class Meta:
        model = Student
        import_id_fields = ("admission_number",)
        fields = (
            "id",
            "school",
            "admission_number",
            "first_name",
            "middle_name",
            "last_name",
            "gender",
            "religion",
            "date_of_birth",
            "graduation_date",
            "class_level",
            "class_of_year",
            "parent_contact",
            "parent_guardian",
            "region",
            "city",
            "street",
            "blood_group",
            "prems_number",
            "std_vii_number",
        )
        export_order = fields

    def before_import_row(self, row, **kwargs):
        # Student.save() raises if parent_contact is missing.
        if not row.get("parent_contact"):
            row["parent_contact"] = "UNKNOWN"
        # Normalise gender (M/F) and religion (lowercase).
        if row.get("gender"):
            row["gender"] = str(row["gender"]).strip().upper()[:1]
        if row.get("religion"):
            row["religion"] = str(row["religion"]).strip().lower()

    def get_queryset(self):
        # Bypass SchoolScopedManager during import/export so all schools' data
        # is visible to superusers, but scope to the logged-in school otherwise.
        return Student.unfiltered_objects.all()


@admin.register(Student)
class StudentAdmin(ImportExportModelAdmin):
    resource_class = StudentResource
    list_display = (
        "admission_number",
        "first_name",
        "middle_name",
        "last_name",
        "class_level",
        "class_of_year",
        "school",
    )
    search_fields = ("admission_number", "first_name", "middle_name", "last_name")
    list_filter = ("school", "class_level", "class_of_year", "gender", "religion")


# ---------- Other models (unchanged) ----------
admin.site.register(ReasonLeft)
admin.site.register(StudentsPreviousAcademicHistory)
admin.site.register(StudentFile)
admin.site.register(StudentHealthRecord)
admin.site.register(FamilyAccessUser)
admin.site.register(Parent)