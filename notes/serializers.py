from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from academic.models import Student
from users.models import CustomUser as User
from .models import (
    Assignment,
    Question,
    Choice,
    GradedAssignment,
)


class StringSerializer(serializers.StringRelatedField):
    def to_internal_value(self, value):
        return value


class QuestionSerializer(serializers.ModelSerializer):
    choices = StringSerializer(many=True)

    class Meta:
        model = Question
        fields = ("id", "choices", "question", "order")


class AssignmentSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    teacher = StringSerializer(many=False)

    class Meta:
        model = Assignment
        fields = "__all__"

    def get_questions(self, obj):
        questions = QuestionSerializer(obj.questions.all(), many=True).data
        return questions

    def create(self, request):
        data = request.data

        assignment = Assignment()
        teacher = User.objects.get(username=data["teacher"])
        assignment.teacher = teacher
        assignment.title = data["title"]
        assignment.save()

        order = 1
        for q in data["questions"]:
            newQ = Question()
            newQ.question = q["title"]
            newQ.order = order
            newQ.save()

            for c in q["choices"]:
                newC = Choice()
                newC.title = c
                newC.save()
                newQ.choices.add(newC)

            newQ.answer = Choice.objects.get(title=q["answer"])
            newQ.assignment = assignment
            newQ.save()
            order += 1
        return assignment


class GradedAssignmentSerializer(serializers.ModelSerializer):
    student = StringSerializer(many=False)

    class Meta:
        model = GradedAssignment
        fields = "__all__"


class GradedAssignmentSubmissionSerializer(serializers.Serializer):
    assignment_id = serializers.IntegerField(min_value=1)
    student_id = serializers.IntegerField(min_value=1)
    answers = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict
    )

    def validate(self, attrs):
        parent = self.context["parent"]
        student = Student.objects.filter(
            pk=attrs["student_id"],
            parent_guardian=parent,
            school_id=parent.school_id,
        ).first()
        if student is None:
            raise PermissionDenied(
                "You can only submit assignments for children linked to your account."
            )

        assignment = (
            Assignment.objects.select_related("teacher")
            .filter(pk=attrs["assignment_id"], teacher__school_id=parent.school_id)
            .first()
        )
        if assignment is None:
            raise serializers.ValidationError(
                {"assignment_id": "The assignment is not available for your school."}
            )

        questions = list(
            assignment.questions.select_related("answer")
            .prefetch_related("choices")
            .order_by("id")
        )
        if not questions:
            raise serializers.ValidationError(
                {"assignment_id": "This assignment has no questions to grade."}
            )

        question_ids = {question.pk for question in questions}
        normalized_answers = {}
        for question_id, choice_id in attrs["answers"].items():
            try:
                parsed_question_id = int(question_id)
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    {"answers": f"Invalid question ID: {question_id}."}
                ) from None

            if parsed_question_id in normalized_answers:
                raise serializers.ValidationError(
                    {
                        "answers": (
                            f"Question {parsed_question_id} was answered more than once."
                        )
                    }
                )
            if parsed_question_id not in question_ids:
                raise serializers.ValidationError(
                    {"answers": f"Question {parsed_question_id} is not in this assignment."}
                )
            normalized_answers[parsed_question_id] = choice_id

        correct_count = 0
        for question in questions:
            choices = list(question.choices.all())
            choice_titles = {choice.title for choice in choices}
            if (
                question.answer_id is None
                or question.answer_id not in {choice.pk for choice in choices}
                or None in choice_titles
                or "" in choice_titles
                or len(choice_titles) != len(choices)
            ):
                raise serializers.ValidationError(
                    {
                        "assignment_id": (
                            "This assignment contains a question without a valid answer."
                        )
                    }
                )

            selected_title = normalized_answers.get(question.pk)
            if selected_title is not None:
                if selected_title not in choice_titles:
                    raise serializers.ValidationError(
                        {
                            "answers": (
                                f"Selected choice is not valid for question {question.pk}."
                            )
                        }
                    )
                if selected_title == question.answer.title:
                    correct_count += 1

        return {
            "assignment": assignment,
            "student": student,
            "grade": correct_count / len(questions) * 100,
        }

    def create(self, validated_data):
        return GradedAssignment.objects.create(**validated_data)
