from django.core.management.base import BaseCommand

from home.models import ContentPage, OrderedContentSet


class Command(BaseCommand):
    help = "Clean broken links for pages"

    def handle(self, *args, **options):
        content_page_links = []
        ordered_content_links = []

        # Only query live pages
        pages = ContentPage.objects.live()

        for page in pages:
            if page.related_pages:
                # Get related pages add it to the list if it is linked to a page that no longer exist
                for rp in page.related_pages:
                    if rp.value is not None:
                        continue
                    content_page_links.append(
                        {"Page ID": page.id, "Error: ": "Related Page is broken"}
                    )

            if page.whatsapp_body:
                buttons = page.whatsapp_body._raw_data[0]["value"].get("buttons")
                if buttons:
                    for btn in buttons:
                        if btn.get("type") == "go_to_page":
                            if btn["value"]["page"] is not None:
                                continue
                            content_page_links.append(
                                {
                                    "Page ID": page.id,
                                    "Error: ": "Go to button is linked to a page that doesn't exist",
                                }
                            )

        # Only get live ordered content sets
        ordered = OrderedContentSet.objects.filter(live=True)

        for oc in ordered:
            if oc.pages:
                for page in oc.pages:
                    if page.value.get("contentpage") is not None:
                        continue
                    ordered_content_links.append(
                        {
                            "Ordered Content": oc.id,
                            "Error": "Page linked to it no longer exist",
                        }
                    )

        self.stdout.write(
            f"BROKEN PAGES > Content Pages: {content_page_links} and Ordered Content Set: {ordered_content_links} "
        )
