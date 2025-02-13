from django import forms
from wagtail.models import Locale


class UploadFileForm(forms.Form):
    FILE_CHOICES = (("CSV", "CSV File"), ("XLSX", "Excel File"))
    file = forms.FileField()
    file_type = forms.ChoiceField(choices=FILE_CHOICES)


class UploadContentFileForm(UploadFileForm):
    YES_NO = ((False, "No"), (True, "Yes"))
    purge = forms.ChoiceField(choices=YES_NO)
    locale = forms.ModelChoiceField(
        queryset=Locale.objects.all(),
        empty_label="Import all languages",
        required=False,
    )


class UploadOrderedContentSetFileForm(UploadFileForm):
    YES_NO = ((False, "No"), (True, "Yes"))
    purge = forms.ChoiceField(choices=YES_NO)
