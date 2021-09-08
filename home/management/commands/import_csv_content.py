import csv
from wagtail.core import blocks
from django.core.management.base import BaseCommand
from home.models import ContentPage, HomePage
from wagtail.core.rich_text import RichText
from taggit.models import Tag


class Command(BaseCommand):
    help = 'Imports content via CSV'

    def add_arguments(self, parser):
        parser.add_argument('path')

    def handle(self, *args, **options):
        def get_rich_text_body(row):
            body = []
            row = row.splitlines()
            for line in row:
                if len(line) != 0:
                    body = body + [('text', RichText(line))]
            return body

        def get_text_body(row):
            body = []
            row = row.splitlines()
            block = blocks.StructBlock([
                ('message', blocks.TextBlock()),
            ])
            block_value = block.to_python({'message': row})
            return block_value

        def create_tags(row, page):
            tags = row[12].split(" ")
            for tag in tags:
                created_tag, _ = Tag.objects.get_or_create(name=tag)
                page.tags.add(created_tag)

        path = options['path']
        home_page = HomePage.objects.first()
        with open(path, 'rt') as f:
            reader = csv.reader(f)
            for row in reader:
                contentpage = ContentPage(
                    title=row[0],
                    subtitle=row[1],
                    body=get_rich_text_body(row[2]),
                    whatsapp_title=row[3],
                    whatsapp_body=[
                        ("Whatsapp_Message", get_text_body(row[5]))],
                )
                create_tags(row, contentpage)
                home_page.add_child(instance=contentpage)
                contentpage.save_revision()

            self.stdout.write(self.style.SUCCESS(
                'Successfully imported Content Pages'))
