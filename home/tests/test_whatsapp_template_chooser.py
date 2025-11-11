import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from wagtail.models import Locale
from wagtail.search.backends import get_search_backend

from home.models import WhatsAppTemplate


User = get_user_model()


@pytest.fixture
def admin_client():
    """Create an admin user and return an authenticated client."""
    user = User.objects.create_superuser(
        username="admin", email="admin@test.com", password="password"
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def locale():
    """Get or create the default English locale."""
    return Locale.objects.get_or_create(language_code="en")[0]


@pytest.fixture
def templates(locale):
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
    def test_search_by_slug(self, admin_client, templates):
        """Test that searching by slug returns matching templates."""
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "template-1"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "template-1-marketing" in content
        assert "template-2-utility" not in content
        assert "customer-service-template" not in content

    def test_search_by_category(self, admin_client, templates):
        """Test that searching by category returns matching templates."""
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "marketing"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "template-1-marketing" in content
        assert "template-2-utility" not in content

    def test_search_by_message(self, admin_client, templates):
        """Test that searching by message content returns matching templates."""
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "customer service"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "customer-service-template" in content
        assert "template-1-marketing" not in content

    def test_search_multiple_results(self, admin_client, templates):
        """Test that searching returns multiple matching templates."""
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "utility"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "template-2-utility" in content
        assert "customer-service-template" in content
        assert "template-1-marketing" not in content

    def test_search_minimum_characters(self, admin_client, templates):
        """Test that single/double character searches don't return results."""
        # Single character search (database backend requires 3+ chars)
        response = admin_client.get(
            "/admin/snippets/choose/home/whatsapptemplate/", {"q": "t"}
        )
        assert response.status_code == 200
        content = response.content.decode()
        # Should show "no snippets match" or empty results
        assert (
            "template-1-marketing" not in content
            or "no snippets match" in content.lower()
        )

    def test_chooser_columns_present(self, admin_client, templates):
        """Test that the chooser displays the expected columns."""
        response = admin_client.get("/admin/snippets/choose/home/whatsapptemplate/")
        assert response.status_code == 200
        content = response.content.decode()

        # Check that custom columns are present in the HTML
        assert "Locale" in content
        assert "Category" in content
        assert "Submission Status" in content

    def test_chooser_shows_template_data(self, admin_client, templates):
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
    def test_search_fields_indexed(self, locale):
        """Test that search fields are properly indexed."""
        template = WhatsAppTemplate.objects.create(
            slug="test-indexed-template",
            category="MARKETING",
            message="This message should be searchable",
            locale=locale,
        )
        template.save_revision().publish()

        # Update search index
        backend = get_search_backend()
        backend.add(template)

        # Test searching by slug
        results = list(backend.search("test-indexed", WhatsAppTemplate))
        assert len(results) > 0
        assert results[0].slug == "test-indexed-template"

        # Test searching by message
        results = list(backend.search("searchable", WhatsAppTemplate))
        assert len(results) > 0
        assert results[0].slug == "test-indexed-template"

    def test_search_by_locale_language_code(self, locale):
        """Test that locale language_code is searchable via RelatedFields."""
        template = WhatsAppTemplate.objects.create(
            slug="locale-test-template",
            category="UTILITY",
            message="Testing locale search",
            locale=locale,
        )
        template.save_revision().publish()

        # Update search index
        backend = get_search_backend()
        backend.add(template)

        # Search should not error on locale field
        # (Previously would fail because locale is a ForeignKey)
        results = list(backend.search("locale-test", WhatsAppTemplate))
        assert len(results) > 0
