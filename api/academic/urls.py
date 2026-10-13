from django.urls import path
from academic.views import (
    SubjectListView,
    SubjectDetailView,
    BulkUploadSubjectsView,
    SubjectsExportView,
    ClassRoomView,
    BulkUploadClassRoomsView,
    ClassRoomsExportView,
    DepartmentListCreateView,
    DepartmentDetailView,
    ClassLevelListCreateView,
    ClassLevelDetailView,
    GradeLevelListCreateView,
    GradeLevelDetailView,
    ClassYearListCreateView,
    ClassYearDetailView,
    ReasonLeftListCreateView,
    ReasonLeftDetailView,
    StreamListCreateView,
    StreamDetailView,
    StudentClassListCreateView,
    StudentClassDetailView,
    BulkUploadStudentClassView,
    StudentClassesExportView,
)


urlpatterns = [
    # Department URLs
    path(
        "departments/",
        DepartmentListCreateView.as_view(),
        name="department-list-create",
    ),
    path(
        "departments/<int:pk>/",
        DepartmentDetailView.as_view(),
        name="department-detail",
    ),
    # ClassLevel URLs
    path(
        "class-levels/",
        ClassLevelListCreateView.as_view(),
        name="class-level-list-create",
    ),
    path(
        "class-levels/<int:pk>/",
        ClassLevelDetailView.as_view(),
        name="class-level-detail",
    ),
    # GradeLevel URLs
    path(
        "grade-levels/",
        GradeLevelListCreateView.as_view(),
        name="grade-level-list-create",
    ),
    path(
        "grade-levels/<int:pk>/",
        GradeLevelDetailView.as_view(),
        name="grade-level-detail",
    ),
    # ClassYear URLs
    path(
        "class-years/", ClassYearListCreateView.as_view(), name="class-year-list-create"
    ),
    path(
        "class-years/<int:pk>/", ClassYearDetailView.as_view(), name="class-year-detail"
    ),
    # ReasonLeft URLs
    path(
        "reasons-left/",
        ReasonLeftListCreateView.as_view(),
        name="reason-left-list-create",
    ),
    path(
        "reasons-left/<int:pk>/",
        ReasonLeftDetailView.as_view(),
        name="reason-left-detail",
    ),
    # Stream URLs
    path("streams/", StreamListCreateView.as_view(), name="stream-list-create"),
    path("streams/<int:pk>/", StreamDetailView.as_view(), name="stream-detail"),
    path("subjects/", SubjectListView.as_view(), name="subject-list"),
    path("subjects/<int:id>/", SubjectDetailView.as_view(), name="subject-detail"),
    path(
        "subjects/bulk-upload/",
        BulkUploadSubjectsView.as_view(),
        name="subject-bulk-upload",
    ),
    path("subjects/export/", SubjectsExportView.as_view(), name="subject-export"),
    path("classrooms/", ClassRoomView.as_view(), name="classroom-list"),
    path(
        "classrooms/bulk-upload/",
        BulkUploadClassRoomsView.as_view(),
        name="bulk-upload-classrooms",
    ),
    path(
        "classrooms/export/",
        ClassRoomsExportView.as_view(),
        name="classrooms-export",
    ),
    # StudentClass URLs
    path(
        "student-classes/",
        StudentClassListCreateView.as_view(),
        name="student-class-list-create",
    ),
    path(
        "student-classes/<int:pk>/",
        StudentClassDetailView.as_view(),
        name="student-class-detail",
    ),
    path(
        "student-classes/bulk-upload/",
        BulkUploadStudentClassView.as_view(),
        name="student-class-bulk-upload",
    ),
    path(
        "student-classes/export/",
        StudentClassesExportView.as_view(),
        name="student-classes-export",
    ),
]
