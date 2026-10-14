from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin


def enable_import_export(model, admin_class=None):
    """
    Register a model with ImportExportModelAdmin in one line.
    Usage: enable_import_export(MarksManagement)
    """
    if admin.site._registry.get(model):
        admin.site.unregister(model)

    resource_class = type(
        f"{model.__name__}Resource",
        (resources.ModelResource,),
        {"Meta": type("Meta", (), {"model": model})},
    )

    admin_cls = type(
        f"{model.__name__}Admin",
        (ImportExportModelAdmin,),
        {
            "resource_class": resource_class,
            "change_list_template": "admin/import_export/change_list_import_export.html",
        },
    )

    admin.site.register(model, admin_cls)