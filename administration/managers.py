# administration/managers.py
from django.db import models
from utils.middleware import get_current_request

class SchoolScopedManager(models.Manager):
    """
    Automatically scopes queries to the logged-in user's school.
    Superusers bypass this to see all data.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        request = get_current_request()
        
        if not request or not hasattr(request, 'user'):
            return qs
            
        user = request.user
        if not user.is_authenticated:
            return qs.none()
            
        if user.is_superuser:
            return qs
            
        if hasattr(user, 'school') and user.school:
            return qs.filter(school=user.school)
            
        return qs.none()