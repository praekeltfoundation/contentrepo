import json
import requests
import willow
from django.core.management.base import BaseCommand

# from taggit.models import Tag
from home.models import ContentPage, HomePage
from wagtail.core import blocks
from wagtail.images.models import Image
from io import BytesIO
from django.core.files.images import ImageFile
from wagtail.images.blocks import ImageChooserBlock


def import_content(file):
    def get_body(message):
        if message["attachment_media_type"] == "image":
            im = ""
            title = message["attachment_media_object"]["filename"]
            try:
                im = Image.objects.get(title=title).id
            except Exception:
                uri = requests.get(message["attachment_uri"])
                image_file = ImageFile(BytesIO(uri.content), name=title)
                image = Image(title=title, file=image_file, width=image_file.width, height=image_file.height)
                image.save()
                im = image.id

            block = blocks.StructBlock(
                [("message", blocks.TextBlock()), ("image", ImageChooserBlock())]
            )
            block_value = block.to_python(
                {"message": message["answer"], "image": im}
            )
            return block_value
        else:
            block = blocks.StructBlock(
                [
                    ("message", blocks.TextBlock()),
                ]
            )
            block_value = block.to_python({"message": message["answer"]})
            return block_value


    def create_tags(tags, page):
        for tag in tags:
            created_tag, _ = Tag.objects.get_or_create(name=tag)
            page.tags.add(created_tag)


    ContentPage.objects.filter(id__lte=1000).delete()
    ContentPage.objects.filter(id__lte=2000).delete()
    ContentPage.objects.filter(id__lte=3000).delete()
    data = json.load(file)

    for message in data["data"]:
        try:
            print(message)
            title_list = message["question"].strip().split(" ")
            language = title_list[-1]
            language = language[1:-1]
            home_page = HomePage.objects.get(title__icontains=language)
            just_title = " ".join(title_list[0:-1])
            contentpage = ContentPage(
                title=message["question"],
                whatsapp_title=message["question"],
                whatsapp_body=[("Whatsapp_Message", get_body(message))],
                locale=home_page.locale,
            )
            create_tags(article["tags"], contentpage)
            home_page.add_child(instance=contentpage)
            contentpage.save_revision().publish()

            translations = ContentPage.objects.filter(
                title__icontains=just_title
            )
            if translations:
                translation = translations.first()
                if translation.pk != contentpage.pk:
                    key = translation.translation_key
                    contentpage.translation_key = key
                    contentpage.save_revision().publish()
        except Exception as e:
            print(e)

    return("success")
