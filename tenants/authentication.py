from django.core.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


def ensure_tenant_membership(user, request):
    django_request = getattr(request, "_request", request)
    tenant = getattr(django_request, "tenant", None)
    if (
        tenant is None
        or tenant.schema_name == "public"
        or user.is_superuser
    ):
        return

    if tenant.school_id is None or user.school_id != tenant.school_id:
        raise PermissionDenied("Your account is not a member of this school.")


class SchoolJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, token = result
        ensure_tenant_membership(user, request)
        django_request = getattr(request, "_request", request)
        django_request.user = user
        return user, token
