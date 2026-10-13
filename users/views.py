import openpyxl
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import FilterSet, CharFilter, DjangoFilterBackend
from rest_framework import views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from utils.bulk_imports import date_value, get_request_school, iter_excel_rows, text_value

from academic.models import Teacher, Subject, Parent
from .models import CustomUser as User, Accountant
from .serializers import (
    UserSerializer,
    UserSerializerWithToken,
    AccountantSerializer,
    TeacherSerializer,
    ParentSerializer,
)


# Custom Token View
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user_data = UserSerializerWithToken(self.user).data
        data.update(user_data)
        return data


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def getUserProfile(request):
    user = request.user
    serializer = UserSerializer(user, many=False)
    return Response(serializer.data)


class UserFilter(FilterSet):
    first_name = CharFilter(field_name="first_name", lookup_expr="icontains")
    middle_name = CharFilter(field_name="middle_name", lookup_expr="icontains")
    last_name = CharFilter(field_name="last_name", lookup_expr="icontains")

    class Meta:
        model = User
        fields = [
            "first_name",
            "middle_name",
            "last_name",
        ]


class TeacherFilter(FilterSet):
    first_name = CharFilter(field_name="first_name", lookup_expr="icontains")
    middle_name = CharFilter(field_name="middle_name", lookup_expr="icontains")
    last_name = CharFilter(field_name="last_name", lookup_expr="icontains")

    class Meta:
        model = Teacher
        fields = [
            "first_name",
            "middle_name",
            "last_name",
        ]


class ParentFilter(FilterSet):
    first_name = CharFilter(field_name="first_name", lookup_expr="icontains")
    middle_name = CharFilter(field_name="middle_name", lookup_expr="icontains")
    last_name = CharFilter(field_name="last_name", lookup_expr="icontains")

    class Meta:
        model = Parent
        fields = [
            "first_name",
            "middle_name",
            "last_name",
        ]


