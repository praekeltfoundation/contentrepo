import json
from pathlib import Path

from django.core.management.base import BaseCommand
from taggit.models import Tag
from wagtail.rich_text import RichText

from home.models import ContentPage, HomePage


class Command(BaseCommand):
    help = "Imports content via JSON"

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        def get_body(body_list):
            body = []
            for line in body_list:
                if len(line) != 0:
                    body = body + [("paragraph", RichText(line))]
            return body

        def create_tags(tags, page):
            for tag in tags:
                created_tag, _ = Tag.objects.get_or_create(name=tag)
                page.tags.add(created_tag)

        path = Path(options["path"])
        home_page = HomePage.objects.first()
        with path.open() as json_file:
            data = json.load(json_file)
            for article in data["articles"]:
                contentpage = ContentPage(
                    title=article["title"],
                    subtitle=article["subtitle"],
                    body=get_body(article["body"]),
                )
                create_tags(article["tags"], contentpage)
                home_page.add_child(instance=contentpage)
                contentpage.save_revision()

            self.stdout.write(self.style.SUCCESS("Successfully imported Content Pages"))
