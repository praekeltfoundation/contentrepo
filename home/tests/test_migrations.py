import importlib

import pytest
from django.contrib.contenttypes.models import ContentType  # type: ignore
from django.test import TestCase  # type: ignore
from wagtail.models import Locale, Page, Site  # type: ignore

from home.models import (
    ContentPage,
    HomePage,
    OrderedContentSet,
    Revision,
    WhatsAppTemplate,
)
from home.tests.utils import create_page

rename_duplicate_slugs_0029 = importlib.import_module(
    "home.migrations.0029_deduplicate_slugs"
).rename_duplicate_slugs

add_previous_template_names = importlib.import_module(
    "home.migrations.0030_contentpage_whatsapp_template_name"
).add_previous_template_names

update_template_names = importlib.import_module(
    "home.migrations.0041_contentpage_whatsapp_template_lower_case_name"
).update_template_names

rename_duplicate_slugs_0085 = importlib.import_module(
    "home.migrations.0086_orderedcontentset_set_locale_and_add_slug"
).rename_duplicate_slugs

set_locale_from_instance = importlib.import_module(
    "home.migrations.0086_orderedcontentset_set_locale_and_add_slug"
).set_locale_from_instance

set_blank_submission_status_to_not_submitted_yet = importlib.import_module(
    "home.migrations.0096_migrate_empty_submission_status_to_not_submitted_yet"
).set_blank_submission_status_to_not_submitted_yet


