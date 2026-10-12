from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Accountant


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ('email', 'is_staff', 'is_active', 'is_accountant', 'is_teacher',)
    list_filter = ('email', 'is_staff', 'is_active', 'is_accountant', 'is_teacher',)
    
    # Include groups and permissions here
    fieldsets = (
        (None, {'fields': ('first_name', 'middle_name', 'last_name', 'email', 'password')}),
        ('Permissions & Roles', {'fields': ('is_staff', 'is_active', 'is_superuser', 'is_accountant', 'is_teacher', 'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'middle_name', 'last_name', 'email', 'password1', 'password2', 'is_staff', 'is_active', 'is_accountant', 'is_teacher', 'groups', 'user_permissions')}
        ),
    )
    
    search_fields = ('email',)
    ordering = ('email',)
    
    # Gives you a clean side-by-side selection widget for groups
    filter_horizontal = ('groups', 'user_permissions',)


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Accountant)