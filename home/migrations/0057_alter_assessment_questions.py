# Generated by Django 4.2.11 on 2024-06-05 09:12

from django.db import migrations
import wagtail.blocks
import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0056_alter_assessment_questions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assessment",
            name="questions",
            field=wagtail.fields.StreamField(
                [
                    (
                        "categorical_question",
                        wagtail.blocks.StructBlock(
                            [
                                (
                                    "question",
                                    wagtail.blocks.TextBlock(
                                        help_text="The question to ask the user"
                                    ),
                                ),
                                (
                                    "explainer",
                                    wagtail.blocks.TextBlock(
                                        help_text="Explainer message which tells the user why we need this question",
                                        required=False,
                                    ),
                                ),
                                (
                                    "error",
                                    wagtail.blocks.TextBlock(
                                        help_text="Error message for this question if we don't understand the input",
                                        required=False,
                                    ),
                                ),
                                (
                                    "answers",
                                    wagtail.blocks.ListBlock(
                                        wagtail.blocks.StructBlock(
                                            [
                                                (
                                                    "answer",
                                                    wagtail.blocks.TextBlock(
                                                        help_text="The choice shown to the user for this option"
                                                    ),
                                                ),
                                                (
                                                    "score",
                                                    wagtail.blocks.FloatBlock(
                                                        help_text="How much to add to the total score if this answer is chosen"
                                                    ),
                                                ),
                                            ]
                                        )
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "age_question",
                        wagtail.blocks.StructBlock(
                            [
                                (
                                    "question",
                                    wagtail.blocks.TextBlock(
                                        help_text="The question to ask the user"
                                    ),
                                ),
                                (
                                    "error",
                                    wagtail.blocks.TextBlock(
                                        help_text="Error message for this question if we don't understand the input",
                                        required=False,
                                    ),
                                ),
                            ]
                        ),
                    ),
                ],
                use_json_field=True,
            ),
        ),
    ]