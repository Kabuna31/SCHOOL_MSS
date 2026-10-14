import logging
import datetime
from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from academic.models import Student, Teacher, ClassRoom, StudentClassEnrollment, Subject
from administration.models import AcademicYear, Term, School
from administration.managers import SchoolScopedManager


logger = logging.getLogger(__name__)


class GradeScale(models.Model):
    """Translate a numeric grade to some other scale.
    Example: Letter grade or 4.0 scale."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_scales")
    name = models.CharField(max_length=255)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_school_grade_scale")
        ]

    def __str__(self):
        return self.name

    def get_rule(self, grade):
        if grade is None:
            return None
        rule = self.gradescalerule_set.filter(
            min_grade__lte=grade, max_grade__gte=grade
        ).first()
        if not rule:
            logger.debug("No grade scale rule matched a numeric grade.")
        return rule

    def to_letter(self, grade):
        rule = self.get_rule(grade)
        if rule:
            return rule.letter_grade
        return None

    def to_numeric(self, grade):
        rule = self.get_rule(grade)
        if rule:
            return rule.numeric_scale
        return None


class GradeScaleRule(models.Model):
    """One rule for a grade scale."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="grade_scale_rules")
    min_grade = models.DecimalField(max_digits=5, decimal_places=2)
    max_grade = models.DecimalField(max_digits=5, decimal_places=2)
    letter_grade = models.CharField(max_length=50, blank=True, null=True)
    numeric_scale = models.DecimalField(max_digits=5, decimal_places=2, blank=True)
    grade_scale = models.ForeignKey(GradeScale, on_delete=models.CASCADE)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school", "grade_scale", "min_grade", "max_grade"], 
                name="unique_school_grade_scale_rule"
            )
        ]
        indexes = [
            models.Index(fields=["min_grade", "max_grade", "grade_scale"]),
        ]

    def __str__(self):
        return f"{self.min_grade}-{self.max_grade} {self.letter_grade} {self.numeric_scale}"

    def clean(self):
        if not self.letter_grade and not self.numeric_scale:
            raise ValidationError(
                "Either a letter grade or numeric scale must be provided."
            )
        if self.letter_grade and self.numeric_scale is None:
            raise ValidationError(
                "If a letter grade is provided, numeric scale must also be provided."
            )
        if self.numeric_scale and self.letter_grade is None:
            raise ValidationError(
                "If a numeric scale is provided, a letter grade must also be provided."
            )

    def save(self, *args, **kwargs):
        if self.min_grade >= self.max_grade:
            raise ValidationError("min_grade must be less than max_grade.")
        super().save(*args, **kwargs)


class Result(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    gpa = models.FloatField(null=True)
    cat_gpa = models.FloatField(null=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.SET_NULL, blank=True, null=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school", "student", "academic_year", "term"],
                name="unique_school_student_term_result"
            )
        ]

    def __str__(self):
        return str(self.student)

    def clean(self):
        if self.gpa is not None and (self.gpa < 0.0 or self.gpa > 4.0):
            raise ValidationError("GPA must be between 0.0 and 4.0.")
        if self.cat_gpa is not None and (self.cat_gpa < 0.0 or self.cat_gpa > 4.0):
            raise ValidationError("CAT GPA must be between 0.0 and 4.0.")


class ExaminationListHandler(models.Model):
    ASSESSMENT_TYPE_CHOICES = (
        ("AOI", "Assessment of Learning (AOI)"),
        ("EOT", "End of Term (EOT)"),
    )

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="examinations")
    name = models.CharField(max_length=100)
    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name="examinations",
        null=True,
        blank=True,
    )
    assessment_type = models.CharField(
        max_length=3,
        choices=ASSESSMENT_TYPE_CHOICES,
        default="EOT",
    )
    start_date = models.DateField()
    ends_date = models.DateField()
    out_of = models.IntegerField()
    classrooms = models.ManyToManyField(ClassRoom, related_name="class_exams")
    comments = models.CharField(
        max_length=200, blank=True, null=True, help_text="Comments Regarding Exam"
    )
    created_by = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True)
    created_on = models.DateTimeField(auto_now_add=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_school_exam_name")
        ]

    @property
    def status(self):
        today = datetime.date.today()
        if today > self.ends_date:
            return "Done"
        elif self.start_date <= today <= self.ends_date:
            return "Ongoing"
        return "Coming Up"

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date > self.ends_date:
            raise ValidationError("Start date cannot be later than end date.")
        if (
            self.term_id
            and self.term.academic_year.school_id
            and self.term.academic_year.school_id != self.school_id
        ):
            raise ValidationError("The selected term belongs to another school.")
        super(ExaminationListHandler, self).clean()


