import logging
from datetime import date, datetime
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from user_agents import parse

from .common_objs import *


logger = logging.getLogger(__name__)


class School(models.Model):
    active = models.BooleanField(
        default=False,
        help_text="DANGER..!!!! If marked, this will be the default School Information System Wide...",
    )
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=250)
    school_type = models.CharField(
        max_length=25, choices=SCHOOL_TYPE_CHOICE, blank=True, null=True
    )
    students_gender = models.CharField(
        max_length=25, choices=SCHOOL_STUDENTS_GENDER, blank=True, null=True
    )
    ownership = models.CharField(
        max_length=25, choices=SCHOOL_OWNERSHIP, blank=True, null=True
    )
    mission = models.TextField(blank=True, null=True)
    vision = models.TextField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True)
    school_email = models.EmailField(blank=True, null=True)
    school_logo = models.ImageField(blank=True, null=True, upload_to="school_info")

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["active"]),
        ]
        ordering = ["name"]


class Article(models.Model):
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="articles", null=True, blank=True
    )
    title = models.CharField(max_length=150, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    picture = models.ImageField(upload_to="articles", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or "Untitled Article"


class CarouselImage(models.Model):
    title = models.CharField(max_length=150, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    picture = models.ImageField(upload_to="carousel")

    def __str__(self):
        return self.title or "Carousel Image"


class AccessLog(models.Model):
    login = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    ua = models.CharField(
        max_length=2000,
        help_text="User agent. We can use this to determine operating system and browser in use.",
    )
    date = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField()
    usage = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.login} - {self.usage} on {self.date}"

    def os(self):
        try:
            user_agent = parse(self.ua)
            return user_agent.os.family
        except Exception:
            logger.warning("Could not extract operating system from access log.")
            return "Unknown"

    def browser(self):
        try:
            user_agent = parse(self.ua)
            return user_agent.browser.family
        except Exception:
            logger.warning("Could not extract browser from access log.")
            return "Unknown"

    class Meta:
        indexes = [
            models.Index(fields=["login"]),
            models.Index(fields=["date"]),
        ]


class Day(models.Model):
    DEFAULT_DAY_NUMBERS = (1, 2, 3, 4, 5)

    DAY_CHOICES = (
        (1, "Monday"),
        (2, "Tuesday"),
        (3, "Wednesday"),
        (4, "Thursday"),
        (5, "Friday"),
        (6, "Saturday"),
        (7, "Sunday"),
    )
    day = models.IntegerField(choices=DAY_CHOICES, unique=True)

    def __str__(self):
        return self.get_day_display()

    class Meta:
        ordering = ("day",)


class AcademicYear(models.Model):
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="academic_years", null=True, blank=True
    )
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    active_year = models.BooleanField(
        help_text="DANGER!! This is the current school year. "
        "There can only be one active year per school."
    )

    class Meta:
        ordering = ("-start_date",)

    def __str__(self):
        return self.name

    @property
    def status(self):
        now_ = date.today()
        if self.active_year:
            return "active"
        elif self.end_date and self.start_date <= now_ <= self.end_date:
            return "pending"
        elif self.end_date and now_ > self.end_date:
            return "ended"
        return "unknown"

    def save(self, *args, **kwargs):
        if self.active_year:
            # Ensure only one active year per school
            AcademicYear.objects.filter(school=self.school).exclude(pk=self.pk).update(active_year=False)
        super().save(*args, **kwargs)

    def clean(self):
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("End date must be after start date.")


class Term(models.Model):
    name = models.CharField(max_length=50)
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="terms"
    )
    default_term_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=312500
    )
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.name} - {self.academic_year.name}"


class SchoolEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ("exam", "Examination Period"),
        ("graduation", "Graduation Day"),
        ("holiday", "Holiday"),
        ("leave", "Student Leave"),
        ("other", "Other Event"),
    ]

    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name="events",
        help_text="The term this event belongs to",
    )
    name = models.CharField(
        max_length=255, help_text="Name of the event (e.g., Midterm Exams, Eid Holiday)"
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(
        blank=True, help_text="Optional details about the event"
    )

    class Meta:
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.name} ({self.term.name} - {self.term.academic_year.name})"

    def clean(self):
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("End date must be after start date.")
        if not (self.term.start_date <= self.start_date <= self.term.end_date):
            raise ValidationError("Start date must be within the term's duration.")
        if self.end_date and not (
            self.term.start_date <= self.end_date <= self.term.end_date
        ):
            raise ValidationError("End date must be within the term's duration.")