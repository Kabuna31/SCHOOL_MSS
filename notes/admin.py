from django.contrib import admin

from .models import *
from school.admin_utils import enable_import_export


enable_import_export(Assignment)
enable_import_export(GradedAssignment)
enable_import_export(Question)
enable_import_export(Choice)
enable_import_export(SpecificExplanations)
enable_import_export(Concept)
enable_import_export(Note)