from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.utils.dateparse import parse_date
from django.utils import timezone
from django_tenants.utils import schema_context

from administration.models import School
from automation.rules import process_school_automation
from tenants.models import SchoolTenant


class Command(BaseCommand):
    help = "Create enabled attendance, fee, and school-event notifications."

    def add_arguments(self, parser):
        parser.add_argument("--school-id", type=int)
        parser.add_argument(
            "--date",
            dest="run_date",
            help="Use a specific YYYY-MM-DD date (defaults to the local date).",
        )

    def handle(self, *args, **options):
        run_date = options["run_date"]
        if run_date:
            run_date = parse_date(run_date)
            if run_date is None:
                raise CommandError("--date must use YYYY-MM-DD format.")
        else:
            run_date = timezone.localdate()

        school_id = options["school_id"]
        totals = {"attendance": 0, "fees": 0, "events": 0, "timetable": 0}
        processed_schools = 0

        if settings.TENANCY_ENABLED:
            tenants = SchoolTenant.objects.exclude(schema_name="public").select_related(
                "school"
            )
            if school_id is not None:
                tenants = tenants.filter(school_id=school_id)
            for tenant in tenants.iterator():
                if tenant.school_id is None:
                    self.stderr.write(
                        f"{tenant.schema_name}: skipped because no school is linked."
                    )
                    continue
                with schema_context(tenant.schema_name):
                    result = process_school_automation(tenant.school, run_date)
                self._add_totals(totals, result)
                processed_schools += 1
                self.stdout.write(f"{tenant.schema_name}: {result}")
        else:
            schools = School.objects.all().order_by("pk")
            if school_id is not None:
                schools = schools.filter(pk=school_id)
            if school_id is not None and not schools.exists():
                raise CommandError(f"School {school_id} was not found.")
            for school in schools.iterator():
                result = process_school_automation(school, run_date)
                self._add_totals(totals, result)
                processed_schools += 1
                self.stdout.write(f"{school.name}: {result}")

        if school_id is not None and settings.TENANCY_ENABLED and not processed_schools:
            raise CommandError(
                f"No provisioned tenant was found for school {school_id}."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Automation checked {processed_schools} school(s): "
                f"{totals['attendance']} attendance, {totals['fees']} fee, and "
                f"{totals['events']} event/exam, and {totals['timetable']} "
                "timetable notifications created."
            )
        )

    @staticmethod
    def _add_totals(totals, result):
        for category, count in result.items():
            totals[category] += count
