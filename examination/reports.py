import io
import re
from collections import defaultdict
from statistics import mean
from xml.sax.saxutils import escape

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils.text import slugify
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

from academic.models import AllocatedSubject, ClassRoom, StudentClassEnrollment, Teacher
from administration.models import Term
from utils.bulk_imports import get_request_school

from .models import MarksManagement


O_LEVEL_BANDS = (
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (50, "D"),
    (0, "E"),
)
A_LEVEL_BANDS = (
    (80, "D1"),
    (70, "D2"),
    (65, "C3"),
    (60, "C4"),
    (55, "C5"),
    (50, "C6"),
    (45, "P7"),
    (40, "P8"),
    (0, "F9"),
)


class ReportQuerySerializer(serializers.Serializer):
    term_id = serializers.IntegerField(min_value=1)
    classroom_id = serializers.IntegerField(min_value=1)
    student_id = serializers.IntegerField(min_value=1, required=False)


def _class_band(class_name):
    name = re.sub(r"[^a-z0-9]", "", class_name.lower())
    if name in {"s1", "senior1", "seniorone", "seniorfirst"}:
        return "O"
    if name in {"s2", "senior2", "seniortwo", "seniorsecond"}:
        return "O"
    if name in {"s3", "senior3", "seniorthree", "seniorthird"}:
        return "O"
    if name in {"s4", "senior4", "seniorfour", "seniorfourth"}:
        return "O"
    if name in {"s5", "senior5", "seniorfive", "seniorfifth"}:
        return "A"
    if name in {"s6", "senior6", "seniorsix", "seniorsixth"}:
        return "A"
    raise ValidationError(
        "Report bands require class names Senior 1–4/S.1–S.4 or Senior 5–6/S.5–S.6."
    )


def _grade_for(score, band):
    if score is None:
        return ""
    bands = A_LEVEL_BANDS if band == "A" else O_LEVEL_BANDS
    for minimum, grade in bands:
        if score >= minimum:
            return grade
    return bands[-1][1]


def report_scope(request):
    school = get_request_school(request)
    if school is None:
        raise PermissionDenied("Your account is not associated with a school.")

    params = ReportQuerySerializer(data=request.query_params)
    params.is_valid(raise_exception=True)
    values = params.validated_data

    term = (
        Term.objects.select_related("academic_year")
        .filter(pk=values["term_id"], academic_year__school=school)
        .first()
    )
    if term is None:
        raise NotFound("The selected term does not belong to your school.")

    classroom = (
        ClassRoom.objects.select_related("name", "stream", "class_teacher")
        .filter(pk=values["classroom_id"], school=school)
        .first()
    )
    if classroom is None:
        raise NotFound("The selected classroom does not belong to your school.")

    if request.user.is_staff or request.user.is_superuser:
        return school, term, classroom, values.get("student_id")

    teacher = Teacher.objects.filter(user=request.user, school=school).first()
    if teacher is None or not (
        classroom.class_teacher_id == teacher.pk
        or AllocatedSubject.objects.filter(
            school=school,
            class_room=classroom,
            teacher_name=teacher,
            academic_year=term.academic_year,
        ).exists()
    ):
        raise PermissionDenied("You are not authorized to view reports for this class.")

    return school, term, classroom, values.get("student_id")


