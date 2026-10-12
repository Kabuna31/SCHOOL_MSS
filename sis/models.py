from django.db import models
from administration.managers import SchoolScopedManager
from administration.models import School


class StudentBulkUpload(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="sis_student_bulk_uploads")
    date_uploaded = models.DateTimeField(auto_now=True)
    csv_file = models.FileField(upload_to="api/sis/students/bulkupload")

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    def __str__(self):
        return f"Bulk Upload ({self.date_uploaded.strftime('%Y-%m-%d %H:%M')})"


class Student(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="sis_students")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    admission_number = models.CharField(max_length=50)

    objects = SchoolScopedManager()
    unfiltered_objects = models.Manager()

    class Meta:
        constraints = [
            # Ensures admission numbers are unique per school, allowing different schools to use the same numbers
            models.UniqueConstraint(fields=["school", "admission_number"], name="unique_sis_school_admission_number")
        ]
        ordering = ["admission_number", "last_name", "first_name"]

    def __str__(self):
        return f"{self.admission_number} - {self.first_name} {self.last_name}"