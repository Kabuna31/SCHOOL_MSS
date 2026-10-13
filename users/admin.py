from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.models import Group
from django.db import models
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, Accountant


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin):
    filter_horizontal = ()
    formfield_overrides = {
        models.ManyToManyField: {"widget": forms.CheckboxSelectMultiple},
    }


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'school', 'is_staff', 'is_active', 'is_accountant', 'is_teacher', 'is_parent')
    list_filter = ('school', 'is_staff', 'is_active', 'is_accountant', 'is_teacher', 'is_parent')
    
    # Include school, groups, and permissions here
    fieldsets = (
        (None, {'fields': ('first_name', 'middle_name', 'last_name', 'email', 'password')}),
        ('School Assignment', {'fields': ('school',)}),
        ('Permissions & Roles', {'fields': ('is_staff', 'is_active', 'is_superuser', 'is_accountant', 'is_teacher', 'is_parent', 'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'middle_name', 'last_name', 'email', 'password1', 'password2', 'school', 'is_staff', 'is_active', 'is_accountant', 'is_teacher', 'is_parent', 'groups', 'user_permissions')}
        ),
    )
    
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    # Gives you a clean side-by-side selection widget for groups
    filter_horizontal = ('groups', 'user_permissions',)


@admin.register(Accountant)
class AccountantAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'school', 'empId', 'salary', 'inactive')
    list_filter = ('school', 'inactive', 'gender')
    search_fields = ('first_name', 'last_name', 'email', 'empId', 'tin_number')
    autocomplete_fields = ('user',)
    ordering = ('first_name', 'last_name')


admin.site.register(CustomUser, CustomUserAdmin)