from django.urls import path

from examination.views import MarksBulkUploadView, MarksExportView


urlpatterns = [
    path("marks/bulk-upload/", MarksBulkUploadView.as_view(), name="marks-bulk-upload"),
    path("marks/export/", MarksExportView.as_view(), name="marks-export"),
]
