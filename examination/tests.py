from datetime import date

from django.urls import reverse
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from academic.models import (
    ClassLevel,
    ClassRoom,
    Stream,
    Student,
    StudentClassEnrollment,
    Subject,
    Teacher,
)
from administration.models import AcademicYear, School, Term
from users.models import CustomUser

from .models import ExaminationListHandler, MarksManagement
from .reports import _class_band, _grade_for, build_class_report


@override_settings(SECURE_SSL_REDIRECT=False)
class ClassReportsTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Rockland Secondary School",
            address="Iganga",
            telephone="0700000000",
            school_email="office@example.test",
        )
        self.user = CustomUser.objects.create_user(
            email="admin@example.test",
            password="test-password",
            phone_number="1000001",
            school=self.school,
            is_staff=True,
        )
        self.teacher = Teacher.objects.create(
            school=self.school,
            user=self.user,
            first_name="Class",
            last_name="Teacher",
            empId="T001",
        )
        self.academic_year = AcademicYear.objects.create(
            school=self.school,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            active_year=True,
        )
        self.term = Term.objects.create(
            name="Term Two",
            academic_year=self.academic_year,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 8, 31),
        )
        self.class_level = ClassLevel.objects.create(
            school=self.school,
            name="Senior One",
        )
        self.stream = Stream.objects.create(school=self.school, name="A")
        self.classroom = ClassRoom.objects.create(
            school=self.school,
            name=self.class_level,
            stream=self.stream,
            class_teacher=self.teacher,
        )
        self.student = Student.objects.create(
            school=self.school,
            first_name="Alex",
            last_name="Learner",
            admission_number="S001",
            parent_contact="1000002",
        )
        self.enrollment = StudentClassEnrollment.objects.create(
            school=self.school,
            classroom=self.classroom,
            academic_year=self.academic_year,
            student=self.student,
        )
        self.subject = Subject.objects.create(
            school=self.school,
            name="Mathematics",
            subject_code="MATH",
        )
        self.aoi = self.make_exam("AOI one", "AOI")
        self.eot = self.make_exam("End of term", "EOT")
        self.add_mark(self.aoi, 80)
        self.add_mark(self.eot, 70)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def make_exam(self, name, assessment_type):
        exam = ExaminationListHandler.objects.create(
            school=self.school,
            name=name,
            term=self.term,
            assessment_type=assessment_type,
            start_date=date(2026, 6, 1),
            ends_date=date(2026, 6, 2),
            out_of=100,
            created_by=self.teacher,
        )
        exam.classrooms.add(self.classroom)
        return exam

    def add_mark(self, exam, score):
        return MarksManagement.objects.create(
            school=self.school,
            exam_name=exam,
            points_scored=score,
            subject=self.subject,
            student=self.enrollment,
            created_by=self.teacher,
        )

    def report_url(self, name):
        return reverse(name) + f"?term_id={self.term.pk}&classroom_id={self.classroom.pk}"

    def test_report_card_and_marksheet_return_printable_pdfs(self):
        for endpoint in ("report-cards", "marksheet"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(self.report_url(endpoint))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "application/pdf")
                self.assertTrue(response.content.startswith(b"%PDF"))

    def test_mid_term_report_card_uses_aoi_marks_only(self):
        response = self.client.get(self.report_url("mid-term-report-cards"))
        report_data = build_class_report(
            self.school,
            self.term,
            self.classroom,
            mid_term=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertEqual(report_data["students"][0]["average"], 80)
        self.assertEqual(report_data["students"][0]["subjects"][0]["grade"], "A")

    def test_analysis_applies_aoi_and_eot_weighting_and_o_level_grade_bands(self):
        response = self.client.get(self.report_url("result-analysis"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["level"], "O-Level")
        self.assertEqual(response.data["weighting"], {"AOI": 20, "EOT": 80})
        self.assertEqual(response.data["class_average"], 72)
        self.assertEqual(response.data["subjects"][0]["average"], 72)
        self.assertEqual(response.data["subjects"][0]["grade_counts"], {"B": 1})
        self.assertEqual(response.data["ranked_students"][0]["rank"], 1)

    def test_a_level_grade_bands_match_the_example(self):
        self.assertEqual(_class_band("Senior Five"), "A")
        self.assertEqual(_class_band("S.6"), "A")
        self.assertEqual(_grade_for(65, "A"), "C3")
        self.assertEqual(_grade_for(39, "A"), "F9")

    def test_classroom_from_another_school_is_not_exposed(self):
        another_school = School.objects.create(
            name="Another School",
            address="Elsewhere",
        )
        other_level = ClassLevel.objects.create(
            school=another_school,
            name="Senior One",
        )
        other_stream = Stream.objects.create(school=another_school, name="B")
        other_classroom = ClassRoom.objects.create(
            school=another_school,
            name=other_level,
            stream=other_stream,
            class_teacher=self.teacher,
        )

        response = self.client.get(
            reverse("result-analysis"),
            {"term_id": self.term.pk, "classroom_id": other_classroom.pk},
        )

        self.assertEqual(response.status_code, 404)

    def test_subjects_need_both_assessment_categories_for_a_final_score(self):
        self.eot.delete()

        response = self.client.get(self.report_url("result-analysis"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["class_average"])
        self.assertEqual(response.data["subjects"][0]["students_completed"], 0)

    def test_marks_from_exams_not_assigned_to_the_class_are_excluded(self):
        other_class_exam = self.make_exam("Other class exam", "EOT")
        other_class_exam.classrooms.clear()
        self.add_mark(other_class_exam, 100)

        response = self.client.get(self.report_url("result-analysis"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["class_average"], 72)
