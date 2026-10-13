from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Apply database migrations using the configured database layout."

    def handle(self, *args, **options):
        if settings.TENANCY_CONFIGURED:
            call_command("migrate_schemas", interactive=False, verbosity=options["verbosity"])
        else:
            call_command("migrate", interactive=False, verbosity=options["verbosity"])
