from django import forms
from wagtail.models import Locale


class UploadFileForm(forms.Form):
    FILE_CHOICES = (("CSV", "CSV file"), ("JSON", "JSON File"))
    YES_NO = ((True, "Yes"), (False, "No"))
    file = forms.FileField()
    file_type = forms.ChoiceField(choices=FILE_CHOICES)
    split_messages = forms.ChoiceField(choices=YES_NO)
    newline = forms.CharField(max_length=5)
    purge = forms.ChoiceField(choices=YES_NO)
    locale = forms.ModelChoiceField(
        queryset=Locale.objects.all(), empty_label="Select Locale"
    )
