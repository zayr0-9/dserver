from django import forms
from .models import FileTypeCategory


class FileTypeCategoryForm(forms.ModelForm):
    class Meta:
        model = FileTypeCategory
        fields = ['name', 'extensions']
