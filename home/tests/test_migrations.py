import importlib

from django.test import TestCase
from wagtail.models import Locale, Page, Site

from home.models import ContentPage, OrderedContentSet

rename_duplicate_slugs_0029 = importlib.import_module(
    "home.migrations.0029_deduplicate_slugs"
).rename_duplicate_slugs

rename_duplicate_slugs_0085 = importlib.import_module(
    "home.migrations.0085_orderedcontentset_locale_orderedcontentset_slug"
).rename_duplicate_slugs

set_locale_from_instance = importlib.import_module(
    "home.migrations.0085_orderedcontentset_locale_orderedcontentset_slug"
).set_locale_from_instance


class MigrationTests(TestCase):
    def test_deduplictes_page_slugs(self):
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

    def test_deduplicates_orderedcontentset_slugs(self):
        """
        Renames all ordered content sets with duplicate slugs, so that there are no two
        ordered content sets with the same slug.
        """
        # Create a default locale for testing
        default_locale = Locale.objects.get(language_code="en")

        # Create ordered content sets with duplicate slugs
        OrderedContentSet.objects.create(
            name="first", slug="duplicate", locale=default_locale
        )
        OrderedContentSet.objects.create(
            name="second", slug="duplicate", locale=default_locale
        )
        OrderedContentSet.objects.create(
            name="third", slug="duplicate-2", locale=default_locale
        )
        OrderedContentSet.objects.create(
            name="unique", slug="unique", locale=default_locale
        )

        rename_duplicate_slugs_0085(OrderedContentSet)

        self.assertEqual(
            sorted(OrderedContentSet.objects.values_list("slug", flat=True)),
            [
                "duplicate",
                "duplicate-2",
                "duplicate-3",
                "unique",
            ],
        )

    def test_set_locale_from_instance_with_pages(self):
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

    def test_set_locale_from_instance_without_pages(self):
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
