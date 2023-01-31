from django import forms
from wagtail.models import Locale


class UploadFileForm(forms.Form):
    FILE_CHOICES = (("CSV", "CSV file"), ("XLSX", "Excel File"))
    YES_NO = ((False, "No"), (True, "Yes"))
    file = forms.FileField()
    file_type = forms.ChoiceField(choices=FILE_CHOICES)
    purge = forms.ChoiceField(choices=YES_NO)
    locale = forms.ModelChoiceField(
        queryset=Locale.objects.all(), empty_label="Select Locale"
    )
