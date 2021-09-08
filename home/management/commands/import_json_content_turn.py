import json
from django.core.management.base import BaseCommand
from taggit.models import Tag
from home.models import ContentPage, HomePage
from wagtail.core.rich_text import RichText
from wagtail.core import blocks
from collections import OrderedDict
from wagtail.core.blocks.struct_block import StructValue
import requests
from wagtail.images.models import Image
from io import BytesIO
from django.core.files.images import ImageFile
from wagtail.images.blocks import ImageChooserBlock

class Command(BaseCommand):
    help = 'Imports turn content via JSON'

    def add_arguments(self, parser):
        parser.add_argument('path')

    def handle(self, *args, **options):
        def get_body(message):
            if message['attachment_media_type'] == "image":
                im = ""
                print("there is an image")
                title = message['attachment_media_object']['filename']
                try:
                    im  = Image.objects.get(title=title).id
                    print("in the try")
                except Exception as e:
                    print("in the exception")
                    http_res = requests.get(message["attachment_uri"])
                    # image_file = ImageFile(open(file_path, 'rb'), name=title)
                    image_file = ImageFile(BytesIO(http_res.content), name=title)
                    image = Image(title=title, file=image_file)
                    image.save()
                    im = image.id


                print("id is ", im)
                block = blocks.StructBlock([
                    ('message', blocks.TextBlock()),
                    ('image', ImageChooserBlock())
                ])
                block_value = block.to_python({'message': message["answer"], 'image': im})
                return block_value
            else:
                print("there is no image")
                block = blocks.StructBlock([
                    ('message', blocks.TextBlock()),
                ])
                block_value = block.to_python({'message': message["answer"]})
                return block_value

        #
        # def create_tags(tags, page):
        #     for tag in tags:
        #         created_tag, _ = Tag.objects.get_or_create(name=tag)
        #         page.tags.add(created_tag)

        path = options['path']


        ContentPage.objects.all().delete()
        with open(path) as json_file:
            data = json.load(json_file)

            for message in data["data"]:
                try:
                    title_list = message["question"].strip().split(" ")
                    language = title_list[-1]
                    language = language[1:-1]
                    print(language)
                    home_page = HomePage.objects.get(title__icontains=language)
                    just_title = " ".join(title_list[0: -1])

                    contentpage = ContentPage(
                        title=message["question"],
                        whatsapp_title=message["question"],
                        whatsapp_body=[("Whatsapp_Message", get_body(message))],
                        locale=home_page.locale
                    )
                    # create_tags(article["tags"], contentpage)
                    home_page.add_child(instance=contentpage)
                    contentpage.save_revision().publish()

                    translations = ContentPage.objects.filter(title__icontains=just_title)
                    if translations:
                        translation = translations.first()
                        # print(translation)
                        # print(just_title)
                        if translation.pk != contentpage.pk:
                            key = translation.translation_key
                            contentpage.translation_key = key
                            contentpage.save_revision().publish()
                except Exception as e:
                    print(e)


            self.stdout.write(self.style.SUCCESS(
                'Successfully imported Content Pages'))
