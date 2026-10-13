from django.core.exceptions import PermissionDenied

from tenants.authentication import ensure_tenant_membership


class TenantMembershipMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            ensure_tenant_membership(user, request)
        return self.get_response(request)
