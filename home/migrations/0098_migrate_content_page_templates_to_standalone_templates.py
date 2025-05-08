from django.db import migrations
from typing import Any


def migrate_content_page_templates_to_standalone_templates(
    ContentPage: Any, WhatsAppTemplate: Any
) -> None:
    content_pages = ContentPage.objects.filter(is_whatsapp_template=True)

    for content_page in content_pages:
        whatsapp_block = content_page.whatsapp_body[0]
        whatsapp_value = whatsapp_block.value
        whatsapp_template = WhatsAppTemplate.objects.create(
            name=content_page.whatsapp_template_name,
            locale=content_page.locale,
            message=whatsapp_value.get("message", ""),
            example_values=whatsapp_value.get("example_values", []),
            category=content_page.whatsapp_template_category,
            buttons=whatsapp_value.get("buttons", []),
            image=whatsapp_value.get("image", None),
            submission_status="NOT_SUBMITTED_YET",
            submission_result="",
        )
        content_page.whatsapp_body = []
        content_page.whatsapp_body.append(("Whatsapp_Template", whatsapp_template))
        content_page.is_whatsapp_template = False
        content_page.save()


def run_migration(apps: Any, schema_editor: Any) -> None:
    ContentPage = apps.get_model("home", "ContentPage")
    WhatsAppTemplate = apps.get_model("home", "WhatsAppTemplate")
    migrate_content_page_templates_to_standalone_templates(
        ContentPage, WhatsAppTemplate
    )


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0097_alter_whatsapptemplate_buttons"),
    ]

    operations = [
        migrations.RunPython(
            code=run_migration, reverse_code=migrations.RunPython.noop
        ),
    ]
