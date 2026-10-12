from django.db import models, transaction
from django.db.models import F
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string
from django.utils import timezone
from users.models import CustomUser
from administration.models import AcademicYear, Term, School
from administration.managers import SchoolScopedManager

from .validators import *
from administration.common_objs import *


class Department(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_departments")
    name = models.CharField(max_length=255)
    order_rank = models.IntegerField(
        blank=True, null=True, help_text="Rank for subject reports"
    )

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        ordering = ("order_rank", "name")
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_academic_school_department")
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        super().save(*args, **kwargs)


class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_subjects")
    name = models.CharField(max_length=255)
    subject_code = models.CharField(max_length=10, blank=True, null=True)
    is_selectable = models.BooleanField(
        default=False, help_text="Select if subject is optional"
    )
    graded = models.BooleanField(default=True, help_text="Teachers can submit grades")
    description = models.CharField(max_length=255, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, blank=True, null=True
    )

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["subject_code"]
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        constraints = [
            models.UniqueConstraint(fields=["school", "subject_code"], name="unique_academic_school_subject_code"),
            models.UniqueConstraint(fields=["school", "name"], name="unique_academic_school_subject_name")
        ]

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        self.description = f"{self.name.lower()} - {self.subject_code}"
        super().save(*args, **kwargs)


class Teacher(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_teachers")
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="academic_teacher",
        null=True,
        blank=True,
    )
    username = models.CharField(max_length=250, blank=True)
    first_name = models.CharField(max_length=300, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=300, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICE, blank=True)
    email = models.EmailField(blank=True, null=True)
    empId = models.CharField(max_length=8, null=True, blank=True)
    tin_number = models.CharField(max_length=9, blank=True, null=True)
    nssf_number = models.CharField(max_length=9, blank=True, null=True)
    short_name = models.CharField(max_length=3, blank=True, null=True)
    salary = models.IntegerField(blank=True, null=True)
    unpaid_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subject_specialization = models.ManyToManyField(Subject, blank=True)
    national_id = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=150, blank=True)
    alt_email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to="Employee_images", blank=True, null=True)
    inactive = models.BooleanField(default=False)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        ordering = ("id", "first_name", "last_name")
        constraints = [
            models.UniqueConstraint(fields=["school", "empId"], name="unique_academic_school_empId"),
            models.UniqueConstraint(fields=["school", "short_name"], name="unique_academic_school_short_name"),
            models.UniqueConstraint(fields=["school", "username"], name="unique_academic_school_teacher_username")
        ]

    def __str__(self):
        return "{} {}".format(self.first_name, self.last_name)

    @property
    def deleted(self):
        return self.inactive

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = f"{self.first_name.lower()}{self.last_name.lower()}{get_random_string(4)}"

        if not self.user:
            user = CustomUser.objects.create(
                first_name=self.first_name,
                last_name=self.last_name,
                email=self.email,
                is_teacher=True,
                school=self.school,
            )
            default_password = f"Complex.{self.empId[-4:] if self.empId and len(self.empId) >= 4 else '0000'}"
            user.set_password(default_password)
            user.save()
            self.user = user

            group, _ = Group.objects.get_or_create(name="teacher")
            user.groups.add(group)

        super().save(*args, **kwargs)

    def update_unpaid_salary(self):
        current_month = timezone.now().month
        if self.unpaid_salary > 0:
            self.unpaid_salary += self.salary
        else:
            self.unpaid_salary = self.salary
        self.save()


class GradeLevel(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_grade_levels")
    name = models.CharField(max_length=150)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_academic_school_grade_level")
        ]

    def __str__(self):
        return self.name


class ClassLevel(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_class_levels")
    name = models.CharField(max_length=150)
    grade_level = models.ForeignKey(
        GradeLevel, blank=True, null=True, on_delete=models.SET_NULL
    )

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_academic_school_class_level")
        ]

    def __str__(self):
        return self.name


class ClassYear(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_class_years")
    year = models.CharField(max_length=100, help_text="Example 2020")
    full_name = models.CharField(
        max_length=255, help_text="Example Class of 2020", blank=True
    )

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "year"], name="unique_academic_school_class_year")
        ]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = f"Class of {self.year}"
        super().save(*args, **kwargs)


class ReasonLeft(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_reasons_left")
    reason = models.CharField(max_length=255)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "reason"], name="unique_academic_school_reason_left")
        ]

    def __str__(self):
        return self.reason


class Stream(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_streams")
    name = models.CharField(max_length=50, validators=[stream_validator])

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_academic_school_stream")
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)