class UserListView(generics.ListCreateAPIView):
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter

    def get_queryset(self):
        return User.objects.filter(is_parent=False)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        user = self.get_object(pk)
        print(user)
        serializer = UserSerializer(user)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        user = self.get_object(pk)
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        user = self.get_object(pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountantListView(APIView):
    """
    API View for handling single and listing accountants.
    """

    def get(self, request, format=None):
        accountants = Accountant.objects.all()
        serializer = AccountantSerializer(accountants, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        serializer = AccountantSerializer(data=request.data)
        if serializer.is_valid():
            accountant = serializer.save()
            return Response(
                AccountantSerializer(accountant).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AccountantDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Accountant, pk=pk)

    def get(self, request, pk, format=None):
        accountant = self.get_object(pk)
        serializer = AccountantSerializer(accountant)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        accountant = self.get_object(pk)
        serializer = AccountantSerializer(accountant, data=request.data)
        if serializer.is_valid():
            updated_accountant = serializer.save()

            # Update the linked CustomUser when accountant details change
            email = updated_accountant.email
            first_name = updated_accountant.first_name
            last_name = updated_accountant.last_name

            try:
                user = User.objects.get(email=accountant.email)
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.save()
            except User.DoesNotExist:
                pass  # If user does not exist, no update is needed

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        accountant = self.get_object(pk)
        accountant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParentListView(generics.ListCreateAPIView):
    queryset = Parent.objects.all()
    serializer_class = ParentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ParentFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent = serializer.save()
        return Response(
            self.get_serializer(parent).data, status=status.HTTP_201_CREATED
        )


class ParentDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Parent, pk=pk)

    def get(self, request, pk, format=None):
        parent = self.get_object(pk)
        serializer = ParentSerializer(parent)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        parent = self.get_object(pk)
        serializer = ParentSerializer(parent, data=request.data)
        if serializer.is_valid():
            updated_parent = serializer.save()

            # Update the linked CustomUser when parent details change
            email = updated_parent.email
            first_name = updated_parent.first_name
            last_name = updated_parent.last_name

            try:
                user = User.objects.get(email=parent.email)
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.save()
            except User.DoesNotExist:
                pass  # If user does not exist, no update is needed

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        parent = self.get_object(pk)
        parent.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Teacher Views
class TeacherListView(generics.ListCreateAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TeacherFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        teacher = serializer.save()
        return Response(
            self.get_serializer(teacher).data, status=status.HTTP_201_CREATED
        )


class TeacherDetailView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Teacher, pk=pk)

    def get(self, request, pk, format=None):
        teacher = self.get_object(pk)
        serializer = TeacherSerializer(teacher)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        teacher = self.get_object(pk)
        serializer = TeacherSerializer(teacher, data=request.data)
        if serializer.is_valid():
            updated_teacher = serializer.save()

            # Update the linked CustomUser when teacher details change
            email = updated_teacher.email
            first_name = updated_teacher.first_name
            last_name = updated_teacher.last_name

            try:
                user = User.objects.get(email=teacher.email)
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.save()
            except User.DoesNotExist:
                pass  # If user does not exist, no update is needed

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        teacher = self.get_object(pk)
        teacher.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BulkUploadTeachersView(APIView):
    parser_classes = (MultiPartParser, FormParser)

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
            "phone_number",
            "employment_id",
            "short_name",
            "subject_specialization",
            "address",
            "gender",
            "date_of_birth",
            "salary",
        ]
        not_created = []
        created_count = 0
        seen_emails = set()
        seen_employee_ids = set()
        seen_short_names = set()
        try:
            for row_number, teacher_data in iter_excel_rows(file, columns):
                try:
                    first_name = text_value(teacher_data["first_name"]).lower()
                    middle_name = text_value(teacher_data["middle_name"]).lower()
                    last_name = text_value(teacher_data["last_name"]).lower()
                    employment_id = text_value(teacher_data["employment_id"])
                    short_name = text_value(teacher_data["short_name"]).upper()
                    if not all((first_name, last_name, employment_id, short_name)):
                        raise ValueError(
                            "First name, last name, employment ID, and short name are required."
                        )
                    if len(short_name) > 3:
                        raise ValueError("Short name must be at most 3 characters.")

                    generated_email = f"{first_name}.{last_name}@hayatul.com"
                    if (
                        generated_email in seen_emails
                        or employment_id in seen_employee_ids
                        or short_name in seen_short_names
                        or Teacher.objects.filter(
                            school=school, empId=employment_id
                        ).exists()
                        or Teacher.objects.filter(
                            school=school, short_name__iexact=short_name
                        ).exists()
                        or Teacher.objects.filter(
                            school=school, email__iexact=generated_email
                        ).exists()
                    ):
                        raise ValueError(
                            "Email, employment ID, or short name already exists in this school or file."
                        )

                    subject_names = [
                        name.strip().lower()
                        for name in text_value(
                            teacher_data["subject_specialization"]
                        ).split(",")
                        if name.strip()
                    ]
                    subjects = [
                        Subject.objects.get(school=school, name__iexact=name)
                        for name in subject_names
                    ]
                    date_of_birth = (
                        date_value(teacher_data["date_of_birth"], "Date of birth")
                        if teacher_data["date_of_birth"]
                        else None
                    )
                    salary_text = text_value(teacher_data["salary"])
                    salary = int(salary_text) if salary_text else None

                    with transaction.atomic():
                        user = User.objects.filter(email=generated_email).first()
                        if user is not None and user.school_id != school.pk:
                            raise ValueError(
                                "The generated login email is already assigned to another school."
                            )
                        if user is None:
                            user = User(
                                email=generated_email,
                                first_name=first_name,
                                last_name=last_name,
                                school=school,
                                is_teacher=True,
                            )
                            user.set_unusable_password()
                            user.save()
                            group, _ = Group.objects.get_or_create(name="teacher")
                            user.groups.add(group)
                        else:
                            user.first_name = first_name
                            user.last_name = last_name
                            user.is_teacher = True
                            user.save(
                                update_fields=["first_name", "last_name", "is_teacher"]
                            )

                        teacher = Teacher(
                            school=school,
                            user=user,
                            first_name=first_name,
                            middle_name=middle_name,
                            last_name=last_name,
                            email=generated_email,
                            short_name=short_name,
                            phone_number=text_value(teacher_data["phone_number"]),
                            empId=employment_id,
                            address=text_value(teacher_data["address"]).lower(),
                            gender=text_value(teacher_data["gender"]),
                            date_of_birth=date_of_birth,
                            salary=salary,
                        )
                        teacher.save()
                        teacher.subject_specialization.set(subjects)

                    created_count += 1
                    seen_emails.add(generated_email)
                    seen_employee_ids.add(employment_id)
                    seen_short_names.add(short_name)
                except (
                    ValueError,
                    ObjectDoesNotExist,
                    MultipleObjectsReturned,
                    IntegrityError,
                ) as exc:
                    not_created.append(
                        {"row": row_number, "data": teacher_data, "error": str(exc)}
                    )

            return Response(
                {
                    "message": f"{created_count} teachers successfully uploaded.",
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