class MigrationTests(TestCase):
    def test_deduplictes_page_slugs(self) -> None:
        """
        Renames all pages with duplicate slugs, so that there are no two pages with the
        same slug.
        """
        home = Page.objects.first()
        duplicate = home.add_child(instance=Page(title="duplicate", slug="duplicate"))
        duplicate.add_child(instance=Page(title="duplicate", slug="duplicate"))
        duplicate.add_child(instance=Page(title="duplicate", slug="duplicate-2"))
        home.add_child(instance=Page(title="unique", slug="unique"))

        rename_duplicate_slugs_0029(Page)

        self.assertEqual(
            sorted(Page.objects.values_list("slug", flat=True)),
            [
                "duplicate",
                "duplicate-2",
                "duplicate-3",
                "home",
                "root",
                "unique",
            ],
        )

    def test_deduplicates_orderedcontentset_slugs(self) -> None:
        """
        Renames all ordered content sets with duplicate slugs, so that there are no two
        ordered content sets with the same slug.
        """
        # Get a default locale for testing
        default_locale = Locale.objects.get(language_code="en")
        pt_locale, _created = Locale.objects.get_or_create(language_code="pt")

        # Create ordered content sets with blank slugs
        OrderedContentSet.objects.create(
            name="first   ", slug="", locale=default_locale
        )
        OrderedContentSet.objects.create(name="first", slug="", locale=default_locale)
        OrderedContentSet.objects.create(name="first_pt", slug="", locale=pt_locale)
        OrderedContentSet.objects.create(
            name="third---", slug="", locale=default_locale
        )
        OrderedContentSet.objects.create(
            name="unique  --", slug="", locale=default_locale
        )
        OrderedContentSet.objects.create(
            name="unique-name", slug="", locale=default_locale
        )
        OrderedContentSet.objects.create(
            name="miXeDcaSe", slug="", locale=default_locale
        )

        rename_duplicate_slugs_0085(OrderedContentSet)

        self.assertEqual(
            sorted(OrderedContentSet.objects.values_list("slug", flat=True)),
            [
                "first",
                "first-1",
                "first_pt",
                "mixedcase",
                "third",
                "unique",
                "unique-name",
            ],
        )

    def test_set_locale_from_instance_with_pages(self) -> None:
        """
        When an OrderedContentSet has pages, it should get its locale from the first page
        in its pages list.
        """
        # Get the locales
        default_locale = Locale.objects.get(language_code="en")
        pt_locale, _created = Locale.objects.get_or_create(language_code="pt")

        # Create a content page with the default locale
        root_page = Site.objects.get(is_default_site=True).root_page
        content_page = ContentPage(title="Test Page", locale=default_locale)
        root_page.add_child(instance=content_page)

        # Create an ordered content set with the page but not the default locale
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="test",
            locale=pt_locale,
        )
        ordered_content_set.pages.append(("pages", {"contentpage": content_page}))
        ordered_content_set.save()

        # Run the migration function
        set_locale_from_instance(OrderedContentSet, Site)

        # Verify the locale was set from the page
        ordered_content_set.refresh_from_db()
        self.assertEqual(ordered_content_set.locale, content_page.locale)

    def test_set_locale_from_instance_without_pages(self) -> None:
        """
        When an OrderedContentSet has no pages, it should get its locale from the default
        site's root page locale.
        """
        # Get the default site
        default_site = Site.objects.get(is_default_site=True)
        pt_locale, _created = Locale.objects.get_or_create(language_code="pt")

        # Create an ordered content set without pages and a non-default locale
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="test",
            locale=pt_locale,
        )
        ordered_content_set.save()

        # Run the migration function
        set_locale_from_instance(OrderedContentSet, Site)

        # Verify the locale was set from the default site's root page
        ordered_content_set.refresh_from_db()
        self.assertEqual(ordered_content_set.locale, default_site.root_page.locale)

    def test_migrate_empty_submission_status_to_not_submitted_yet(self) -> None:
        """
        When a WhatsAppTemplate has an empty submission status, it should be set to
        "NOT_SUBMITTED_YET".
        """
        # Create a WhatsAppTemplate with an empty submission status
        template = WhatsAppTemplate.objects.create(
            slug="test-template",
            submission_status="",
            locale=Locale.objects.get(language_code="en"),
        )
        template.save()

        # Run the migration function
        set_blank_submission_status_to_not_submitted_yet(WhatsAppTemplate)

        # Verify the submission status was set to NOT_SUBMITTED_YET
        template.refresh_from_db()
        self.assertEqual(
            template.submission_status,
            WhatsAppTemplate.SubmissionStatus.NOT_SUBMITTED_YET,
        )

    @pytest.mark.xfail(
        reason="This fails because we have removed the whatsapp_template_name field. "
        "While there are ways to test a previous version of a model, the DB won't be synced "
        "up to it, which means you can't perform any operations on it."
    )
    def test_backfills_template_name(self) -> None:
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

    @pytest.mark.xfail(
        reason="This fails because we have removed the whatsapp template fields. "
        "While there are ways to test a previous version of a model, the DB won't be synced "
        "up to it, which means you can't perform any operations on it."
    )
    def test_migrate_content_page_templates_to_standalone_templates(self) -> None:
        """
        When a ContentPage has is_whatsapp_template=True, the migration should create a WhatsAppTemplate
        with the correct fields, set the ContentPage's whatsapp_body to the new WhatsAppTemplate, and set is_whatsapp_template=False.
        """
        locale = Locale.objects.get(language_code="en")
        root_page = HomePage.objects.first()
        content_page = ContentPage(
            title="Test WhatsApp Template Page",
            slug="test-whatsapp-template-page",
            whatsapp_template_name="Test Template",
            locale=locale,
            whatsapp_body=[
                {
                    "type": "Whatsapp_Message",
                    "value": {
                        "message": "Sample body",
                    },
                },
                {
                    "type": "Whatsapp_Message",
                    "value": {
                        "message": "Sample body 2",
                    },
                },
            ],
        )
        root_page.add_child(instance=content_page)
        content_page.whatsapp_template_category = (
            ContentPage.WhatsAppTemplateCategory.UTILITY
        )
        content_page.save_revision().publish()

        migration_module = importlib.import_module(
            "home.migrations.0099_migrate_content_page_templates_to_standalone_templates"
        )
        migrate_func = (
            migration_module.migrate_content_page_templates_to_standalone_templates
        )

        migrate_func(ContentPage, WhatsAppTemplate)

        content_page.refresh_from_db()
        whatsapp_templates = WhatsAppTemplate.objects.filter(
            name="Test Template", locale=locale
        )
        self.assertEqual(whatsapp_templates.count(), 1)
        whatsapp_template = whatsapp_templates.first()

        self.assertEqual(whatsapp_template.name, content_page.whatsapp_template_name)
        self.assertEqual(whatsapp_template.locale, content_page.locale)
        self.assertEqual(whatsapp_template.message, "Sample body")
        self.assertEqual(
            whatsapp_template.category, content_page.whatsapp_template_category
        )
        self.assertEqual(
            whatsapp_template.submission_status,
            WhatsAppTemplate.SubmissionStatus.NOT_SUBMITTED_YET,
        )
        self.assertEqual(whatsapp_template.submission_result, "")

        self.assertFalse(content_page.is_whatsapp_template)

        self.assertEqual(len(content_page.whatsapp_body), 2)
        self.assertEqual(content_page.whatsapp_body[0].value, whatsapp_template)
        self.assertEqual(
            content_page.whatsapp_body[1].value["message"], "Sample body 2"
        )

        whatsapp_template.delete()
        content_page.delete()
