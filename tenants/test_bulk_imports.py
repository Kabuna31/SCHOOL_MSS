from datetime import date
from io import BytesIO

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook
from openpyxl import load_workbook
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate
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
    ClassRoomsExportView,
    StudentClassesExportView,
    SubjectsExportView,
)
from administration.models import AcademicYear, School, SchoolEvent, Term
from administration.views import SchoolEventBulkUploadView
from administration.views import SchoolEventExportView
from examination.models import ExaminationListHandler, MarksManagement
from examination.views import MarksBulkUploadView, MarksExportView
from finance.models import Receipt, ReceiptAllocation
from finance.views import ReceiptBulkUploadView, ReceiptsExportView
from sis.views import BulkUploadStudentsView
from sis.views import StudentsExportView
from tenants.authentication import ensure_tenant_membership
from users.models import CustomUser
from users.views import (
    BulkUploadTeachersView,
    BulkUploadUsersView,
    TeachersExportView,
    UsersExportView,
)
from utils.bulk_imports import excel_response, iter_excel_rows
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

    def export(self, view):
        request = self.factory.get("/export/")
        force_authenticate(request, user=self.user)
        return CurrentRequestMiddleware(view)(request)

    def workbook_rows(self, response):
        workbook = load_workbook(BytesIO(response.content), read_only=True)
        try:
            return list(workbook.active.iter_rows(values_only=True))
        finally:
            workbook.close()

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

        exam = ExaminationListHandler.objects.create(
            school=self.school,
            name="Midyear",
            start_date=date(2026, 2, 1),
            ends_date=date(2026, 2, 28),
            out_of=100,
            created_by=teacher,
        )
        exam.classrooms.add(classroom)
        marks_response = self.upload(
            MarksBulkUploadView.as_view(),
            self.workbook_file(
                [
                    "exam_name",
                    "student_admission_number",
                    "classroom_name",
                    "stream_name",
                    "academic_year",
                    "subject_code",
                    "points_scored",
                    "created_by_emp_id",
                ],
                [
                    [
                        exam.name,
                        student.admission_number,
                        class_level.name,
                        stream.name,
                        year.name,
                        "BIO",
                        85,
                        teacher.empId,
                    ]
                ],
            ),
        )
        self.assertEqual(marks_response.status_code, 201, marks_response.data)
        self.assertEqual(MarksManagement.objects.get().school_id, self.school.pk)

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

        user_import_response = self.upload(
            BulkUploadUsersView.as_view(),
            self.workbook_file(
                ["email", "first_name", "middle_name", "last_name"],
                [["clerk@rockland.test", "Chris", "", "Clerk"]],
            ),
        )
        self.assertEqual(
            user_import_response.status_code, 201, user_import_response.data
        )
        imported_user = CustomUser.objects.get(email="clerk@rockland.test")
        self.assertEqual(imported_user.school_id, self.school.pk)
        self.assertFalse(imported_user.has_usable_password())
        self.assertFalse(imported_user.is_staff)
        self.assertFalse(imported_user.is_teacher)

    def test_exports_cover_bulk_import_data_and_are_school_scoped(self):
        other_school = School.objects.create(name="Other School", address="Elsewhere")
        CustomUser.objects.create_user(
            email="other@other.test",
            password="test-password",
            school=other_school,
            is_staff=True,
        )
        department = Department.objects.create(school=self.school, name="science")
        subject = Subject.objects.create(
            school=self.school,
            name="biology",
            subject_code="BIO",
            department=department,
        )
        class_level = ClassLevel.objects.create(school=self.school, name="Senior 1")
        stream = Stream.objects.create(school=self.school, name="NORTH")
        teacher = Teacher.objects.create(
            school=self.school,
            first_name="Jane",
            last_name="Doe",
            empId="T001",
            short_name="JD",
            email="jane.doe@rockland.test",
        )
        teacher.user.set_unusable_password()
        teacher.user.save(update_fields=["password"])
        classroom = ClassRoom.objects.create(
            school=self.school,
            name=class_level,
            stream=stream,
            class_teacher=teacher,
        )
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
        student = Student.objects.create(
            school=self.school,
            first_name="Mary",
            last_name="Doe",
            admission_number="S001",
            parent_contact="0700111222",
            class_level=class_level,
        )
        student.parent_guardian.user.set_unusable_password()
        student.parent_guardian.user.save(update_fields=["password"])
        enrollment = StudentClassEnrollment.objects.create(
            school=self.school,
            student=student,
            classroom=classroom,
            academic_year=year,
        )
        exam = ExaminationListHandler.objects.create(
            school=self.school,
            name="Midyear",
            start_date=date(2026, 2, 1),
            ends_date=date(2026, 2, 28),
            out_of=100,
            created_by=teacher,
        )
        exam.classrooms.add(classroom)
        MarksManagement.objects.create(
            school=self.school,
            exam_name=exam,
            student=enrollment,
            subject=subject,
            points_scored=85,
            created_by=teacher,
        )
        allocation = ReceiptAllocation.objects.create(
            school=self.school, name="Tuition"
        )
        Receipt.objects.create(
            school=self.school,
            payer="Parent",
            paid_for=allocation,
            student=student,
            amount=250000,
            term=term,
            payment_date=date(2026, 2, 1),
        )
        SchoolEvent.objects.create(
            name="Midterm",
            event_type="exam",
            term=term,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 3),
        )

        for view in (
            UsersExportView.as_view(),
            TeachersExportView.as_view(),
            SubjectsExportView.as_view(),
            ClassRoomsExportView.as_view(),
            StudentsExportView.as_view(),
            StudentClassesExportView.as_view(),
            ReceiptsExportView.as_view(),
            SchoolEventExportView.as_view(),
            MarksExportView.as_view(),
        ):
            with self.subTest(view=view.view_class.__name__):
                response = self.export(view)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    response["Content-Disposition"].startswith("attachment;")
                )
                rows = self.workbook_rows(response)
                if view.view_class is UsersExportView:
                    self.assertGreaterEqual(len(rows), 2)
                    exported_emails = {row[0] for row in rows[1:]}
                    self.assertNotIn("other@other.test", exported_emails)
                else:
                    self.assertEqual(len(rows), 2)

    def test_excel_rows_skip_empty_lines_and_pad_short_rows(self):
        upload = self.workbook_file(
            ["one", "two", "three"],
            [["value", None]],
        )
        self.assertEqual(
            list(iter_excel_rows(upload, ["one", "two", "three"])),
            [(2, {"one": "value", "two": None, "three": None})],
        )

    def test_bulk_operation_routes_are_registered(self):
        expected_paths = {
            "users-bulk-upload": "/api/users/users/bulk-upload/",
            "users-export": "/api/users/users/export/",
            "teacher-bulk-upload": "/api/users/teachers/bulk-upload/",
            "teachers-export": "/api/users/teachers/export/",
            "subject-bulk-upload": "/api/academic/subjects/bulk-upload/",
            "subject-export": "/api/academic/subjects/export/",
            "bulk-upload-classrooms": "/api/academic/classrooms/bulk-upload/",
            "classrooms-export": "/api/academic/classrooms/export/",
            "student-class-bulk-upload": "/api/academic/student-classes/bulk-upload/",
            "student-classes-export": "/api/academic/student-classes/export/",
            "students-export": "/api/sis/students/export/",
            "receipt-bulk-upload": "/api/finance/receipts/bulk-upload/",
            "receipt-export": "/api/finance/receipts/export/",
            "school-events-bulk-upload": "/api/administration/school-events/bulk-upload/",
            "school-events-export": "/api/administration/school-events/export/",
            "marks-bulk-upload": "/api/examination/marks/bulk-upload/",
            "marks-export": "/api/examination/marks/export/",
        }
        for route_name, expected_path in expected_paths.items():
            with self.subTest(route=route_name):
                self.assertEqual(reverse(route_name), expected_path)

    def test_exported_user_values_are_written_as_text(self):
        response = excel_response(
            "safe.xlsx", "Data", ["value"], [("=1+1",)]
        )

        workbook = load_workbook(BytesIO(response.content), read_only=False)
        try:
            cell = workbook.active["A2"]
            self.assertEqual(cell.value, "=1+1")
            self.assertEqual(cell.data_type, "s")
        finally:
            workbook.close()

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
