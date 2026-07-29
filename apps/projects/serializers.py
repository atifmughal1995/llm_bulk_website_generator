from rest_framework import serializers
from .models import Page, Template, Project


class PageSerializer(serializers.ModelSerializer):
    """Serializes Page model instances for API responses."""

    template = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ['id', 'name', 'service_type', 'target_region', 'template', 'temperature']

    def get_template(self, obj: Page) -> dict:
        return {'id': obj.template.id, 'name': obj.template.name}


class TemplateSerializer(serializers.ModelSerializer):
    """Serializes Template model instances for API responses."""

    class Meta:
        model = Template
        fields = ['id', 'name']


class ProjectDomainSerializer(serializers.ModelSerializer):
    """Serializes Project model for domain update requests."""

    class Meta:
        model = Project
        fields = ['client_domain']