import openpyxl
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from administration.models import AcademicYear
from .models import (
    Subject,
    Department,
    ClassRoom,
    ClassLevel,
    Stream,
    Teacher,
    GradeLevel,
    ClassYear,
    ReasonLeft,
    StudentClassEnrollment as StudentClass,
    Student,
)
from .serializers import (
    DepartmentSerializer,
    ClassLevelSerializer,
    GradeLevelSerializer,
    ClassYearSerializer,
    ReasonLeftSerializer,
    StreamSerializer,
    SubjectSerializer,
    ClassRoomSerializer,
    StudentClassEnrollmentSerializer,
)
from utils.bulk_imports import (
    excel_response,
    get_request_school,
    iter_excel_rows,
    text_value,
)


# Department Views
class DepartmentListCreateView(generics.ListCreateAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]


# ClassLevel Views
class ClassLevelListCreateView(generics.ListCreateAPIView):
    queryset = ClassLevel.objects.all()
    serializer_class = ClassLevelSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        print(request.data)
        return super().create(request, *args, **kwargs)


class ClassLevelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ClassLevel.objects.all()
    serializer_class = ClassLevelSerializer
    permission_classes = [IsAuthenticated]


# GradeLevel Views
class GradeLevelListCreateView(generics.ListCreateAPIView):
    queryset = GradeLevel.objects.all()
    serializer_class = GradeLevelSerializer
    permission_classes = [IsAuthenticated]


class GradeLevelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GradeLevel.objects.all()
    serializer_class = GradeLevelSerializer
    permission_classes = [IsAuthenticated]


# ClassYear Views
class ClassYearListCreateView(generics.ListCreateAPIView):
    queryset = ClassYear.objects.all()
    serializer_class = ClassYearSerializer
    permission_classes = [IsAuthenticated]


class ClassYearDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ClassYear.objects.all()
    serializer_class = ClassYearSerializer
    permission_classes = [IsAuthenticated]


# ReasonLeft Views
class ReasonLeftListCreateView(generics.ListCreateAPIView):
    queryset = ReasonLeft.objects.all()
    serializer_class = ReasonLeftSerializer
    permission_classes = [IsAuthenticated]


class ReasonLeftDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ReasonLeft.objects.all()
    serializer_class = ReasonLeftSerializer
    permission_classes = [IsAuthenticated]


# Stream Views
class StreamListCreateView(generics.ListCreateAPIView):
    queryset = Stream.objects.all()
    serializer_class = StreamSerializer
    permission_classes = [IsAuthenticated]


class StreamDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Stream.objects.all()
    serializer_class = StreamSerializer
    permission_classes = [IsAuthenticated]


class SubjectListView(generics.ListCreateAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]


class SubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve, update, or delete a subject.
    """

    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    lookup_field = "id"  # You can change this to "subject_code" if needed


class BulkUploadSubjectsView(APIView):
    """
    API View to handle bulk uploading of subjects from an Excel file.
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

        columns = ["name", "subject_code", "department"]
        subjects_to_create = []
        not_created = []
        seen_names = set()
        seen_codes = set()
        try:
            for row_number, subject_data in iter_excel_rows(file, columns):
                try:
                    name = text_value(subject_data["name"]).lower()
                    subject_code = text_value(subject_data["subject_code"]).upper()
                    department_name = text_value(subject_data["department"]).lower()
                    if not name or not subject_code or not department_name:
                        raise ValueError(
                            "Name, subject code, and department are required."
                        )
                    if subject_code in seen_codes or Subject.objects.filter(
                        school=school, subject_code__iexact=subject_code
                    ).exists():
                        raise ValueError(
                            f"Subject code {subject_code!r} already exists."
                        )
                    if name in seen_names or Subject.objects.filter(
                        school=school, name__iexact=name
                    ).exists():
                        raise ValueError(f"Subject name {name!r} already exists.")
                    department = Department.objects.get(
                        school=school, name__iexact=department_name
                    )
                    subject = Subject(
                        school=school,
                        name=name,
                        subject_code=subject_code,
                        description=f"{name} - {subject_code}",
                        department=department,
                    )
                    subjects_to_create.append(subject)
                    seen_names.add(name)
                    seen_codes.add(subject_code)
                except (ValueError, ObjectDoesNotExist, MultipleObjectsReturned) as exc:
                    not_created.append(
                        {"row": row_number, "data": subject_data, "error": str(exc)}
                    )

            if subjects_to_create:
                try:
                    with transaction.atomic():
                        Subject.objects.bulk_create(subjects_to_create)
                except IntegrityError:
                    return Response(
                        {
                            "error": "One or more subjects conflict with existing school data."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            return Response(
                {
                    "message": f"{len(subjects_to_create)} subjects successfully uploaded.",
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


class ClassRoomView(APIView):
    """
    API View to handle CRUD operations for ClassRoom model.
    """

    def get(self, request):
        classrooms = ClassRoom.objects.all()
        serializer = ClassRoomSerializer(classrooms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ClassRoomSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkUploadClassRoomsView(APIView):
    """
    API View to handle bulk uploading of classrooms from an Excel file.
    """

    def post(self, request):
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

        columns = ["name", "stream", "class_teacher"]
        classrooms_to_create = []
        not_created = []
        seen_classrooms = set()
        try:
            for row_number, classroom_data in iter_excel_rows(file, columns):
                try:
                    class_name = text_value(classroom_data["name"]).lower()
                    stream_name = text_value(classroom_data["stream"]).upper()
                    teacher_reference = text_value(
                        classroom_data["class_teacher"]
                    )
                    if not class_name or not stream_name or not teacher_reference:
                        raise ValueError(
                            "Class, stream, and class teacher are required."
                        )
                    name = ClassLevel.objects.get(
                        school=school, name__iexact=class_name
                    )
                    stream = Stream.objects.get(
                        school=school, name__iexact=stream_name
                    )
                    key = (name.pk, stream.pk)
                    if key in seen_classrooms or ClassRoom.objects.filter(
                        school=school, name=name, stream=stream
                    ).exists():
                        raise ValueError(
                            "Classroom with this class and stream already exists."
                        )

                    class_teacher = Teacher.objects.filter(
                        school=school, empId__iexact=teacher_reference
                    ).first()
                    if class_teacher is None:
                        teacher_name_parts = teacher_reference.lower().split()
                        if len(teacher_name_parts) < 2:
                            raise ValueError(
                                "Class teacher must be identified by employment ID or full name."
                            )
                        class_teacher = Teacher.objects.get(
                            school=school,
                            first_name__iexact=teacher_name_parts[0],
                            last_name__iexact=teacher_name_parts[-1],
                        )
                    classroom = ClassRoom(
                        school=school,
                        name=name,
                        stream=stream,
                        class_teacher=class_teacher,
                    )
                    classrooms_to_create.append(classroom)
                    seen_classrooms.add(key)
                except (ValueError, ObjectDoesNotExist, MultipleObjectsReturned) as exc:
                    not_created.append(
                        {
                            "row": row_number,
                            "data": classroom_data,
                            "error": str(exc),
                        }
                    )

            if classrooms_to_create:
                try:
                    with transaction.atomic():
                        ClassRoom.objects.bulk_create(classrooms_to_create)
                except IntegrityError:
                    return Response(
                        {
                            "error": "One or more classrooms conflict with existing school data."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            return Response(
                {
                    "created": len(classrooms_to_create),
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


class StudentClassListCreateView(generics.ListCreateAPIView):
    """
    View to list and create student-class assignments.
    """

    queryset = StudentClass.objects.all()
    serializer_class = StudentClassEnrollmentSerializer
    permission_classes = [IsAuthenticated]


class StudentClassDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View to retrieve, update, or delete a specific student-class assignment.
    """

    queryset = StudentClass.objects.all()
    serializer_class = StudentClassEnrollmentSerializer
    permission_classes = [IsAuthenticated]


class BulkUploadStudentClassView(APIView):
    """
    API View to handle bulk uploading of StudentClass records from an Excel file.
    """

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        columns = [
            "classroom_name",
            "stream_name",
            "academic_year",
            "student_full_name",
            "student_admission_number",
        ]
        rows_with_errors = []
        student_classes_to_create = []
        seen_assignments = set()
        pending_per_classroom = {}
        try:
            for row_number, row_data in iter_excel_rows(file, columns):
                try:
                    classroom_name = text_value(row_data["classroom_name"]).lower()
                    stream_name = text_value(row_data["stream_name"]).upper()
                    year_name = text_value(row_data["academic_year"])
                    full_name = text_value(row_data["student_full_name"]).lower()
                    admission_number = text_value(
                        row_data["student_admission_number"]
                    )
                    if not all((classroom_name, stream_name, year_name)) or not (
                        full_name or admission_number
                    ):
                        raise ValueError(
                            "Classroom, stream, academic year, and student name or admission number are required."
                        )
                    classroom = ClassRoom.objects.get(
                        school=school,
                        name__name__iexact=classroom_name,
                        stream__name__iexact=stream_name,
                    )
                    academic_year = AcademicYear.objects.get(
                        school=school, name__iexact=year_name
                    )
                    if admission_number:
                        student = Student.objects.get(
                            school=school, admission_number=admission_number
                        )
                    else:
                        name_parts = full_name.split()
                        if len(name_parts) < 2:
                            raise ValueError(
                                "Student full name must include first and last names."
                            )
                        first_name, last_name = name_parts[0], name_parts[-1]
                        student = Student.objects.get(
                            school=school,
                            first_name__iexact=first_name,
                            last_name__iexact=last_name,
                        )
                    if classroom.name != student.class_level:
                        raise ValueError(
                            "The classroom does not match the student's class level."
                        )
                    assignment_key = (classroom.pk, academic_year.pk, student.pk)
                    if assignment_key in seen_assignments or StudentClass.objects.filter(
                        school=school,
                        classroom=classroom,
                        academic_year=academic_year,
                        student=student,
                    ).exists():
                        raise ValueError(
                            "Student is already assigned to this classroom and year."
                        )
                    next_occupancy = (
                        classroom.occupied_sits
                        + pending_per_classroom.get(classroom.pk, 0)
                        + 1
                    )
                    if next_occupancy > classroom.capacity:
                        raise ValueError(f"Classroom {classroom} has reached its capacity.")
                    student_class = StudentClass(
                        school=school,
                        classroom=classroom,
                        academic_year=academic_year,
                        student=student,
                    )
                    student_classes_to_create.append(student_class)
                    seen_assignments.add(assignment_key)
                    pending_per_classroom[classroom.pk] = (
                        pending_per_classroom.get(classroom.pk, 0) + 1
                    )
                except (
                    ValueError,
                    ObjectDoesNotExist,
                    MultipleObjectsReturned,
                    ValidationError,
                ) as exc:
                    rows_with_errors.append({"row": row_number, "errors": str(exc)})

            with transaction.atomic():
                if student_classes_to_create:
                    StudentClass.objects.bulk_create(student_classes_to_create)
                    for classroom_id, count in pending_per_classroom.items():
                        ClassRoom.objects.filter(
                            school=school, pk=classroom_id
                        ).update(occupied_sits=F("occupied_sits") + count)
            return Response(
                {
                    "message": f"{len(student_classes_to_create)} student-class records successfully uploaded.",
                    "errors": rows_with_errors,
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


class SubjectsExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subjects = Subject.objects.filter(school=school).select_related("department")
        rows = (
            (subject.name, subject.subject_code, subject.department.name if subject.department else "")
            for subject in subjects
        )
        return excel_response(
            "subjects.xlsx",
            "Subjects",
            ["name", "subject_code", "department"],
            rows,
        )


class ClassRoomsExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        classrooms = ClassRoom.objects.filter(school=school).select_related(
            "name", "stream", "class_teacher"
        )
        rows = (
            (
                classroom.name.name,
                classroom.stream.name,
                (
                    classroom.class_teacher.empId
                    or f"{classroom.class_teacher.first_name} {classroom.class_teacher.last_name}".strip()
                ),
            )
            for classroom in classrooms
        )
        return excel_response(
            "classrooms.xlsx",
            "Classrooms",
            ["name", "stream", "class_teacher"],
            rows,
        )


class StudentClassesExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrollments = StudentClass.objects.filter(school=school).select_related(
            "classroom__name",
            "classroom__stream",
            "academic_year",
            "student",
        )
        rows = (
            (
                enrollment.classroom.name.name,
                enrollment.classroom.stream.name,
                enrollment.academic_year.name,
                enrollment.student.full_name if enrollment.student else "",
                (
                    enrollment.student.admission_number
                    if enrollment.student
                    else ""
                ),
            )
            for enrollment in enrollments
        )
        return excel_response(
            "student_classes.xlsx",
            "Student Classes",
            [
                "classroom_name",
                "stream_name",
                "academic_year",
                "student_full_name",
                "student_admission_number",
            ],
            rows,
        )
