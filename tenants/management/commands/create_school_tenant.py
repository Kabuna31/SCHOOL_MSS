import re

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import schema_context

from administration.models import Day, School
from tenants.models import Domain, SchoolTenant


class Command(BaseCommand):
    help = "Create a PostgreSQL schema and path tenant for an existing school."

    def add_arguments(self, parser):
        parser.add_argument("--school-id", type=int, required=True)
        parser.add_argument("--schema-name", required=True)
        parser.add_argument(
            "--slug",
            help="Tenant URL slug. Defaults to --schema-name.",
        )

    def handle(self, *args, **options):
        if not settings.TENANCY_CONFIGURED:
            raise CommandError(
                "Set TENANCY_PREPARATION=1 or enable django-tenants before "
                "provisioning a school."
            )
        if connection.vendor != "postgresql":
            raise CommandError("School schemas can only be created on PostgreSQL.")

        schema_name = options["schema_name"].lower()
        tenant_slug = (options["slug"] or schema_name).lower()
        if len(tenant_slug) > 63 or not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", tenant_slug
        ):
            raise CommandError(
                "Tenant URL slugs must be at most 63 lowercase letters, "
                "numbers, or hyphen-separated segments."
            )

        try:
            school = School.objects.get(pk=options["school_id"])
        except School.DoesNotExist as exc:
            raise CommandError(
                f"No public school record exists with id {options['school_id']}."
            ) from exc

        if not SchoolTenant.objects.filter(schema_name="public").exists():
            raise CommandError(
                "Create the public tenant registry first with "
                "`python manage.py ensure_public_tenant`."
            )

        if Domain.objects.filter(domain=tenant_slug).exists():
            raise CommandError(f"Tenant URL slug {tenant_slug!r} is already in use.")

        tenant = SchoolTenant(
            schema_name=schema_name,
            name=school.name,
            school=school,
        )
        tenant.save()

        if tenant.create_schema(check_if_exists=True) is False:
            tenant.delete()
            raise CommandError(
                f"Schema {schema_name!r} already exists; refusing to reuse it."
            )

        try:
            school_data = {
                field.attname: getattr(school, field.attname)
                for field in school._meta.concrete_fields
            }
            day_data = list(Day.objects.values_list("day", flat=True))

            with schema_context(tenant.schema_name):
                School.objects.create(**school_data)
                Day.objects.bulk_create([Day(day=day) for day in day_data])

            Domain.objects.create(
                domain=tenant_slug,
                tenant=tenant,
                is_primary=True,
            )
        except Exception:
            tenant.delete(force_drop=True)
            raise

        self.stdout.write(
            self.style.SUCCESS(
                f"Created tenant schema {schema_name!r}; "
                f"tenant URL prefix is /{settings.TENANT_SUBFOLDER_PREFIX}/{tenant_slug}/."
            )
        )
