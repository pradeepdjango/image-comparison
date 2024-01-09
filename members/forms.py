from django import forms

class ZipFileUploadForm(forms.Form):
    zip_file = forms.FileField()
