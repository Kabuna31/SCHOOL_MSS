# school/admin_mixins.py

class SchoolIsolationAdminMixin:
    """
    Automatically filters Django Admin querysets by the logged-in user's school.
    Superusers see everything; staff see only their assigned school's data.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or not request.user.school:
            return qs
        
        # Filter by school if the model has a 'school' field
        if hasattr(qs.model, 'school'):
            return qs.filter(school=request.user.school)
        return qs

    def save_model(self, request, obj, form, change):
        # Auto-assign the user's school to new records if not a superuser
        if not change and hasattr(obj, 'school') and not obj.school and request.user.school:
            obj.school = request.user.school
        super().save_model(request, obj, form, change)