from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.db import models

from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Accountant


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin):
    filter_horizontal = ()
    formfield_overrides = {
        models.ManyToManyField: {"widget": forms.CheckboxSelectMultiple},
    }


# ---------- CustomUser import/export ----------
class CustomUserResource(resources.ModelResource):
    """
    Resource for bulk import/export of users.
    NOTE: Passwords are exported hashed. When importing, leave `password` blank
    to create an unusable password, or the user can reset it later.
    """
    school = fields.Field(
        column_name="school",
        attribute="school",
        widget=ForeignKeyWidget(
            CustomUser._meta.get_field("school").related_model,
            field="name",
        ),
    )

    class Meta:
        model = CustomUser
        import_id_fields = ("email",)
        fields = (
            "id",
            "email",
            "first_name",
            "middle_name",
            "last_name",
            "school",
            "is_staff",
            "is_active",
            "is_superuser",
            "is_accountant",
            "is_teacher",
            "is_parent",
        )
        export_order = fields

    def before_import_row(self, row, **kwargs):
        # Don't import hashed passwords via CSV — mark them unusable.
        row["password"] = ""

    def after_init_instance(self, instance, new, row, **kwargs):
        # New users get an unusable password; admin can reset via the UI.
        if new and not instance.password:
            instance.set_unusable_password()


@admin.register(CustomUser)
class CustomUserAdmin(ImportExportModelAdmin, UserAdmin):
    resource_class = CustomUserResource
    change_list_template = "admin/import_export/change_list_import_export.html"

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = (
        "email",
        "first_name",
        "last_name",
        "school",
        "is_staff",
        "is_active",
        "is_accountant",
        "is_teacher",
        "is_parent",
    )
    list_filter = (
        "school",
        "is_staff",
        "is_active",
        "is_accountant",
        "is_teacher",
        "is_parent",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "first_name",
                    "middle_name",
                    "last_name",
                    "email",
                    "password",
                )
            },
        ),
        ("School Assignment", {"fields": ("school",)}),
        (
            "Permissions & Roles",
            {
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "is_accountant",
                    "is_teacher",
                    "is_parent",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "middle_name",
                    "last_name",
                    "email",
                    "password1",
                    "password2",
                    "school",
                    "is_staff",
                    "is_active",
                    "is_accountant",
                    "is_teacher",
                    "is_parent",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )

    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    filter_horizontal = ("groups", "user_permissions")


# ---------- Accountant import/export ----------
class AccountantResource(resources.ModelResource):
    school = fields.Field(
        column_name="school",
        attribute="school",
        widget=ForeignKeyWidget(
            Accountant._meta.get_field("school").related_model,
            field="name",
        ),
    )
    user = fields.Field(
        column_name="user",
        attribute="user",
        widget=ForeignKeyWidget(CustomUser, field="email"),
    )

    class Meta:
        model = Accountant
        import_id_fields = ("empId",)
        fields = (
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "email",
            "school",
            "empId",
            "salary",
            "inactive",
            "gender",
            "tin_number",
            "user",
        )


@admin.register(Accountant)
class AccountantAdmin(ImportExportModelAdmin):
    resource_class = AccountantResource
    change_list_template = "admin/import_export/change_list_import_export.html"
    list_display = (
        "first_name",
        "last_name",
        "email",
        "school",
        "empId",
        "salary",
        "inactive",
    )
    list_filter = ("school", "inactive", "gender")
    search_fields = ("first_name", "last_name", "email", "empId", "tin_number")
    autocomplete_fields = ("user",)
    ordering = ("first_name", "last_name")