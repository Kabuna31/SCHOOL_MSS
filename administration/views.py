import openpyxl
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import generics, viewsets, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from utils.bulk_imports import (
    date_value,
    excel_response,
    get_request_school,
    iter_excel_rows,
    text_value,
)
from .models import AcademicYear, Term, Article, CarouselImage, SchoolEvent
from .serializers import (
    AcademicYearSerializer,
    TermSerializer,
    ArticleSerializer,
    CarouselImageSerializer,
    SchoolEventSerializer,
)
from .permissions import IsAdminOrReadOnly


# Article Views
class ArticleListCreateView(generics.ListCreateAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]


class ArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]


# CarouselImage Views
class CarouselImageListCreateView(generics.ListCreateAPIView):
    queryset = CarouselImage.objects.all()
    serializer_class = CarouselImageSerializer
    permission_classes = [IsAuthenticated]


class CarouselImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CarouselImage.objects.all()
    serializer_class = CarouselImageSerializer
    permission_classes = [IsAuthenticated]


# AcademicYear Views
class AcademicYearListCreateView(generics.ListCreateAPIView):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        print(request.data)
        return super().create(request, *args, **kwargs)


class AcademicYearDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated]


# Term Views
class TermListCreateView(generics.ListCreateAPIView):
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        print(request.data)
        return super().create(request, *args, **kwargs)


class TermDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [IsAuthenticated]


class SchoolEventViewSet(viewsets.ModelViewSet):
    queryset = SchoolEvent.objects.select_related("term", "term__academic_year").all()
    serializer_class = SchoolEventSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = self.queryset
        term_id = self.request.query_params.get("term")
        year_name = self.request.query_params.get("academic_year")
        start_date = parse_date(self.request.query_params.get("start_date") or "")
        end_date = parse_date(self.request.query_params.get("end_date") or "")

        if term_id:
            queryset = queryset.filter(term__id=term_id)
        if year_name:
            queryset = queryset.filter(term__academic_year__name=year_name)
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        return queryset


class SchoolEventBulkUploadView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        excel_file = request.FILES.get("file")
        if not excel_file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        columns = ["name", "event_type", "term_id", "start_date", "end_date", "description"]
        created = 0
        errors = []
        try:
            for row_number, row_data in iter_excel_rows(excel_file, columns):
                try:
                    name = text_value(row_data["name"])
                    event_type = text_value(row_data["event_type"]).lower()
                    term_id = text_value(row_data["term_id"])
                    start_date = date_value(row_data["start_date"], "Start date")
                    end_date = (
                        date_value(row_data["end_date"], "End date")
                        if row_data["end_date"]
                        else None
                    )
                    description = text_value(row_data["description"])
                    if not name or not event_type or not term_id:
                        raise ValueError("Name, event type, and term ID are required.")
                    valid_event_types = {
                        value for value, _label in SchoolEvent.EVENT_TYPE_CHOICES
                    }
                    if event_type not in valid_event_types:
                        raise ValueError("Event type is not supported.")
                    term = Term.objects.get(
                        pk=term_id, academic_year__school=school
                    )
                    event = SchoolEvent(
                        name=name,
                        event_type=event_type,
                        term=term,
                        start_date=start_date,
                        end_date=end_date,
                        description=description,
                    )
                    event.full_clean()
                    event.save()
                    created += 1
                except (ValueError, TypeError, Term.DoesNotExist, ValidationError) as exc:
                    errors.append({"row": row_number, "data": row_data, "error": str(exc)})

            return Response(
                {"detail": f"{created} events uploaded successfully.", "not_created": errors},
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


class SchoolEventExportView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        school = get_request_school(request)
        if school is None:
            return Response(
                {"error": "Your account is not associated with a school."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        events = SchoolEvent.objects.filter(
            term__academic_year__school=school
        ).select_related("term")
        rows = (
            (
                event.name,
                event.event_type,
                event.term_id,
                event.start_date,
                event.end_date,
                event.description,
            )
            for event in events
        )
        return excel_response(
            "school_events.xlsx",
            "School Events",
            ["name", "event_type", "term_id", "start_date", "end_date", "description"],
            rows,
        )


class SchoolEventTemplateDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "School Events Template"

        # Headers
        headers = [
            "name",
            "event_type",
            "term_id",
            "start_date",
            "end_date",
            "description",
        ]
        ws.append(headers)

        # Example row
        ws.append(
            [
                "Midterm Exams",
                "exam",
                1,
                "2025-07-10",
                "2025-07-14",
                "Midterm assessment",
            ]
        )

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            "attachment; filename=school_events_template.xlsx"
        )
        wb.save(response)
        return response
