# Generated by Django 4.2.17 on 2025-02-13 08:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0088_alter_assessment_questions"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="assessment",
            options={"verbose_name": "CMS Form", "verbose_name_plural": "CMS Forms"},
        ),
    ]