def build_class_report(
    school, term, classroom, requested_student_id=None, mid_term=False
):
    band = _class_band(classroom.name.name)
    enrollments = list(
        StudentClassEnrollment.objects.filter(
            school=school,
            classroom=classroom,
            academic_year=term.academic_year,
            student__isnull=False,
        )
        .select_related("student")
        .order_by("student__last_name", "student__first_name", "student__admission_number")
    )
    students = []
    seen_student_ids = set()
    for enrollment in enrollments:
        if enrollment.student_id not in seen_student_ids:
            students.append(enrollment.student)
            seen_student_ids.add(enrollment.student_id)

    if requested_student_id is not None:
        students = [student for student in students if student.pk == requested_student_id]
        if not students:
            raise NotFound("The student is not enrolled in this class for the selected year.")
        enrollments = [
            enrollment for enrollment in enrollments
            if enrollment.student_id == requested_student_id
        ]

    enrollment_ids = [enrollment.pk for enrollment in enrollments]
    marks = list(
        MarksManagement.objects.filter(
            school=school,
            student_id__in=enrollment_ids,
            exam_name__term=term,
            exam_name__classrooms=classroom,
        )
        .select_related("exam_name", "subject", "student__student")
        .order_by("subject__name", "exam_name__assessment_type")
    )

    scores = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    subjects = {}
    for mark in marks:
        subjects[mark.subject_id] = mark.subject
        maximum = mark.exam_name.out_of
        if maximum <= 0:
            continue
        percentage = mark.points_scored / maximum * 100
        scores[mark.student.student_id][mark.subject_id][
            mark.exam_name.assessment_type
        ].append(percentage)

    report_students = []
    for student in students:
        subject_results = []
        for subject in sorted(subjects.values(), key=lambda item: item.name.lower()):
            categories = scores[student.pk][subject.pk]
            aoi = mean(categories["AOI"]) if categories["AOI"] else None
            eot = mean(categories["EOT"]) if categories["EOT"] else None
            final_score = 0.2 * aoi + 0.8 * eot if aoi is not None and eot is not None else None
            subject_results.append(
                {
                    "subject": subject,
                    "aoi": round(aoi, 2) if aoi is not None else None,
                    "eot": round(eot, 2) if eot is not None else None,
                    "final": round(final_score, 2) if final_score is not None else None,
                    "grade": _grade_for(
                        aoi if mid_term else final_score,
                        band,
                    ),
                }
            )
        completed_scores = [
            result["aoi"] if mid_term else result["final"]
            for result in subject_results
            if (result["aoi"] if mid_term else result["final"]) is not None
        ]
        report_students.append(
            {
                "student": student,
                "subjects": subject_results,
                "average": round(mean(completed_scores), 2) if completed_scores else None,
                "completed_subjects": len(completed_scores),
            }
        )

    ranked = sorted(
        (
            item for item in report_students
            if item["average"] is not None
        ),
        key=lambda item: (-item["average"], item["student"].last_name or "", item["student"].first_name or ""),
    )
    previous_average = None
    current_rank = 0
    for index, item in enumerate(ranked, start=1):
        if item["average"] != previous_average:
            current_rank = index
        item["rank"] = current_rank
        previous_average = item["average"]
    for item in report_students:
        item.setdefault("rank", None)

    analysis = []
    for subject in sorted(subjects.values(), key=lambda item: item.name.lower()):
        completed = [
            item["final"]
            for student_report in report_students
            for item in student_report["subjects"]
            if item["subject"].pk == subject.pk and item["final"] is not None
        ]
        grades = defaultdict(int)
        for score in completed:
            grades[_grade_for(score, band)] += 1
        pass_mark = 40 if band == "A" else 50
        analysis.append(
            {
                "subject": subject,
                "students_completed": len(completed),
                "average": round(mean(completed), 2) if completed else None,
                "highest": round(max(completed), 2) if completed else None,
                "lowest": round(min(completed), 2) if completed else None,
                "pass_rate": (
                    round(sum(score >= pass_mark for score in completed) * 100 / len(completed), 2)
                    if completed
                    else None
                ),
                "grade_counts": dict(grades),
            }
        )

    class_averages = [
        item["average"] for item in report_students if item["average"] is not None
    ]
    return {
        "school": school,
        "term": term,
        "classroom": classroom,
        "band": band,
        "students": report_students,
        "subjects": list(sorted(subjects.values(), key=lambda item: item.name.lower())),
        "analysis": analysis,
        "class_average": round(mean(class_averages), 2) if class_averages else None,
        "students_enrolled": len(report_students),
        "students_with_results": len(class_averages),
    }


def _pdf_response(filename, story, pagesize=A4):
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=pagesize,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=filename,
    )
    document.build(story)
    response = HttpResponse(output.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SchoolTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=17,
            leading=20,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Heading2"],
            alignment=TA_CENTER,
            fontSize=11,
            leading=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="HeaderCell",
            parent=styles["BodyText"],
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
            textColor=colors.white,
        )
    )
    return styles


def _heading(data, styles, subtitle):
    elements = []
    try:
        if data["school"].school_logo and data["school"].school_logo.path:
            logo = Image(data["school"].school_logo.path, width=18 * mm, height=18 * mm)
            logo.hAlign = "CENTER"
            elements.append(logo)
    except (OSError, ValueError):
        pass
    elements.extend(
        [
            Paragraph(escape(data["school"].name), styles["SchoolTitle"]),
            Paragraph(
                escape(" | ".join(
                    value
                    for value in (
                        data["school"].address,
                        data["school"].telephone,
                        data["school"].school_email or "",
                    )
                    if value
                )),
                styles["Normal"],
            ),
            Paragraph(subtitle, styles["ReportSubtitle"]),
            Paragraph(
                escape(
                    f"{data['classroom']} | {data['term'].name} "
                    f"{data['term'].academic_year.name}"
                ),
                styles["Normal"],
            ),
            Spacer(1, 6 * mm),
        ]
    )
    return elements


