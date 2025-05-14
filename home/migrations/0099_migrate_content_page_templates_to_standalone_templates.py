from django.db import migrations
from typing import Any
from django.db.models import Count


def rename_duplicate_whatsapp_titles(ContentPage: Any) -> None:
    duplicate_whatsapp_titles = (
        ContentPage.objects.values("whatsapp_title")
        .annotate(count=Count("whatsapp_title"))
        .filter(count__gt=1)
        .values_list("whatsapp_title", flat=True)
    )
    for whatsapp_title in duplicate_whatsapp_titles:
        pages = ContentPage.objects.filter(whatsapp_title=whatsapp_title)
        while pages.count() > 1:
            page = pages.first()
            suffix = 1
            candidate_whatsapp_title = whatsapp_title
            while ContentPage.objects.filter(
                whatsapp_title=candidate_whatsapp_title
            ).exists():
                suffix += 1
                candidate_whatsapp_title = f"{whatsapp_title}-{suffix}"
            page.whatsapp_title = candidate_whatsapp_title
            page.save(update_fields=["whatsapp_title"])


def rename_matching_whatsapp_names(ContentPage: Any, WhatsAppTemplate: Any) -> None:
    templates = WhatsAppTemplate.objects.all()
    for template in templates:
        pages = ContentPage.objects.filter(whatsapp_title=template.name)
        while pages.count() > 1:
            page = pages.first()
            suffix = 1
            candidate_whatsapp_title = template.name
            while ContentPage.objects.filter(
                whatsapp_title=candidate_whatsapp_title
            ).exists():
                suffix += 1
                candidate_whatsapp_title = f"{template.name}-{suffix}"
            page.whatsapp_title = candidate_whatsapp_title
            page.save(update_fields=["whatsapp_title"])


def migrate_content_page_templates_to_standalone_templates(
    ContentPage: Any, WhatsAppTemplate: Any, Image: Any
) -> None:
    content_pages = ContentPage.objects.filter(is_whatsapp_template=True)

    for content_page in content_pages:
        whatsapp_block = content_page.whatsapp_body[0]
        whatsapp_value = whatsapp_block.value
        print(f"Content Page slug: {content_page.slug}")
        print(f"Content page title: {content_page.whatsapp_title}")
        print(f"Whatsapp Value type: {type(whatsapp_value)}, value: {whatsapp_value}")
        if (
            not hasattr(whatsapp_value, "_meta")
            or whatsapp_value._meta.verbose_name != "WhatsApp Template"
        ):
            image = whatsapp_value.get("image", None)
            if image:
                print(f"Image type: {type(image)}")
                if isinstance(image, int):
                    image = Image.objects.get(id=image)
                elif hasattr(image, "id"):
                    image = Image.objects.get(id=image.id)
                elif isinstance(image, dict) and "id" in image:
                    image = Image.objects.get(id=image["id"])
                else:
                    image = None
            else:
                print("No image")
            example_values = list(whatsapp_value.get("example_values", []))
            whatsapp_template = WhatsAppTemplate.objects.create(
                name=content_page.whatsapp_title.lower().replace(" ", "_"),
                locale=content_page.locale,
                message=whatsapp_value.get("message", ""),
                example_values=[
                    ("example_values", example_value)
                    for example_value in example_values
                ],
                category=content_page.whatsapp_template_category,
                buttons=whatsapp_value.get("buttons", []),
                image=image,
                submission_status="NOT_SUBMITTED_YET",
                submission_result="",
            )
            content_page.whatsapp_body = []
            content_page.whatsapp_body.append(("Whatsapp_Template", whatsapp_template))
            content_page.is_whatsapp_template = False
            content_page.save()
            print("Content Page Saved")


def run_migration(apps: Any, schema_editor: Any) -> None:
    ContentPage = apps.get_model("home", "ContentPage")
    WhatsAppTemplate = apps.get_model("home", "WhatsAppTemplate")
    Image = apps.get_model("wagtailimages", "Image")
    rename_duplicate_whatsapp_titles(ContentPage)
    rename_matching_whatsapp_names(ContentPage, WhatsAppTemplate)
    migrate_content_page_templates_to_standalone_templates(
        ContentPage, WhatsAppTemplate, Image
    )


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0098_whatsapptemplate_locked_whatsapptemplate_locked_at_and_more"),
    ]

    operations = [
        migrations.RunPython(
            code=run_migration, reverse_code=migrations.RunPython.noop
        ),
    ]
