from django.core.management.base import BaseCommand

from home.models import ContentPage


class Command(BaseCommand):
    help = (
        "Updates the embeddings for all live ContentPages. "
        "Intended to be run when sentence transformation is turned on for an instance "
        "so that existing content has embeddings saved."
        "Does not create a new revision and does not publish pages after saving."
    )

    def handle(self, *args, **options):
        pages = ContentPage.objects.live()
        for page in pages:
            page.save()
