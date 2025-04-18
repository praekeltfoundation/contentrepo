# Generated by Django 4.2.17 on 2025-03-26 09:29

import django.core.validators
from django.db import migrations
import wagtail.blocks
import wagtail.fields
import wagtail.snippets.blocks


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0091_alter_assessment_slug"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="whatsapptemplate",
            name="quick_replies",
        ),
        migrations.AddField(
            model_name="whatsapptemplate",
            name="buttons",
            field=wagtail.fields.StreamField(
                [
                    (
                        "next_message",
                        wagtail.blocks.StructBlock(
                            [
                                (
                                    "title",
                                    wagtail.blocks.CharBlock(
                                        help_text="Text for the button, up to 20 characters.",
                                        validators=(
                                            django.core.validators.MaxLengthValidator(
                                                20
                                            ),
                                        ),
                                    ),
                                )
                            ]
                        ),
                    ),
                    (
                        "go_to_page",
                        wagtail.blocks.StructBlock(
                            [
                                (
                                    "title",
                                    wagtail.blocks.CharBlock(
                                        help_text="Text for the button, up to 20 characters.",
                                        validators=(
                                            django.core.validators.MaxLengthValidator(
                                                20
                                            ),
                                        ),
                                    ),
                                ),
                                (
                                    "page",
                                    wagtail.blocks.PageChooserBlock(
                                        help_text="Page the button should go to"
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "go_to_form",
                        wagtail.blocks.StructBlock(
                            [
                                (
                                    "title",
                                    wagtail.blocks.CharBlock(
                                        help_text="Text for the button, up to 20 characters.",
                                        validators=(
                                            django.core.validators.MaxLengthValidator(
                                                20
                                            ),
                                        ),
                                    ),
                                ),
                                (
                                    "form",
                                    wagtail.snippets.blocks.SnippetChooserBlock(
                                        "home.Assessment",
                                        help_text="Form the button should start",
                                    ),
                                ),
                            ]
                        ),
                    ),
                ],
                null=True,
                use_json_field=True,
            ),
        ),
    ]
