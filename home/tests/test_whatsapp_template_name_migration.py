import importlib

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from wagtail.models import Revision

from home.models import ContentPage
from home.tests.utils import create_page

add_previous_template_names = importlib.import_module(
    "home.migrations.0030_contentpage_whatsapp_template_name"
).add_previous_template_names


class WhatsappTemplateNameMigrationTests(TestCase):
    def test_backfills_template_name(self):
        """
        Should fill in the template name in all pages and all their revisions, ignoring
        any non-templates
        """
        page = create_page()
        revision_not_template = page.latest_revision
        page.is_whatsapp_template = True
        revision = page.save_revision()
        revision.publish()

        add_previous_template_names(ContentType, ContentPage, Revision)

        page.refresh_from_db()
        self.assertEqual(page.whatsapp_template_name, f"WA_Title_{revision.pk}")
        revision.refresh_from_db()
        revision_page = revision.as_object()
        self.assertEqual(
            revision_page.whatsapp_template_name, f"WA_Title_{revision.pk}"
        )
        revision_not_template.refresh_from_db()
        revision_not_template_page = revision_not_template.as_object()
        self.assertEqual(revision_not_template_page.whatsapp_template_name, "")
