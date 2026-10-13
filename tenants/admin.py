from django.contrib import admin
from django.conf import settings

from .models import Domain, SchoolTenant


@admin.register(SchoolTenant)
class SchoolTenantAdmin(admin.ModelAdmin):
    list_display = ("name", "schema_name", "school")
    search_fields = ("name", "schema_name", "school__name")

    def has_module_permission(self, request):
        return not settings.TENANCY_CONFIGURED and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return not settings.TENANCY_CONFIGURED and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return not settings.TENANCY_CONFIGURED and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return not settings.TENANCY_CONFIGURED and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not settings.TENANCY_CONFIGURED and super().has_delete_permission(request, obj)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("domain", "tenant__name", "tenant__schema_name")

    def has_module_permission(self, request):
        return not settings.TENANCY_CONFIGURED and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return not settings.TENANCY_CONFIGURED and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return not settings.TENANCY_CONFIGURED and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return not settings.TENANCY_CONFIGURED and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not settings.TENANCY_CONFIGURED and super().has_delete_permission(request, obj)
