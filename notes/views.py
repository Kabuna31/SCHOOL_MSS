from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from academic.models import Parent
from .models import Assignment, GradedAssignment
from .serializers import (
    AssignmentSerializer,
    GradedAssignmentSerializer,
    GradedAssignmentSubmissionSerializer,
)


def get_request_parent(request):
    try:
        return Parent.objects.select_related("school").get(user=request.user)
    except Parent.DoesNotExist:
        raise PermissionDenied("Only parent accounts can access graded assignments.")


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    queryset = Assignment.objects.all()

    def create(self, request):
        serializer = AssignmentSerializer(data=request.data)
        if serializer.is_valid():
            assignment = serializer.create(request)
            if assignment:
                return Response(status=HTTP_201_CREATED)
        return Response(status=HTTP_400_BAD_REQUEST)


class GradedAssignmentListView(ListAPIView):
    serializer_class = GradedAssignmentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        parent = get_request_parent(self.request)
        return GradedAssignment.objects.filter(
            student__parent_guardian=parent,
            student__school_id=parent.school_id,
        ).select_related("student", "assignment")


class GradedAssignmentCreateView(CreateAPIView):
    serializer_class = GradedAssignmentSubmissionSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["parent"] = get_request_parent(self.request)
        return context

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        graded_assignment = serializer.save()
        response_serializer = GradedAssignmentSerializer(
            graded_assignment, context=self.get_serializer_context()
        )
        return Response(response_serializer.data, status=HTTP_201_CREATED)