def report_cards_pdf(data, mid_term=False):
    styles = _styles()
    story = []
    for index, item in enumerate(data["students"]):
        if index:
            story.append(PageBreak())
        student = item["student"]
        title = "MID-TERM ACADEMIC REPORT" if mid_term else "STUDENT ACADEMIC REPORT"
        story.extend(_heading(data, styles, title))
        details = Table(
            [
                [
                    f"Student: {escape(student.full_name)}",
                    f"Admission No: {escape(student.admission_number or '—')}",
                    f"Position: {item['rank'] or '—'}",
                ],
                [
                    f"Class: {data['classroom'].name.name}",
                    f"Stream: {data['classroom'].stream.name if data['classroom'].stream_id else '—'}",
                    f"Average: {item['average'] if item['average'] is not None else '—'}%",
                ],
            ],
            colWidths=[70 * mm, 65 * mm, 45 * mm],
        )
        details.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(details)
        rows = (
            [["SUBJECT", "AOI AVERAGE / 100%", "GRADE"]]
            if mid_term
            else [["SUBJECT", "AOI / 20%", "EOT / 80%", "FINAL / 100%", "GRADE"]]
        )
        for result in item["subjects"]:
            if mid_term:
                rows.append(
                    [
                        result["subject"].name,
                        result["aoi"] if result["aoi"] is not None else "—",
                        result["grade"] or "—",
                    ]
                )
            else:
                rows.append(
                    [
                        result["subject"].name,
                        result["aoi"] if result["aoi"] is not None else "—",
                        result["eot"] if result["eot"] is not None else "—",
                        result["final"] if result["final"] is not None else "—",
                        result["grade"] or "—",
                    ]
                )
        col_widths = [100 * mm, 55 * mm, 35 * mm] if mid_term else [
            75 * mm, 35 * mm, 35 * mm, 40 * mm, 25 * mm
        ]
        table = Table(rows, repeatRows=1, colWidths=col_widths)
        table.setStyle(_table_style())
        story.extend([Spacer(1, 5 * mm), table, Spacer(1, 13 * mm)])
        story.append(
            Table(
                [["Class Teacher's Comment: ________________________________________________"],
                 ["Head Teacher's Comment: _________________________________________________"],
                 ["Class Teacher: _________________________", "Head Teacher: _________________________"]],
                colWidths=[105 * mm, 95 * mm],
                style=TableStyle(
                    [
                        ("SPAN", (0, 0), (1, 0)),
                        ("SPAN", (0, 1), (1, 1)),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            )
        )
        story.append(Paragraph("This report is valid only when signed and stamped by the school.", styles["Normal"]))
    if not data["students"]:
        story.extend(_heading(data, styles, "STUDENT ACADEMIC REPORT"))
        story.append(Paragraph("No students are enrolled in this class for the selected academic year.", styles["Normal"]))
    return _pdf_response(
        f"{slugify(str(data['classroom']))}-{slugify(data['term'].name)}"
        f"-{'mid-term-' if mid_term else ''}report-cards.pdf",
        story,
        pagesize=landscape(A4),
    )


def _table_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9EADBD")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4F8")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def marksheet_pdf(data):
    styles = _styles()
    story = _heading(data, styles, "CLASS MARKSHEET")
    headers = ["NO.", "ADMISSION NO.", "STUDENT"]
    headers.extend(
        f"{escape(subject.name)}\nAOI / EOT / FINAL"
        for subject in data["subjects"]
    )
    headers.append("AVERAGE")
    rows = [[Paragraph(value.replace("\n", "<br/>"), styles["HeaderCell"]) for value in headers]]
    for index, item in enumerate(data["students"], start=1):
        student = item["student"]
        row = [
            index,
            escape(student.admission_number or "—"),
            escape(student.full_name or "—"),
        ]
        for subject in data["subjects"]:
            result = next(
                result for result in item["subjects"] if result["subject"].pk == subject.pk
            )
            row.append(
                "/".join(
                    str(value) if value is not None else "—"
                    for value in (result["aoi"], result["eot"], result["final"])
                )
            )
        row.append(item["average"] if item["average"] is not None else "—")
        rows.append(row)

    page_size = landscape(A3)
    available_width = page_size[0] - 24 * mm
    fixed_width = 10 * mm + 25 * mm + 45 * mm + 15 * mm
    score_width = max(
        15 * mm,
        (available_width - fixed_width) / max(len(data["subjects"]), 1),
    )
    col_widths = [10 * mm, 25 * mm, 45 * mm] + [score_width] * len(data["subjects"]) + [15 * mm]
    table = Table(rows, repeatRows=1, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(_table_style())
    story.extend([Spacer(1, 5 * mm), table])
    return _pdf_response(
        f"{slugify(str(data['classroom']))}-{slugify(data['term'].name)}-marksheet.pdf",
        story,
        pagesize=page_size,
    )


def analysis_payload(data):
    ranked = sorted(
        (
            item for item in data["students"]
            if item["average"] is not None
        ),
        key=lambda item: item["rank"],
    )
    return {
        "school": data["school"].name,
        "classroom": str(data["classroom"]),
        "term": data["term"].name,
        "academic_year": data["term"].academic_year.name,
        "level": "A-Level" if data["band"] == "A" else "O-Level",
        "weighting": {"AOI": 20, "EOT": 80},
        "students_enrolled": data["students_enrolled"],
        "students_with_results": data["students_with_results"],
        "class_average": data["class_average"],
        "subjects": [
            {
                "name": result["subject"].name,
                "students_completed": result["students_completed"],
                "average": result["average"],
                "highest": result["highest"],
                "lowest": result["lowest"],
                "pass_rate": result["pass_rate"],
                "grade_counts": result["grade_counts"],
            }
            for result in data["analysis"]
        ],
        "ranked_students": [
            {
                "rank": item["rank"],
                "admission_number": item["student"].admission_number,
                "student": item["student"].full_name,
                "average": item["average"],
            }
            for item in ranked
        ],
    }


def analysis_pdf(data):
    styles = _styles()
    story = _heading(data, styles, "CLASS RESULT ANALYSIS")
    story.append(
        Paragraph(
            f"Level: {'A-Level' if data['band'] == 'A' else 'O-Level'}"
            f" &nbsp; | &nbsp; Students enrolled: {data['students_enrolled']}"
            f" &nbsp; | &nbsp; With complete results: {data['students_with_results']}"
            f" &nbsp; | &nbsp; Class average: "
            f"{data['class_average'] if data['class_average'] is not None else '—'}%",
            styles["Normal"],
        )
    )
    subject_rows = [["SUBJECT", "COMPLETE", "AVERAGE", "HIGHEST", "LOWEST", "PASS RATE"]]
    for result in data["analysis"]:
        subject_rows.append(
            [
                escape(result["subject"].name),
                result["students_completed"],
                result["average"] if result["average"] is not None else "—",
                result["highest"] if result["highest"] is not None else "—",
                result["lowest"] if result["lowest"] is not None else "—",
                f"{result['pass_rate']}%" if result["pass_rate"] is not None else "—",
            ]
        )
    subject_table = Table(subject_rows, repeatRows=1, colWidths=[62 * mm, 25 * mm, 28 * mm, 28 * mm, 28 * mm, 30 * mm])
    subject_table.setStyle(_table_style())
    story.extend([Spacer(1, 5 * mm), subject_table, Spacer(1, 7 * mm)])

    ranking_rows = [["RANK", "ADMISSION NO.", "STUDENT", "AVERAGE"]]
    ranking_rows.extend(
        [
            item["rank"],
            escape(item["student"].admission_number or "—"),
            escape(item["student"].full_name or "—"),
            f"{item['average']}%",
        ]
        for item in sorted(
            (entry for entry in data["students"] if entry["average"] is not None),
            key=lambda entry: entry["rank"],
        )
    )
    ranking_table = Table(ranking_rows, repeatRows=1, colWidths=[20 * mm, 40 * mm, 90 * mm, 30 * mm])
    ranking_table.setStyle(_table_style())
    story.append(ranking_table)
    return _pdf_response(
        f"{slugify(str(data['classroom']))}-{slugify(data['term'].name)}-analysis.pdf",
        story,
        pagesize=landscape(A4),
    )
