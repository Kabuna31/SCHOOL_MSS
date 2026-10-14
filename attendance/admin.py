from django.contrib import admin

from .models import *
from school.admin_utils import enable_import_export


enable_import_export(AttendanceStatus)
enable_import_export(TeachersAttendance)
enable_import_export(StudentAttendance)
enable_import_export(PeriodAttendance)