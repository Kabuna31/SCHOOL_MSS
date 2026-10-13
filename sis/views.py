import openpyxl
import re
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.db import transaction
from django_filters.rest_framework import FilterSet, CharFilter, DjangoFilterBackend
from rest_framework import views
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status, generics
from django.http import Http404


from academic.models import Student, ClassLevel, Parent
from .serializers import StudentSerializer
from utils.bulk_imports import (
    excel_response,
    get_request_school,
    iter_excel_rows,
    text_value,
)

# Students filter


class StudentFilter(FilterSet):
    first_name = CharFilter(field_name="first_name", lookup_expr="icontains")
    middle_name = CharFilter(field_name="middle_name", lookup_expr="icontains")
    last_name = CharFilter(field_name="last_name", lookup_expr="icontains")
    class_level = CharFilter(method="filter_by_class_level")

    class Meta:
        model = Student
        fields = ["first_name", "middle_name", "last_name", "class_level"]

    def filter_by_class_level(self, queryset, name, value):
        return queryset.filter(class_level__name__icontains=value)


class StudentListView(generics.ListCreateAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = StudentFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        return Response(
            self.get_serializer(student).data, status=status.HTTP_201_CREATED
        )


class StudentDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Student.objects.get(pk=pk)
        except Student.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        student = self.get_object(pk)
        serializer = StudentSerializer(student)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        student = self.get_object(pk)
        serializer = StudentSerializer(student, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        student = self.get_object(pk)
        student.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BulkUploadStudentsView(APIView):
    """
    API View to handle bulk uploading of students from an Excel file.
    """

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        columns = [
            "first_name",
            "middle_name",
            "last_name",
            "admission_number",
            "parent_contact",
            "religion",
            "class_level",
            "gender",
        ]
        not_created = []
        created_students = []
        new_parents_created = 0
        updated_students_info = []
        skipped_students = []
        seen_admission_numbers = set()
        try:
            for row_number, student_data in iter_excel_rows(file, columns):
                new_parent_created = False
                try:
                    first_name = text_value(student_data["first_name"]).lower()
                    middle_name = text_value(student_data["middle_name"]).lower()
                    last_name = text_value(student_data["last_name"]).lower()
                    admission_number = text_value(student_data["admission_number"])
                    parent_contact = text_value(student_data["parent_contact"])
                    class_name = text_value(student_data["class_level"])
                    gender = text_value(student_data["gender"])
                    if not all((first_name, last_name, admission_number, parent_contact, class_name, gender)):
                        raise ValueError(
                            "First name, last name, admission number, parent contact, class, and gender are required."
                        )
                    if admission_number in seen_admission_numbers:
                        raise ValueError(
                            f"Admission number {admission_number!r} is duplicated in this file."
                        )
                    with transaction.atomic():
                        class_level = ClassLevel.objects.get(
                            school=school, name__iexact=class_name
                        )
                        parent = Parent.objects.filter(
                            school=school, phone_number=parent_contact
                        ).first()
                        if parent is None:
                            phone_digits = re.sub(r"\D", "", parent_contact)
                            parent = Parent(
                                school=school,
                                phone_number=parent_contact,
                                first_name=middle_name or first_name,
                                last_name=last_name,
                                email=f"parent_{school.pk}_{phone_digits}@hayatul.com",
                            )
                            parent.save()
                            if parent.user_id:
                                parent.user.set_unusable_password()
                                parent.user.save(update_fields=["password"])
                            new_parent_created = True

                        student_exists = Student.objects.filter(
                            school=school, admission_number=admission_number
                        ).first()
                        if student_exists:
                            update_reasons = []
                            if not student_exists.parent_guardian_id:
                                student_exists.parent_guardian = parent
                                update_reasons.append("parent added")
                            existing_sibling = (
                                Student.objects.filter(
                                    school=school, parent_contact=parent_contact
                                )
                                .exclude(pk=student_exists.pk)
                                .first()
                            )
                            if existing_sibling and not student_exists.siblings.filter(
                                pk=existing_sibling.pk
                            ).exists():
                                student_exists.siblings.add(existing_sibling)
                                existing_sibling.siblings.add(student_exists)
                                update_reasons.append("sibling added")
                            if update_reasons:
                                student_exists.save()
                                updated_students_info.append(
                                    {
                                        "admission_number": admission_number,
                                        "full_name": (
                                            f"{student_exists.first_name} "
                                            f"{student_exists.last_name}"
                                        ),
                                        "reasons": update_reasons,
                                    }
                                )
                            else:
                                skipped_students.append(
                                    {
                                        "admission_number": admission_number,
                                        "full_name": (
                                            f"{student_exists.first_name} "
                                            f"{student_exists.last_name}"
                                        ),
                                        "reason": "Student already exists and no updates were needed.",
                                    }
                                )
                        else:
                            student = Student(
                                school=school,
                                first_name=first_name,
                                middle_name=middle_name,
                                last_name=last_name,
                                admission_number=admission_number,
                                parent_contact=parent_contact,
                                religion=text_value(student_data["religion"]),
                                class_level=class_level,
                                gender=gender,
                                parent_guardian=parent,
                            )
                            existing_sibling = Student.objects.filter(
                                school=school, parent_contact=parent_contact
                            ).first()
                            student.save()
                            if existing_sibling and existing_sibling.pk != student.pk:
                                student.siblings.add(existing_sibling)
                                existing_sibling.siblings.add(student)
                            created_students.append(student)
                    seen_admission_numbers.add(admission_number)
                    if new_parent_created:
                        new_parents_created += 1
                except (
                    ValueError,
                    ObjectDoesNotExist,
                    MultipleObjectsReturned,
                    ValidationError,
                    IntegrityError,
                ) as exc:
                    not_created.append(
                        {"row": row_number, "data": student_data, "error": str(exc)}
                    )

            return Response(
                {
                    "message": f"{len(created_students)} students successfully uploaded. {new_parents_created} parents created successfully. ",
                    "updated_students": updated_students_info,
                    "skipped_students": skipped_students,
                    "not_created": not_created,
                },
                status=status.HTTP_201_CREATED,
            )
        except (
            openpyxl.utils.exceptions.InvalidFileException,
            OSError,
            ValueError,
        ) as exc:
            return Response(
                {"error": f"Invalid Excel file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class StudentsExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        students = Student.objects.filter(school=school).select_related("class_level")
        rows = (
            (
                student.first_name,
                student.middle_name,
                student.last_name,
                student.admission_number,
                student.parent_contact,
                student.religion,
                student.class_level.name if student.class_level else "",
                student.gender,
            )
            for student in students
        )
        return excel_response(
            "students.xlsx",
            "Students",
            [
                "first_name",
                "middle_name",
                "last_name",
                "admission_number",
                "parent_contact",
                "religion",
                "class_level",
                "gender",
            ],
            rows,
        )


"""
class StudentHealthRecordViewSet(viewsets.ModelViewSet):
    queryset = StudentHealthRecord.objects.all()
    serializer_class = StudentHealthRecordSerializer

class GradeScaleViewSet(viewsets.ModelViewSet):
    queryset = GradeScale.objects.all()
    serializer_class = GradeScaleSerializer

class GradeScaleRuleViewSet(viewsets.ModelViewSet):
    queryset = GradeScaleRule.objects.all()
    serializer_class = GradeScaleRuleSerializer

class SchoolYearViewSet(viewsets.ModelViewSet):
    queryset = SchoolYear.objects.all()
    serializer_class = SchoolYearSerializer

class MessageToStudentViewSet(viewsets.ModelViewSet):
    queryset = MessageToStudent.objects.all()
    serializer_class = MessageToStudentSerializer
"""
