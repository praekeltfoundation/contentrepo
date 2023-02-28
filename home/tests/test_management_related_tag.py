import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from taggit.models import Tag

from home.models import ContentPage, HomePage


class ManagementRelatedTag(TestCase):
    def setUp(self):
        """
        Create a page with no tags or related pages, the `related_page`
        Create a page with a tag pointing to `related_page`, no related pages
        """
        home_page = HomePage.objects.first()
        self.related_page = ContentPage(title="Related page", slug="related-page")
        home_page.add_child(instance=self.related_page)
        self.page = ContentPage(title="Test page", slug="test-page")
        self.page.tags.add(Tag.objects.create(name=f"related_{self.related_page.id}"))
        home_page.add_child(instance=self.page)

    def test_default_dry_run(self):
        """
        Dry run should happen by default, it should log the changes but not make any.
        """
        out = StringIO()

        call_command("change_related_tag_to_related_page", stdout=out)

        self.assertIn(
            f"Added related pages {{{self.related_page.id}}} to {self.page}",
            out.getvalue(),
        )
        self.page.refresh_from_db()
        self.assertEqual(len(self.page.related_pages), 0)
        self.assertIn("Dry run", out.getvalue())

    def test_no_dry_run(self):
        """
        With the --no-dry-run flag, the changes should be comitted to the database.
        Related pages should be added, but no tags should be removed
        """
        out = StringIO()

        call_command("change_related_tag_to_related_page", "--no-dry-run", stdout=out)

        self.assertIn(
            f"Added related pages {{{self.related_page.id}}} to {self.page}",
            out.getvalue(),
        )
        self.page.refresh_from_db()
        self.assertEqual(len(self.page.related_pages), 1)
        self.assertNotIn("Dry run", out.getvalue())

    def test_existing_related_pages(self):
        """
        If for all the tags, the related pages are there already, then no action should
        be taken
        """
        out = StringIO()
        self.page.related_pages = json.dumps(
            [{"type": "related_page", "value": self.related_page.id}]
        )
        self.page.save_revision().publish()

        call_command("change_related_tag_to_related_page", "--no-dry-run", stdout=out)

        self.assertEqual(out.getvalue(), "")
        page = ContentPage.objects.get(id=self.page.id)
        self.assertEqual(page, self.page)

    def test_invalid_tags(self):
        """
        If any of the tags don't point to a valid page ID, then they should be excluded
        """
        out = StringIO()
        self.page.tags.add(Tag.objects.create(name="related_9999"))
        self.page.related_pages = json.dumps([{"type": "related_page", "value": None}])
        self.page.save_revision().publish()

        call_command("change_related_tag_to_related_page", "--no-dry-run", stdout=out)

        page = ContentPage.objects.get(id=self.page.id)
        self.assertEqual(
            [p.value.id for p in page.related_pages], [self.related_page.id]
        )
