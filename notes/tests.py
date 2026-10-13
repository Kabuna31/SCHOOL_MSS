from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APITestCase

from academic.models import Parent, Student
from administration.models import School
from users.models import CustomUser

from .models import Assignment, Choice, GradedAssignment, Question


@override_settings(SECURE_SSL_REDIRECT=False)
class GradedAssignmentSubmissionTests(APITestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Example School",
            address="Example address",
        )
        self.parent_user = CustomUser.objects.create_user(
            email="parent@example.test",
            password="test-password",
            phone_number="1000001",
            school=self.school,
            is_parent=True,
        )
        self.parent = Parent.objects.create(
            school=self.school,
            first_name="Parent",
            last_name="One",
            email="parent@example.test",
            phone_number="1000001",
        )
        self.student = Student.objects.create(
            school=self.school,
            first_name="Student",
            last_name="One",
            admission_number="S-001",
            parent_contact=self.parent.phone_number,
        )
        self.teacher = CustomUser.objects.create_user(
            email="teacher@example.test",
            password="test-password",
            phone_number="1000002",
            school=self.school,
        )
        self.assignment = Assignment.objects.create(
            title="Math quiz",
            teacher=self.teacher,
        )
        self.question_one, self.answer_one, self.wrong_one = self.add_question(
            "One plus one?", 1
        )
        self.question_two, self.answer_two, self.wrong_two = self.add_question(
            "Two plus two?", 2
        )
        self.client.force_authenticate(user=self.parent_user)

    def add_question(self, text, order):
        correct_choice = Choice.objects.create(title=f"correct {order}")
        wrong_choice = Choice.objects.create(title=f"wrong {order}")
        question = Question.objects.create(
            assignment=self.assignment,
            question=text,
            answer=correct_choice,
            order=order,
        )
        question.choices.add(correct_choice, wrong_choice)
        return question, correct_choice, wrong_choice

    def submission(self, **overrides):
        data = {
            "assignment_id": self.assignment.pk,
            "student_id": self.student.pk,
            "answers": {
                str(self.question_one.pk): self.answer_one.title,
                str(self.question_two.pk): self.wrong_two.title,
            },
        }
        data.update(overrides)
        return data

    def test_parent_can_submit_for_linked_child_and_grade_is_calculated(self):
        response = self.client.post(
            reverse("graded-assignment-submit"),
            self.submission(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["grade"], 50)
        self.assertEqual(GradedAssignment.objects.get().student, self.student)

    def test_parent_cannot_submit_for_an_unlinked_child(self):
        other_student = Student.objects.create(
            school=self.school,
            first_name="Student",
            last_name="Two",
            admission_number="S-002",
            parent_contact="1000003",
        )

        response = self.client.post(
            reverse("graded-assignment-submit"),
            self.submission(student_id=other_student.pk),
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(GradedAssignment.objects.exists())

    def test_answers_for_questions_outside_the_assignment_are_rejected(self):
        response = self.client.post(
            reverse("graded-assignment-submit"),
            self.submission(answers={"999999": self.answer_one.title}),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(GradedAssignment.objects.exists())

    def test_choice_must_belong_to_the_question(self):
        response = self.client.post(
            reverse("graded-assignment-submit"),
            self.submission(
                answers={
                    str(self.question_one.pk): self.answer_two.title,
                    str(self.question_two.pk): self.answer_two.title,
                }
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(GradedAssignment.objects.exists())

    def test_assignment_without_questions_cannot_be_graded(self):
        empty_assignment = Assignment.objects.create(
            title="Empty quiz",
            teacher=self.teacher,
        )

        response = self.client.post(
            reverse("graded-assignment-submit"),
            self.submission(assignment_id=empty_assignment.pk, answers={}),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(GradedAssignment.objects.exists())

    def test_parent_can_only_list_their_children_submissions(self):
        other_parent = Parent.objects.create(
            school=self.school,
            first_name="Parent",
            last_name="Two",
            email="other-parent@example.test",
            phone_number="1000004",
        )
        other_student = Student.objects.create(
            school=self.school,
            first_name="Student",
            last_name="Three",
            admission_number="S-003",
            parent_contact=other_parent.phone_number,
        )
        GradedAssignment.objects.create(
            assignment=self.assignment,
            student=self.student,
            grade=50,
        )
        GradedAssignment.objects.create(
            assignment=self.assignment,
            student=other_student,
            grade=100,
        )

        response = self.client.get(reverse("graded-assignment-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["student"], str(self.student))
