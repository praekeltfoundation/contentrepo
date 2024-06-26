# Generated by Django 4.2.11 on 2024-06-26 21:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0074_alter_assessment_high_inflection"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assessment",
            name="high_inflection",
            field=models.FloatField(
                blank=True,
                help_text="Any score equal to or above this amount is considered high",
                null=True,
            ),
        ),
    ]
