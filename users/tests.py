from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.middleware.locale import LocaleMiddleware
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import translation
from rest_framework.test import APIRequestFactory, force_authenticate

from administration.models import School
from finance.serializers import PaymentSerializer
from users.models import CustomUser
from users.views import UserDetailView, UserListView


class AdminTranslationCatalogTests(SimpleTestCase):
    def test_admin_javascript_catalog_handles_deactivated_language(self):
        with translation.override("en-us"):
            translation.deactivate_all()
            request = RequestFactory().get("/admin/jsi18n/")
            response = LocaleMiddleware(admin.site.i18n_javascript)(request)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(request.LANGUAGE_CODE, "en")
            self.assertTrue(response["Content-Type"].startswith("text/javascript"))


class SchoolUserVisibilityTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Rockland Secondary", address="Luuka")
        self.other_school = School.objects.create(name="Other School", address="Luuka")
        self.user = CustomUser.objects.create_user(
            email="admin@rockland.test",
            password="test-password",
            school=self.school,
            is_staff=True,
        )
        self.school_user = CustomUser.objects.create_user(
            email="teacher@rockland.test",
            password="test-password",
            school=self.school,
            is_teacher=True,
        )
        self.other_school_user = CustomUser.objects.create_user(
            email="admin@other.test",
            password="test-password",
            school=self.other_school,
            is_staff=True,
        )
        self.factory = APIRequestFactory()

    def request_as_user(self, request, user):
        force_authenticate(request, user=user)
        return request

    def test_user_list_only_returns_users_from_requesting_school(self):
        request = self.request_as_user(self.factory.get("/users/"), self.user)

        response = UserListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {row["email"] for row in response.data},
            {self.user.email, self.school_user.email},
        )

    def test_user_list_never_includes_superusers(self):
        superuser = CustomUser.objects.create_superuser(
            email="root@rockland.test",
            password="test-password",
            school=self.school,
        )
        request = self.request_as_user(self.factory.get("/users/"), self.user)

        response = UserListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            superuser.email,
            {row["email"] for row in response.data},
        )

    def test_user_detail_hides_superusers(self):
        superuser = CustomUser.objects.create_superuser(
            email="root@rockland.test",
            password="test-password",
            school=self.school,
        )
        request = self.request_as_user(
            self.factory.get(f"/users/{superuser.pk}/"), self.user
        )

        response = UserDetailView.as_view()(request, pk=superuser.pk)

        self.assertEqual(response.status_code, 404)

    def test_payment_user_dropdown_excludes_superusers(self):
        superuser = CustomUser.objects.create_superuser(
            email="root@rockland.test",
            password="test-password",
            school=self.school,
        )

        selectable_users = PaymentSerializer().fields["user_id"].queryset

        self.assertFalse(selectable_users.filter(pk=superuser.pk).exists())

    def test_user_detail_cannot_read_another_schools_user(self):
        request = self.request_as_user(
            self.factory.get(f"/users/{self.other_school_user.pk}/"), self.user
        )

        response = UserDetailView.as_view()(request, pk=self.other_school_user.pk)

        self.assertEqual(response.status_code, 404)

    def test_user_creation_assigns_requesting_school(self):
        request = self.request_as_user(
            self.factory.post(
                "/users/",
                {
                    "email": "new-user@rockland.test",
                    "first_name": "New",
                    "last_name": "User",
                },
                format="json",
            ),
            self.user,
        )

        response = UserListView.as_view()(request)

        self.assertEqual(response.status_code, 201, response.data)
        created_user = CustomUser.objects.get(email="new-user@rockland.test")
        self.assertEqual(created_user.school_id, self.school.pk)

    def test_user_list_is_empty_for_accounts_without_a_school(self):
        user_without_school = CustomUser.objects.create_user(
            email="unassigned@test",
            password="test-password",
        )
        request = self.request_as_user(
            self.factory.get("/users/"), user_without_school
        )

        response = UserListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])


class GroupPermissionAdminTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_superuser(
            email="superuser@test",
            password="test-password",
        )
        self.client.force_login(self.admin_user)

    def test_group_permissions_use_selectable_checkboxes(self):
        request = RequestFactory().get("/admin/auth/group/add/")
        request.user = self.admin_user
        form_class = admin.site._registry[Group].get_form(request)

        self.assertIsInstance(
            form_class.base_fields["permissions"].widget.widget,
            forms.CheckboxSelectMultiple,
        )

    def test_group_admin_saves_selected_permissions(self):
        permission = Permission.objects.first()
        self.assertIsNotNone(permission)
        request = RequestFactory().get("/admin/auth/group/add/")
        request.user = self.admin_user
        form_class = admin.site._registry[Group].get_form(request)
        form = form_class(
            data={
                "name": "School operators",
                "permissions": [permission.pk],
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        group = form.save()
        self.assertTrue(group.permissions.filter(pk=permission.pk).exists())