class ClassRoom(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_class_rooms")
    name = models.ForeignKey(
        ClassLevel, on_delete=models.CASCADE, blank=True, related_name="class_level"
    )
    stream = models.ForeignKey(
        Stream, on_delete=models.CASCADE, blank=True, related_name="class_stream"
    )
    class_teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, blank=True)
    capacity = models.PositiveIntegerField(default=40, blank=True)
    occupied_sits = models.PositiveIntegerField(default=0, blank=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name", "stream"], name="unique_academic_school_classroom")
        ]

    def __str__(self):
        return f"{self.name} {self.stream}" if self.stream else str(self.name)

    @property
    def available_sits(self):
        return self.capacity - self.occupied_sits

    @property
    def class_status(self):
        if self.capacity == 0:
            return "0.00%"
        percentage = (self.occupied_sits / self.capacity) * 100
        return f"{percentage:.2f}%"

    def clean(self):
        if self.occupied_sits > self.capacity:
            raise ValidationError("Occupied sits cannot exceed the capacity.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Topic(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_topics")
    name = models.CharField(max_length=255, blank=True, null=True)
    class_level = models.ForeignKey(
        ClassLevel, on_delete=models.CASCADE, blank=True, null=True
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, blank=True, null=True
    )

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return self.name


class SubTopic(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_sub_topics")
    name = models.CharField(max_length=255, blank=True, null=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, blank=True, null=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return self.name


class AllocatedSubject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_allocated_subjects")
    teacher_name = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="allocated_subjects"
    )
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.SET_NULL, blank=True, null=True)
    class_room = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, related_name="subjects"
    )
    weekly_periods = models.IntegerField(help_text="Total number of periods per week.")
    max_daily_periods = models.IntegerField(
        default=2,
        help_text="Maximum number of periods allowed per day for this subject.",
    )

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return f"{self.teacher_name} - {self.subject} ({self.academic_year})"


