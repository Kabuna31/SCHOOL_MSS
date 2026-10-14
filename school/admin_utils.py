from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin


def enable_import_export(model):
    """
    Register a model with ImportExportModelAdmin in one line.
    Safe to call multiple times — replaces any existing registration.
    """
    # Unregister if already registered
    if model in admin.site._registry:
        admin.site.unregister(model)

    # Build a Resource class for this model
    resource_class = type(
        f"{model.__name__}Resource",
        (resources.ModelResource,),
        {
            "__module__": "school.admin_utils",
            "Meta": type(
                "Meta",
                (),
                {
                    "model": model,
                    "fields": "__all__",
                },
            ),
        },
    )

    # Build an Admin class for this model
    admin_class = type(
        f"{model.__name__}Admin",
        (ImportExportModelAdmin,),
        {
            "__module__": "school.admin_utils",
            "resource_class": resource_class,
            "change_list_template": "admin/import_export/change_list_import_export.html",
        },
    )

    admin.site.register(model, admin_class)