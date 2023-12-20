import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from home.forms import UploadContentFileForm


class TestUploadContentFileForm:
    @pytest.mark.django_db
    def test_empty_locale_label(self):
        """
        The label for the empty locale option should be Import all languages
        """
        assert "Import all languages" in UploadContentFileForm().render()

    def test_default_locale(self):
        """
        Not supplying a locale should give a default "None" value, which the importer
        interprets as we should import all locales found in the file
        """
        file = SimpleUploadedFile(
            name="test.csv", content=b"foo,bar", content_type="text/csv"
        )
        form = UploadContentFileForm(
            files={"file": file},
            data={"file_type": "CSV", "purge": "False", "locale": ""},
        )

        assert form.errors == {}
        assert form.cleaned_data["locale"] is None
