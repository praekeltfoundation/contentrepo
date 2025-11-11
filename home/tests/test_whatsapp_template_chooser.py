from typing import Any

import pytest
from wagtail.models import Locale  # type: ignore
from wagtail.search.backends import get_search_backend  # type: ignore

from home.models import WhatsAppTemplate


@pytest.fixture
def admin_client(client: Any, django_user_model: Any) -> Any:
    """Create an admin user and return an authenticated client."""
    creds = {"username": "test", "password": "test"}
    django_user_model.objects.create_superuser(**creds)
    client.login(**creds)
    return client


@pytest.fixture
def locale() -> Locale:
    """Get or create the default English locale."""
    return Locale.objects.get_or_create(language_code="en")[0]


@pytest.fixture
def templates(locale: Locale) -> list[WhatsAppTemplate]:
    """Create test WhatsApp templates."""
    templates = [
        WhatsAppTemplate.objects.create(
            slug="template-1-marketing",
            category="MARKETING",
            message="This is a marketing message",
            locale=locale,
        ),
        WhatsAppTemplate.objects.create(
            slug="template-2-utility",
            category="UTILITY",
            message="This is a utility message",
            locale=locale,
        ),
        WhatsAppTemplate.objects.create(
            slug="customer-service-template",
            category="UTILITY",
            message="Customer service response template",
            locale=locale,
        ),
    ]

    # Publish all templates
    for template in templates:
        template.save_revision().publish()

    # Update search index
    backend = get_search_backend()
    backend.add_bulk(WhatsAppTemplate, templates)

    return templates


@pytest.mark.django_db
class TestWhatsAppTemplateChooser:
    def test_search_by_slug(
        self, admin_client: Any, templates: list[WhatsAppTemplate]
    ) -> None:
        """Test that searching by slug returns matching templates."""
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "template-1"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "template-1-marketing" in content
        assert "template-2-utility" not in content
        assert "customer-service-template" not in content

    def test_search_by_category(
        self, admin_client: Any, templates: list[WhatsAppTemplate]
    ) -> None:
        """Test that searching by category returns matching templates."""
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "marketing"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "template-1-marketing" in content
        assert "template-2-utility" not in content

    def test_search_by_message(
        self, admin_client: Any, templates: list[WhatsAppTemplate]
    ) -> None:
        """Test that searching by message content returns matching templates."""
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "customer service"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "customer-service-template" in content
        assert "template-1-marketing" not in content

    def test_search_multiple_results(
        self, admin_client: Any, templates: list[WhatsAppTemplate]
    ) -> None:
        """Test that searching returns multiple matching templates."""
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "template"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        # All templates have "template" in their slug
        assert "template-1-marketing" in content
        assert "template-2-utility" in content
        assert "customer-service-template" in content

    def test_search_autocomplete_partial_match(
        self, admin_client: Any, templates: list[WhatsAppTemplate]
    ) -> None:
        """Test that autocomplete enables partial/prefix matching."""
        # Single character search works with AutocompleteField
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "t"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        # Should find templates starting with 't'
        assert "template-1-marketing" in content or "template-2-utility" in content

    def test_chooser_columns_present(
        self, admin_client: Any, templates: list[WhatsAppTemplate]
    ) -> None:
        """Test that the chooser displays the expected columns."""
        response = admin_client.get("/admin/snippets/choose/home/whatsapptemplate/")
        assert response.status_code == 200
        content = response.content.decode()

        # Check that custom columns are present in the HTML
        assert "Locale" in content
        assert "Category" in content
        assert "Submission Status" in content

    def test_chooser_shows_template_data(
        self, admin_client: Any, templates: list[WhatsAppTemplate]
    ) -> None:
        """Test that the chooser displays template data in columns."""
        response = admin_client.get("/admin/snippets/choose/home/whatsapptemplate/")
        assert response.status_code == 200
        content = response.content.decode()

        # Check that actual data is displayed
        assert "template-1-marketing" in content
        assert "Marketing" in content or "MARKETING" in content
        assert "Utility" in content or "UTILITY" in content


@pytest.mark.django_db
class TestWhatsAppTemplateSearchIndex:
    def test_search_fields_configuration(self, locale: Locale) -> None:
        """Test that search fields are properly configured without errors."""
        template = WhatsAppTemplate.objects.create(
            slug="test-indexed-template",
            category="MARKETING",
            message="This message should be searchable",
            locale=locale,
        )
        template.save_revision().publish()

        # Verify search fields are configured and adding to index doesn't error
        backend = get_search_backend()
        backend.add(template)

        # Verify the template was created successfully with search fields
        assert WhatsAppTemplate.objects.filter(slug="test-indexed-template").exists()

    def test_locale_related_fields_no_error(self, locale: Locale) -> None:
        """Test that locale RelatedFields configuration doesn't cause errors."""
        # This test verifies the fix where locale (ForeignKey) caused errors
        # when configured directly in search_fields
        template = WhatsAppTemplate.objects.create(
            slug="locale-test-template",
            category="UTILITY",
            message="Testing locale search",
            locale=locale,
        )
        template.save_revision().publish()

        # Adding to search index should not error with locale RelatedFields
        backend = get_search_backend()
        backend.add(template)

        # Verify the template was created successfully
        assert WhatsAppTemplate.objects.filter(slug="locale-test-template").exists()
