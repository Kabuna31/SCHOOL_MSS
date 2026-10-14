from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from .models import ReceiptAllocation, Receipt, PaymentAllocation, Payment
from school.admin_utils import enable_import_export


# ---------- Payment ----------
class PaymentResource(resources.ModelResource):
    school = fields.Field(
        column_name="school",
        attribute="school",
        widget=ForeignKeyWidget(
            Payment._meta.get_field("school").related_model,
            field="name",
        ),
    )

    class Meta:
        model = Payment
        import_id_fields = ("id",)
        fields = "__all__"
        export_order = fields


@admin.register(Payment)
class PaymentAdmin(ImportExportModelAdmin):
    resource_class = PaymentResource
    change_list_template = "admin/import_export/change_list_import_export.html"


# ---------- Receipt ----------
class ReceiptResource(resources.ModelResource):
    school = fields.Field(
        column_name="school",
        attribute="school",
        widget=ForeignKeyWidget(
            Receipt._meta.get_field("school").related_model,
            field="name",
        ),
    )

    class Meta:
        model = Receipt
        import_id_fields = ("id",)
        fields = "__all__"
        export_order = fields


@admin.register(Receipt)
class ReceiptAdmin(ImportExportModelAdmin):
    resource_class = ReceiptResource
    change_list_template = "admin/import_export/change_list_import_export.html"


# ---------- PaymentAllocation ----------
class PaymentAllocationResource(resources.ModelResource):
    class Meta:
        model = PaymentAllocation
        import_id_fields = ("id",)
        fields = "__all__"


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(ImportExportModelAdmin):
    resource_class = PaymentAllocationResource
    change_list_template = "admin/import_export/change_list_import_export.html"


# ---------- ReceiptAllocation ----------
class ReceiptAllocationResource(resources.ModelResource):
    class Meta:
        model = ReceiptAllocation
        import_id_fields = ("id",)
        fields = "__all__"


@admin.register(ReceiptAllocation)
class ReceiptAllocationAdmin(ImportExportModelAdmin):
    resource_class = ReceiptAllocationResource
    change_list_template = "admin/import_export/change_list_import_export.html"