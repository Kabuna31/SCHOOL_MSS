from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db import connection

from tenants.models import SchoolTenant


class Command(BaseCommand):
    help = "Create the django-tenants public schema registry if it is missing."

    def handle(self, *args, **options):
        if not settings.TENANCY_CONFIGURED:
            raise CommandError("Set TENANCY_PREPARATION=1 before initializing tenancy.")
        if connection.vendor != "postgresql":
            raise CommandError("django-tenants requires PostgreSQL.")

        tenant, created = SchoolTenant.objects.get_or_create(
            schema_name="public",
            defaults={"name": "Public", "school": None},
        )
        action = "Created" if created else "Found"
        self.stdout.write(self.style.SUCCESS(f"{action} public tenant registry."))