class Parent(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_parents")
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="academic_parent",
        null=True,
        blank=True,
    )
    first_name = models.CharField(max_length=300, verbose_name="First Name", blank=True, null=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Middle Name")
    last_name = models.CharField(max_length=300, verbose_name="Last Name", blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICE, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    parent_type = models.CharField(choices=PARENT_CHOICE, max_length=10, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=150, help_text="Personal phone number")
    national_id = models.CharField(max_length=100, blank=True, null=True)
    occupation = models.CharField(max_length=255, blank=True, null=True, help_text="Current occupation")
    monthly_income = models.FloatField(help_text="Parent's average monthly income", blank=True, null=True)
    single_parent = models.BooleanField(default=False, blank=True, help_text="Is he/she a single parent")
    alt_email = models.EmailField(blank=True, null=True, help_text="Personal email")
    date = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to="Parent_images", blank=True)
    inactive = models.BooleanField(default=False)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        ordering = ["email", "first_name", "last_name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "phone_number"], name="unique_academic_school_parent_phone"),
            models.UniqueConstraint(fields=["school", "email"], name="unique_academic_school_parent_email")
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def save(self, *args, **kwargs):
        user, created = CustomUser.objects.get_or_create(
            phone_number=self.phone_number,
            school=self.school,
            defaults={
                "first_name": self.first_name,
                "last_name": self.last_name,
                "email": self.email,
                "is_parent": True,
            },
        )

        if created:
            user.set_password("Complex.0000")
            user.save()
            group, _ = Group.objects.get_or_create(name="parent")
            user.groups.add(group)

        self.user = user
        super().save(*args, **kwargs)


class Student(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_students")
    first_name = models.CharField(max_length=150, null=True, verbose_name="First Name")
    middle_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Middle Name")
    last_name = models.CharField(max_length=150, null=True, verbose_name="Last Name")
    graduation_date = models.DateField(blank=True, null=True)
    class_level = models.ForeignKey(
        "ClassLevel", blank=True, null=True, on_delete=models.SET_NULL
    )
    class_of_year = models.ForeignKey(
        "ClassYear", blank=True, null=True, on_delete=models.SET_NULL
    )
    date_dismissed = models.DateField(blank=True, null=True)
    reason_left = models.ForeignKey(
        "ReasonLeft", blank=True, null=True, on_delete=models.SET_NULL
    )
    gender = models.CharField(max_length=10, choices=GENDER_CHOICE, blank=True, null=True)
    religion = models.CharField(max_length=50, choices=RELIGION_CHOICE, blank=True, null=True)
    region = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True)
    blood_group = models.CharField(max_length=10, blank=True, null=True)
    parent_guardian = models.ForeignKey(
        "Parent",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="children",
    )
    parent_contact = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    admission_date = models.DateTimeField(auto_now_add=True)
    admission_number = models.CharField(max_length=50, blank=True)
    prems_number = models.CharField(max_length=50, blank=True)
    std_vii_number = models.CharField(max_length=50, blank=True)
    siblings = models.ManyToManyField("self", blank=True)
    image = models.ImageField(upload_to="Student_images", blank=True)
    cache_gpa = models.DecimalField(
        editable=False, max_digits=5, decimal_places=2, blank=True, null=True
    )

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        ordering = ["admission_number", "last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(fields=["school", "admission_number"], name="unique_academic_school_admission_number")
        ]

    def __str__(self):
        return f"{self.admission_number} - {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        parts = filter(None, [self.first_name, self.middle_name, self.last_name])
        return " ".join(part.capitalize() for part in parts)

    @property
    def debt(self):
        return sum(
            (record.balance for record in self.debt_records.filter(is_reversed=False)),
            Decimal("0.00"),
        )

    @property
    def total_paid(self):
        return self.payments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    def unpaid_terms(self):
        return self.debt_records.filter(is_reversed=False).exclude(
            amount_paid__gte=models.F("amount_added")
        )

    def clean(self):
        if Teacher.objects.filter(id=self.id).exists():
            raise ValidationError("A person cannot be both a student and a teacher.")
        super().clean()

    def save(self, *args, **kwargs):
        if not self.parent_contact:
            raise ValidationError("Parent contact is required.")

        self.first_name = self.first_name.lower() if self.first_name else ""
        self.middle_name = self.middle_name.lower() if self.middle_name else ""
        self.last_name = self.last_name.lower() if self.last_name else ""

        parent, created = Parent.objects.get_or_create(
            phone_number=self.parent_contact,
            school=self.school,
            defaults={
                "first_name": self.middle_name or "Unknown",
                "last_name": self.last_name or "Unknown",
                "email": f"parent_of_{self.first_name}_{self.last_name}@system.com",
                "phone_number": self.parent_contact,
                "school": self.school,
            },
        )
        self.parent_guardian = parent

        super().save(*args, **kwargs)

        existing_siblings = Student.objects.filter(
            parent_contact=self.parent_contact,
            school=self.school
        ).exclude(id=self.id)

        for sibling in existing_siblings:
            self.siblings.add(sibling)
            sibling.siblings.add(self)


class StudentClassEnrollment(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_student_enrollments")
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, related_name="class_students"
    )
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="student_classes",
        blank=True,
        null=True,
    )

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    @property
    def is_current_class(self):
        return self.academic_year.is_current_session

    def __str__(self):
        return f"Student: {self.student}, Class: {self.classroom}"


class StudentsMedicalHistory(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_medical_histories")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    history = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="students_medical_files", blank=True, null=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return f"Medical History for {self.student}"


class StudentsPreviousAcademicHistory(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_prev_academic_histories")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    former_school = models.CharField(max_length=255)
    last_gpa = models.FloatField()
    notes = models.CharField(max_length=255, blank=True)
    academic_record = models.FileField(upload_to="students_former_academic_files", blank=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return f"Previous Academic History for {self.student}"


class Dormitory(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_dormitories")
    name = models.CharField(max_length=150)
    capacity = models.PositiveIntegerField(blank=True, null=True)
    occupied_beds = models.IntegerField(blank=True, null=True)
    captain = models.ForeignKey(Student, on_delete=models.CASCADE, blank=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_academic_school_dormitory")
        ]

    def __str__(self):
        return self.name

    def available_beds(self):
        total = self.capacity - self.occupied_beds
        if total <= 0:
            return 0
        return total


class DormitoryAllocation(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_dormitory_allocations")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    dormitory = models.ForeignKey(Dormitory, on_delete=models.CASCADE)
    date_from = models.DateField(auto_now_add=True)
    date_till = models.DateField(blank=True, null=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return str(self.student.admission_number)


class StudentFile(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_student_files")
    file = models.FileField(
        upload_to="students_files/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "jpg", "png", "docx"])],
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return str(self.student)


class StudentHealthRecord(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_health_records")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    record = models.TextField()

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return str(self.student)


class MessageToParent(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_parent_messages")
    message = models.TextField()
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(default=timezone.now)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return self.message


class MessageToTeacher(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="academic_teacher_messages")
    message = models.TextField()
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(default=timezone.now)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return self.message


class FamilyAccessUser(CustomUser):
    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        group, _ = Group.objects.get_or_create(name="family")
        if not self.groups.filter(name="family").exists():
            self.groups.add(group)