class MarksManagement(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="marks_management")
    exam_name = models.ForeignKey(
        ExaminationListHandler, on_delete=models.CASCADE, related_name="exam_marks"
    )
    points_scored = models.FloatField()
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="subject_marks"
    )
    student = models.ForeignKey(
        StudentClassEnrollment, on_delete=models.CASCADE, related_name="student_marks"
    )
    created_by = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, related_name="marks_entered"
    )
    date_time = models.DateTimeField(auto_now_add=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return f"{self.exam_name} - {self.student} - {self.points_scored}"

    def clean(self):
        if self.points_scored < 0 or self.points_scored > self.exam_name.out_of:
            raise ValidationError(
                f"Points scored must be between 0 and {self.exam_name.out_of}."
            )
        super(MarksManagement, self).clean()

    def _submission_is_locked(self, for_update=False):
        if not all((self.school_id, self.exam_name_id, self.subject_id, self.student_id)):
            return False
        enrollment = self.student
        submissions = MarksSubmission.unfiltered_objects.filter(
            school_id=self.school_id,
            exam_id=self.exam_name_id,
            classroom_id=enrollment.classroom_id,
            subject_id=self.subject_id,
            status__in=(
                MarksSubmission.Status.SUBMITTED,
                MarksSubmission.Status.APPROVED,
                MarksSubmission.Status.RELEASED,
            ),
        )
        if for_update:
            return submissions.select_for_update().first() is not None
        return submissions.exists()

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self._submission_is_locked(for_update=True):
                raise ValidationError(
                    "Marks cannot be changed while this submission is locked. "
                    "An authorized administrator must reopen it first."
                )
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self._submission_is_locked(for_update=True):
                raise ValidationError(
                    "Marks cannot be deleted while this submission is locked. "
                    "An authorized administrator must reopen it first."
                )
            return super().delete(*args, **kwargs)


class MarksSubmission(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        RELEASED = "released", "Released"

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="marks_submissions"
    )
    exam = models.ForeignKey(
        ExaminationListHandler,
        on_delete=models.CASCADE,
        related_name="mark_submissions",
    )
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, related_name="mark_submissions"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="mark_submissions"
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="marks_submitted",
    )
    submitted_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="marks_approved",
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    released_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        ordering = ("exam__name", "classroom__name__name", "subject__name")
        constraints = [
            models.UniqueConstraint(
                fields=("school", "exam", "classroom", "subject"),
                name="unique_marks_submission_scope",
            )
        ]

    def __str__(self):
        return f"{self.exam} — {self.classroom} — {self.subject} ({self.status})"

    def clean(self):
        if (
            self.exam_id
            and self.classroom_id
            and not self.exam.classrooms.filter(pk=self.classroom_id).exists()
        ):
            raise ValidationError(
                {"classroom": "This exam is not assigned to the selected class."}
            )
        for related_object in (self.exam, self.classroom, self.subject):
            if related_object.school_id != self.school_id:
                raise ValidationError(
                    "The exam, class, subject, and submission must belong to one school."
                )


class MarksSubmissionEvent(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        RELEASED = "released", "Released"
        REOPENED = "reopened", "Reopened"

    submission = models.ForeignKey(
        MarksSubmission, on_delete=models.CASCADE, related_name="events"
    )
    action = models.CharField(max_length=12, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True
    )
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("created_at", "pk")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Submission history entries are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Submission history entries cannot be deleted.")