from django.urls import path

from examination.views import (
    MarksBulkUploadView,
    MarksExportView,
    MarksheetView,
    MidTermReportCardsView,
    ReportCardsView,
    ResultAnalysisPDFView,
    ResultAnalysisView,
)


urlpatterns = [
    path("marks/bulk-upload/", MarksBulkUploadView.as_view(), name="marks-bulk-upload"),
    path("marks/export/", MarksExportView.as_view(), name="marks-export"),
    path("reports/report-cards/", ReportCardsView.as_view(), name="report-cards"),
    path(
        "reports/mid-term-report-cards/",
        MidTermReportCardsView.as_view(),
        name="mid-term-report-cards",
    ),
    path("reports/marksheet/", MarksheetView.as_view(), name="marksheet"),
    path("reports/analysis/", ResultAnalysisView.as_view(), name="result-analysis"),
    path(
        "reports/analysis.pdf/",
        ResultAnalysisPDFView.as_view(),
        name="result-analysis-pdf",
    ),
]
