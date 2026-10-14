from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django_tenants.utils import schema_context

from automation.dispatcher import process_outbox
from tenants.models import SchoolTenant


class Command(BaseCommand):
    help = "Send queued email and SMS notifications and retry eligible failures."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1 or limit > 1000:
            raise CommandError("--limit must be between 1 and 1000.")

        if settings.TENANCY_ENABLED:
            totals = {"processed": 0, "sent": 0, "failed": 0}
            for tenant in SchoolTenant.objects.exclude(schema_name="public").iterator():
                if tenant.school_id is None:
                    self.stderr.write(
                        f"{tenant.schema_name}: skipped because no school is linked."
                    )
                    continue
                with schema_context(tenant.schema_name):
                    result = process_outbox(limit=limit, school_id=tenant.school_id)
                for key in totals:
                    totals[key] += result[key]
                self.stdout.write(f"{tenant.schema_name}: {result}")
        else:
            totals = process_outbox(limit=limit)

        self.stdout.write(
            self.style.SUCCESS(
                "Notification outbox: "
                f"{totals['processed']} processed, {totals['sent']} sent, "
                f"{totals['failed']} failed."
            )
        )
