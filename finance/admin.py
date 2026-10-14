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
        fields = (
            "id",
            "school",
            "payment_number",
            "date",
            "paid_to",
            "user",
            "paid_for",
            "paid_through",
            "amount",
            "status",
            "paid_by",
        )


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
        fields = (
            "id",
            "school",
            "receipt_number",
            "date",
            "payer",
            "paid_for",
            "student",
            "amount",
            "paid_through",
            "term",
            "payment_date",
            "status",
            "received_by",
        )


@admin.register(Receipt)
class ReceiptAdmin(ImportExportModelAdmin):
    resource_class = ReceiptResource
    change_list_template = "admin/import_export/change_list_import_export.html"


# ---------- Allocations (simple) ----------
enable_import_export(PaymentAllocation)
enable_import_export(ReceiptAllocation)