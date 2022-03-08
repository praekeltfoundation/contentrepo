import csv
from django.core.management.base import BaseCommand
from home.models import ContentPage
from taggit.models import Tag


class Command(BaseCommand):
    help = "Updates content tags via CSV"

    def add_arguments(self, parser):
        parser.add_argument("--path")

    def handle(self, *args, **options):
        def update_tags(row, page):
            tags = row["tags"].split(",")

            for tag in page.tags.all():
                tag.delete()

            for tag in tags:
                created_tag, _ = Tag.objects.get_or_create(name=tag.strip())
                page.tags.add(created_tag)

        def clean_row(row):
            for field in ("web_title", "whatsapp_title"):
                if row[field]:
                    row[field] = str(row[field]).strip()
            return row

        path = options["path"]
        with open(path, "rt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row = clean_row(row)

                contentpage = ContentPage.objects.get(
                    title=row["web_title"], whatsapp_title=row["whatsapp_title"]
                )

                update_tags(row, contentpage)

                contentpage.save_revision().publish()

            self.stdout.write(
                self.style.SUCCESS("Successfully Updated Content Page Tags")
            )
