import importlib

from django.test import TestCase

migration = importlib.import_module(
    "home.migrations.0037_alter_contentpage_whatsapp_body"
)
copy_next_prompt_to_next_button_for_message = (
    migration.copy_next_prompt_to_next_button_for_message
)


class TestNextPromptToButtonMigration(TestCase):
    """
    We want to take the `next_prompt` value in WhatsApp messages, and convert it to
    use the new `buttons` value instead
    """

    def test_button_created(self):
        message = {"value": {"message": "test message", "next_prompt": "Tell me more"}}
        copy_next_prompt_to_next_button_for_message(message)

        [button] = message["value"]["buttons"]
        button.pop("id")
        self.assertEqual(
            button, {"type": "next_message", "value": {"title": "Tell me more"}}
        )
