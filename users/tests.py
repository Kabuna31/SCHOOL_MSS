from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from administration.models import School
from users.models import CustomUser
from users.views import UserDetailView, UserListView


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
