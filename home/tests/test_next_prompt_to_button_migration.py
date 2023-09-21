import importlib

from django.test import TestCase

from home.models import ContentPage, HomePage

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
        homepage = HomePage.objects.first()
        page = ContentPage(
            title="test",
            slug="text",
            whatsapp_body=[
                {
                    "type": "Whatsapp_Message",
                    "value": {"message": "test message", "next_prompt": "Tell me more"},
                }
            ],
        )
        homepage.add_child(instance=page)
        page.save_revision()

        message = page.whatsapp_body[0].value
        copy_next_prompt_to_next_button_for_message({"value": message})

        [button] = message["buttons"]
        button.pop("id")
        self.assertEqual(
            button, {"type": "next_message", "value": {"title": "Tell me more"}}
        )
