from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class SchoolTenant(TenantMixin):
    name = models.CharField(max_length=255)
    school = models.OneToOneField(
        "administration.School",
        on_delete=models.PROTECT,
        related_name="tenant_configuration",
        null=True,
        blank=True,
    )

    auto_create_schema = False

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    pass
