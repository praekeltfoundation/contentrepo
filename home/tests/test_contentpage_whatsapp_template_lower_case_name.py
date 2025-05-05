import importlib

import pytest
from django.contrib.contenttypes.models import ContentType  # type: ignore
from django.test import TestCase  # type: ignore
from wagtail.models import Revision  # type: ignore

from home.models import ContentPage
from home.tests.utils import create_page

update_template_names = importlib.import_module(
    "home.migrations.0041_contentpage_whatsapp_template_lower_case_name"
).update_template_names


class TemplateNameMigration(TestCase):
    @pytest.mark.xfail(
        reason="This fails because we have removed the whatsapp_template_name field. "
        "While there are ways to test a previous version of a model, the DB won't be synced "
        "up to it, which means you can't perform any operations on it."
    )
    def test_template_name_lower_case_migration(self) -> None:
        page = create_page(whatsapp_template_name="WA_Title_1")

        revision = page.save_revision()
        revision.publish()

        update_template_names(ContentPage, ContentType, Revision)

        page.refresh_from_db()
        self.assertEqual(page.whatsapp_template_name, "wa_title_1")
        revision.refresh_from_db()
        revision_page = revision.as_object()
        self.assertEqual(revision_page.whatsapp_template_name, "wa_title_1")

    @pytest.mark.xfail(
        reason="This fails because we have removed the whatsapp_template_name field. "
        "While there are ways to test a previous version of a model, the DB won't be synced "
        "up to it, which means you can't perform any operations on it."
    )
    def test_contentpage_is_not_a_template(self) -> None:
        page = create_page()
        revision_not_template = page.latest_revision

        revision = page.save_revision()
        revision.publish()

        update_template_names(ContentPage, ContentType, Revision)

        self.assertEqual(page.whatsapp_template_name, "")

        revision_not_template.refresh_from_db()
        revision_not_template_page = revision_not_template.as_object()
        self.assertEqual(revision_not_template_page.whatsapp_template_name, "")
