from django.core.management.base import BaseCommand
from wagtail.models import Page

from home.models import ContentPage, OrderedContentSet


class Command(BaseCommand):
    help = "Clean broken links for pages"

    def handle(self, *args, **options):
        # Query all pages
        content_pages = ContentPage.objects.all()

        for page in content_pages:
            if page.related_pages:
                # Get related pages add it to the list if it is linked to a page that no longer exist
                for rp in page.related_pages:
                    if rp.value is not None:
                        continue
                    self.stdout.write(
                        f"Content Page: {page.id} with non existing related page "
                    )

            if page.whatsapp_body:
                buttons = page.whatsapp_body._raw_data[0]["value"].get("buttons")
                if buttons:
                    for btn in buttons:
                        if btn.get("type") == "go_to_page":
                            # Get page linked to it
                            pg_id = btn["value"]["page"]
                            try:
                                Page.objects.get(id=pg_id)
                            except Page.DoesNotExist:
                                self.stdout.write(
                                    f"Content Page: {page.id} with non existing button page: {pg_id}"
                                )

        # Get ordered content sets
        ordered = OrderedContentSet.objects.all()

        for oc in ordered:
            if oc.pages:
                for page in oc.pages:
                    if page.value.get("contentpage") is not None:
                        continue
                    self.stdout.write(
                        f"Ordered Content: {oc.id} with non existing page"
                    )

        self.stdout.write(self.style.SUCCESS("Successfully retrieve broken links"))
