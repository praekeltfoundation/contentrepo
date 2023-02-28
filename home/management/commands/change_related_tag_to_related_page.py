import json

from django.core.management.base import BaseCommand
from wagtail.models import Page

from home.models import ContentPage


class Command(BaseCommand):
    help = (
        "Takes all 'related_<id>' tags, and adds them as related pages. Does not "
        "remove any tags. Only acts on live pages. If all the related pages specified "
        "by tags are already there, then no action is taken. Publishes a new revision "
        "with related pages added."
    )
    TAG_PREFIX = "related_"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-dry-run",
            action="store_true",
            help="By default we do a dry run. Use this to actually execute the command",
        )

    def handle(self, *args, **options):
        pages = (
            ContentPage.objects.live()
            .filter(tags__name__startswith=self.TAG_PREFIX)
            .distinct()
        )
        for page in pages:
            related_pages = set(
                p.value.id if p.value else None for p in page.related_pages
            )
            existing_related_pages = related_pages.copy()
            # Add any related pages specified by tags
            for tag in page.tags.filter(name__startswith=self.TAG_PREFIX):
                page_id = int(tag.name.replace(self.TAG_PREFIX, ""))
                related_pages.add(page_id)
            # Remove any non-existing related pages
            related_pages = set(
                Page.objects.filter(id__in=related_pages).values_list("id", flat=True)
            )

            if related_pages == existing_related_pages:
                continue
            if options["no_dry_run"]:
                page.related_pages = json.dumps(
                    [{"type": "related_page", "value": id} for id in related_pages]
                )
                page.save_revision().publish()
            self.stdout.write(f"Added related pages {related_pages} to {page}")

        if not options["no_dry_run"]:
            self.stdout.write(
                "WARNING: Dry run mode, not making any changes. Use --no-dry-run to "
                "make database changes"
            )
