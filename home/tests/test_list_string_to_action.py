import importlib

from django.test import TestCase

list_string_to_action = importlib.import_module(
    "home.migrations.0083_alter_contentpage_whatsapp_body"
).list_string_to_action


class ListStringToActionMigrationTests(TestCase):
    def test_list_string_to_action(self) -> None:
        """
        Converts old list items (strings) to new list items (dicts)
        """
        # Based on this: https://docs.wagtail.org/en/v4.2/advanced_topics/streamfield_migrations.html#old-list-format
        # we assume this is the format of what is currently in CMS before the migration takes place.
        block_value = [
            {"id": "1", "value": "Item 1", "type": "item"},
            {"id": "2", "value": "Item 2", "type": "item"},
            {"id": "3", "value": "Item 3", "type": "item"},
        ]

        new_list = list_string_to_action(block_value)

        self.assertEqual(
            new_list,
            [
                {
                    "type": "next_message",
                    "id": block_value[0]["id"],
                    "value": {"title": block_value[0]["value"]},
                },
                {
                    "type": "next_message",
                    "id": block_value[1]["id"],
                    "value": {"title": block_value[1]["value"]},
                },
                {
                    "type": "next_message",
                    "id": block_value[2]["id"],
                    "value": {"title": block_value[2]["value"]},
                },
            ],
        )
