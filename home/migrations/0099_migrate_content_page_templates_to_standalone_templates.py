from django.db import migrations
from typing import Any


def create_unique_whatsapp_template_name(
    content_page_name: str, WhatsAppTemplate: Any
) -> str:
    suffix = 1
    candidate_whatsapp_title = content_page_name
    while WhatsAppTemplate.objects.filter(name=candidate_whatsapp_title).exists():
        suffix += 1
        candidate_whatsapp_title = f"{content_page_name}-{suffix}"
    return candidate_whatsapp_title


def migrate_content_page_templates_to_standalone_templates(
    ContentPage: Any, WhatsAppTemplate: Any, Image: Any
) -> None:
    content_pages = ContentPage.objects.filter(is_whatsapp_template=True)

    for content_page in content_pages:
        whatsapp_block = content_page.whatsapp_body[0]
        whatsapp_value = whatsapp_block.value
        if (
            hasattr(whatsapp_value, "_meta")
            and whatsapp_value._meta.verbose_name == "WhatsApp Template"
        ):
            continue
        image = whatsapp_value.get("image", None)
        if image:
            if isinstance(image, int):
                image = Image.objects.get(id=image)
            elif hasattr(image, "id"):
                image = Image.objects.get(id=image.id)
            elif isinstance(image, dict) and "id" in image:
                image = Image.objects.get(id=image["id"])
            else:
                image = None
        example_values = list(whatsapp_value.get("example_values", []))
        whatsapp_template = WhatsAppTemplate.objects.create(
            name=create_unique_whatsapp_template_name(
                content_page.whatsapp_title.lower().replace(" ", "_"), WhatsAppTemplate
            ),
            locale=content_page.locale,
            message=whatsapp_value.get("message", ""),
            example_values=[
                ("example_values", example_value) for example_value in example_values
            ],
            category=content_page.whatsapp_template_category,
            buttons=whatsapp_value.get("buttons", []),
            image=image,
            submission_status=(
                "SUBMITTED"
                if content_page.whatsapp_template_name
                else "NOT_SUBMITTED_YET"
            ),
            submission_result="",
            submission_name=content_page.whatsapp_template_name,
        )
        wb = content_page.whatsapp_body
        wb[0] = ("Whatsapp_Template", whatsapp_template)
        content_page.whatsapp_body = wb
        content_page.is_whatsapp_template = False
        content_page.save()


def run_migration(apps: Any, schema_editor: Any) -> None:
    ContentPage = apps.get_model("home", "ContentPage")
    WhatsAppTemplate = apps.get_model("home", "WhatsAppTemplate")
    Image = apps.get_model("wagtailimages", "Image")
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
