# administration/managers.py
from django.db import models
from utils.middleware import get_current_request


class SchoolScopedManager(models.Manager):
    """
    Restricts tenant-schema queries to that tenant's school.
    In the legacy shared schema, queries are scoped to the logged-in user's school.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        from django.db import connection

        tenant = getattr(connection, "tenant", None)
        if tenant is not None and tenant.schema_name != "public":
            tenant_school_id = getattr(tenant, "school_id", None)
            if tenant_school_id is not None:
                return qs.filter(school_id=tenant_school_id)

        request = get_current_request()

        if not request or not hasattr(request, 'user'):
            return qs

        user = request.user
        if not user.is_authenticated:
            return qs.none()

        if user.is_superuser:
            return qs

        if hasattr(user, 'school') and user.school:
            return qs.filter(school_id=user.school_id)

        return qs.none()