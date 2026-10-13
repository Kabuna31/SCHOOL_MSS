from rest_framework.routers import DefaultRouter
from django.urls import path
from notes.views import (
    AssignmentViewSet,
    GradedAssignmentCreateView,
    GradedAssignmentListView,
)

router = DefaultRouter()
router.register(r'', AssignmentViewSet)
urlpatterns = [
    path("graded/", GradedAssignmentListView.as_view(), name="graded-assignment-list"),
    path(
        "graded/submit/",
        GradedAssignmentCreateView.as_view(),
        name="graded-assignment-submit",
    ),
]
urlpatterns += router.urls
