from typing import Any

from django.db import migrations, models


def run_data_migration(apps: Any, schema_editor: Any) -> None:
    WhatsAppTemplate = apps.get_model("home", "WhatsAppTemplate")
    migrate_whatsapp_template_name_to_slug(WhatsAppTemplate)


def migrate_whatsapp_template_name_to_slug(WhatsAppTemplate: Any) -> None:
    whatsapp_templates = WhatsAppTemplate.objects.all()

    whatsapp_templates = WhatsAppTemplate.objects.all()
    for template in whatsapp_templates:
        name = template.name
        candidate_slug = name.lower().replace(" ", "-")
        suffix = 1
        while WhatsAppTemplate.objects.filter(slug=candidate_slug).exists():
            suffix += 1
            candidate_slug = f"{candidate_slug}-{suffix}"

        template.slug = candidate_slug
        template.save()


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0102_whatsapptemplate_slug"),
    ]

    operations = [
        
        migrations.RunPython(
            code=run_data_migration, reverse_code=migrations.RunPython.noop
        ),
        
    ]