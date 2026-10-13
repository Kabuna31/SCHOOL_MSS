from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from django.urls import resolve
from django_tenants.urlresolvers import get_subfolder_urlconf


class TenantManagementCommandTests(SimpleTestCase):
    @override_settings(TENANT_SUBFOLDER_PREFIX="t")
    def test_tenant_urlconf_is_mounted_under_render_hostname_path(self):
        tenant_urlconf = get_subfolder_urlconf(
            SimpleNamespace(domain_subfolder="school-one")
        )

        match = resolve("/t/school-one/", urlconf=tenant_urlconf)

        self.assertEqual(match.url_name, None)
        self.assertEqual(match.func.__name__, "api_welcome")

    @override_settings(TENANCY_CONFIGURED=False)
    def test_tenant_provisioning_requires_tenancy_configuration(self):
        with self.assertRaisesMessage(
            CommandError,
            "Set TENANCY_PREPARATION=1 or enable django-tenants before provisioning a school.",
        ):
            call_command(
                "create_school_tenant",
                school_id=1,
                schema_name="example",
                slug="example",
            )

    @override_settings(
        TENANCY_CONFIGURED=True,
        TENANT_SUBFOLDER_PREFIX="t",
    )
    @patch("tenants.management.commands.create_school_tenant.connection.vendor", "postgresql")
    @patch("tenants.management.commands.create_school_tenant.schema_context")
    @patch("tenants.management.commands.create_school_tenant.Domain")
    @patch("tenants.management.commands.create_school_tenant.SchoolTenant")
    @patch("tenants.management.commands.create_school_tenant.Day")
    @patch("tenants.management.commands.create_school_tenant.School")
    def test_provisioning_keeps_schema_when_create_schema_returns_none(
        self, school_model, day_model, tenant_model, domain_model, schema_context
    ):
        school = SimpleNamespace(
            name="Example School",
            _meta=SimpleNamespace(concrete_fields=()),
        )
        school_model.objects.get.return_value = school
        tenant_model.objects.filter.return_value.exists.return_value = True
        domain_model.objects.filter.return_value.exists.return_value = False
        tenant = tenant_model.return_value
        tenant.schema_name = "example"
        tenant.create_schema.return_value = None
        day_model.objects.values_list.return_value = [1, 2, 3, 4, 5]
        schema_context.return_value = nullcontext()

        call_command(
            "create_school_tenant",
            school_id=1,
            schema_name="example",
            slug="example",
            verbosity=0,
        )

        tenant.create_schema.assert_called_once_with(check_if_exists=True)
        tenant.delete.assert_not_called()
        domain_model.objects.create.assert_called_once_with(
            domain="example",
            tenant=tenant,
            is_primary=True,
        )

    @override_settings(TENANCY_CONFIGURED=True)
    @patch("tenants.management.commands.create_school_tenant.connection.vendor", "postgresql")
    @patch("tenants.management.commands.create_school_tenant.Domain")
    @patch("tenants.management.commands.create_school_tenant.SchoolTenant")
    @patch("tenants.management.commands.create_school_tenant.School")
    def test_provisioning_refuses_existing_schema_without_dropping_it(
        self, school_model, tenant_model, domain_model
    ):
        school = SimpleNamespace(name="Example School")
        school_model.objects.get.return_value = school
        tenant_model.objects.filter.return_value.exists.return_value = True
        domain_model.objects.filter.return_value.exists.return_value = False
        tenant = tenant_model.return_value
        tenant.create_schema.return_value = False

        with self.assertRaisesMessage(
            CommandError, "Schema 'example' already exists; refusing to reuse it."
        ):
            call_command(
                "create_school_tenant",
                school_id=1,
                schema_name="example",
                slug="example",
                verbosity=0,
            )

        tenant.delete.assert_called_once_with()

    @override_settings(TENANCY_CONFIGURED=True)
    @patch("tenants.management.commands.migrate_deployment.call_command")
    def test_deployment_uses_schema_migrations_when_configured(self, migrate):
        call_command("migrate_deployment", verbosity=0)

        migrate.assert_called_once_with(
            "migrate_schemas",
            interactive=False,
            verbosity=0,
        )

    @override_settings(TENANCY_CONFIGURED=False)
    @patch("tenants.management.commands.migrate_deployment.call_command")
    def test_deployment_uses_standard_migrations_in_legacy_mode(self, migrate):
        call_command("migrate_deployment", verbosity=0)

        migrate.assert_called_once_with(
            "migrate",
            interactive=False,
            verbosity=0,
        )
