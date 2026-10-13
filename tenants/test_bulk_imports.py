from datetime import date
from io import BytesIO

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken

from academic.models import (
    ClassLevel,
    ClassRoom,
    Department,
    Stream,
    Student,
    StudentClassEnrollment,
    Subject,
    Teacher,
)
from academic.views import (
    BulkUploadClassRoomsView,
    BulkUploadStudentClassView,
    BulkUploadSubjectsView,
)
from administration.models import AcademicYear, School, SchoolEvent, Term
from administration.views import SchoolEventBulkUploadView
from finance.models import Receipt, ReceiptAllocation
from finance.views import ReceiptBulkUploadView
from sis.views import BulkUploadStudentsView
from tenants.authentication import ensure_tenant_membership
from users.models import CustomUser
from users.views import BulkUploadTeachersView
from utils.bulk_imports import iter_excel_rows
from utils.middleware import CurrentRequestMiddleware


class BulkImportIntegrationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Rockland Secondary School", address="Luuka")
        self.user = CustomUser.objects.create_user(
            email="admin@rockland.test",
            password="Strong-password-21",
            school=self.school,
            is_staff=True,
        )
        self.factory = APIRequestFactory()

    def workbook_file(self, columns, values):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(columns)
        for row in values:
            worksheet.append(row)
        output = BytesIO()
        workbook.save(output)
        return SimpleUploadedFile(
            "import.xlsx",
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def upload(self, view, file):
        token = AccessToken.for_user(self.user)
        request = self.factory.post(
            "/upload/",
            {"file": file},
            format="multipart",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        return CurrentRequestMiddleware(view)(request)

    def test_all_excel_importers_write_to_the_request_school(self):
        department = Department.objects.create(school=self.school, name="science")
        class_level = ClassLevel.objects.create(school=self.school, name="Senior 1")
        stream = Stream.objects.create(school=self.school, name="NORTH")
        year = AcademicYear.objects.create(
            school=self.school,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            active_year=False,
        )
        term = Term.objects.create(
            name="Term 1",
            academic_year=year,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 4, 30),
        )
        allocation = ReceiptAllocation.objects.create(
            school=self.school, name="Tuition"
        )

        teacher_response = self.upload(
            BulkUploadTeachersView.as_view(),
            self.workbook_file(
                ["first_name", "middle_name", "last_name", "phone_number", "employment_id", "short_name", "subject_specialization", "address", "gender", "date_of_birth", "salary"],
                [["Jane", "A", "Doe", "0712345678", "T001", "JD", "", "Luuka", "Female", date(1990, 1, 1), 900000]],
            ),
        )
        self.assertEqual(teacher_response.status_code, 201, teacher_response.data)
        teacher = Teacher.objects.get(school=self.school, empId="T001")
        self.assertEqual(teacher.user.school_id, self.school.pk)
        self.assertFalse(teacher.user.has_usable_password())

        subject_response = self.upload(
            BulkUploadSubjectsView.as_view(),
            self.workbook_file(
                ["name", "subject_code", "department"],
                [["Biology", "BIO", department.name]],
            ),
        )
        self.assertEqual(subject_response.status_code, 201, subject_response.data)
        subject = Subject.objects.get(school=self.school, subject_code="BIO")
        self.assertEqual(subject.department_id, department.pk)

        classroom_response = self.upload(
            BulkUploadClassRoomsView.as_view(),
            self.workbook_file(
                ["name", "stream", "class_teacher"],
                [[class_level.name, stream.name, "Jane Doe"]],
            ),
        )
        self.assertEqual(classroom_response.status_code, 201, classroom_response.data)
        classroom = ClassRoom.objects.get(school=self.school)

        student_response = self.upload(
            BulkUploadStudentsView.as_view(),
            self.workbook_file(
                ["first_name", "middle_name", "last_name", "admission_number", "parent_contact", "religion", "class_level", "gender"],
                [["Mary", "", "Doe", "S001", "0700111222", "Christian", class_level.name, "Female"]],
            ),
        )
        self.assertEqual(student_response.status_code, 201, student_response.data)
        student = Student.objects.get(school=self.school, admission_number="S001")
        self.assertEqual(student.parent_guardian.school_id, self.school.pk)
        self.assertFalse(student.parent_guardian.user.has_usable_password())

        enrollment_response = self.upload(
            BulkUploadStudentClassView.as_view(),
            self.workbook_file(
                ["classroom_name", "stream_name", "academic_year", "student_full_name"],
                [[class_level.name, stream.name, year.name, "Mary Doe"]],
            ),
        )
        self.assertEqual(enrollment_response.status_code, 201, enrollment_response.data)
        self.assertEqual(StudentClassEnrollment.objects.get().school_id, self.school.pk)
        classroom.refresh_from_db()
        self.assertEqual(classroom.occupied_sits, 1)

        receipt_response = self.upload(
            ReceiptBulkUploadView.as_view(),
            self.workbook_file(
                ["payer", "first_name", "middle_name", "last_name", "paid_for", "paid_through", "payment_date", "term", "amount"],
                [["Parent", "Mary", "", "Doe", allocation.name, "CASH", date(2026, 2, 1), "Term 1-2026", 250000]],
            ),
        )
        self.assertEqual(receipt_response.status_code, 201, receipt_response.data)
        self.assertEqual(Receipt.objects.get().school_id, self.school.pk)

        event_response = self.upload(
            SchoolEventBulkUploadView.as_view(),
            self.workbook_file(
                ["name", "event_type", "term_id", "start_date", "end_date", "description"],
                [["Midterm", "exam", term.pk, date(2026, 2, 1), date(2026, 2, 3), "Exams"]],
            ),
        )
        self.assertEqual(event_response.status_code, 201, event_response.data)
        self.assertEqual(SchoolEvent.objects.get().term_id, term.pk)

    def test_excel_rows_skip_empty_lines_and_pad_short_rows(self):
        upload = self.workbook_file(
            ["one", "two", "three"],
            [["value", None]],
        )
        self.assertEqual(
            list(iter_excel_rows(upload, ["one", "two", "three"])),
            [(2, {"one": "value", "two": None, "three": None})],
        )

    def test_tenant_access_rejects_another_schools_user(self):
        other_school = School.objects.create(name="Other School", address="Luuka")
        tenant = type(
            "Tenant",
            (),
            {"schema_name": "rockland", "school_id": self.school.pk},
        )()
        request = type("Request", (), {"tenant": tenant})()

        with self.assertRaisesMessage(
            PermissionDenied, "Your account is not a member of this school."
        ):
            ensure_tenant_membership(
                CustomUser.objects.create_user(
                    email="other@school.test", password="Another-password-21", school=other_school
                ),
                request,
            )
