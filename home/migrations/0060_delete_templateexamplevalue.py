# Generated by Django 4.2.11 on 2024-03-19 11:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0059_remove_whatsapptemplate_example_values"),
    ]

    operations = [
        migrations.DeleteModel(
            name="TemplateExampleValue",
        ),
    ]