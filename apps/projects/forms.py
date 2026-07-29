from django import forms
from .models import Project, UploadedFile, ProjectPage
from django.core.validators import RegexValidator
from typing import Optional

DOMAIN_REGEX = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'


class ProjectForm(forms.ModelForm):
    create_service_pages_flag = forms.BooleanField(
        required=False,
        initial=False,
        label='Create separate service pages',
        widget=forms.CheckboxInput(attrs={'class': 'ml-2'}),
    )

    class Meta:
        model = Project
        fields = ['name', 'service_type', 'model', 'prompt', 'contact_phone_number', 'email', 'client_domain']

    name = forms.CharField(required=True, widget=forms.TextInput())
    service_type = forms.CharField(required=True, max_length=500, widget=forms.TextInput())
    prompt = forms.CharField(
        required=False,
        max_length=10_000,
        widget=forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Enter a prompt'}),
    )


class UploadFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file', 'project', 'prompt']

    prompt = forms.CharField(
        required=False,
        max_length=10_000,
        widget=forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Enter a prompt'}),
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.all().order_by('-id')


class ProjectDomainForm(forms.ModelForm):
    client_domain = forms.CharField(
        required=False,
        label='Client Domain',
        validators=[
            RegexValidator(
                regex=DOMAIN_REGEX,
                message='Enter a valid domain name (e.g. example.com).',
                code='invalid_domain',
            )
        ],
        widget=forms.TextInput(attrs={'placeholder': 'example.com'}),
    )

    class Meta:
        model = Project
        fields = ['email', 'client_domain', 'contact_phone_number']
        widgets = {
            'client_domain': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. www.example.com'}),
            'email': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. abc@example.com'}),
        }
        labels = {
            'client_domain': 'Domain',
            'email': 'Email',
            'contact_phone_number': 'Phone no.',
        }
        help_texts = {
            'client_domain': 'Enter the domain configured for this project (e.g., myproject.com)',
        }


class CreateServicePageForm(forms.ModelForm):
    class Meta:
        model = ProjectPage
        fields = ['name', 'type', 'prompt']

    prompt = forms.CharField(
        required=False,
        max_length=10_000,
        widget=forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Enter a prompt'}),
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['type'].initial = 'service'
        self.fields['type'].widget = forms.HiddenInput()