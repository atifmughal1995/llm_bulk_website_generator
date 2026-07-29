import json
import re
import logging
from typing import Optional

from django.urls import reverse
from django.contrib import admin
from django.contrib import messages
from rest_framework.test import APIRequestFactory
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.template.loader import render_to_string
from django_grapesjs.admin import GrapesJsAdminMixin

from .models import (
    Project,
    Page,
    Template,
    Section,
    TemplateSection,
    AIGeneratedContent,
    UploadedFile,
    State,
    County,
    City,
    ProjectPage,
    ProjectPageVersion,
    CityPageVersions,
    ProjectPromptHistory,
    CityPromptHistory,
    RegeneratedImage,
)
from .views.api import CreatePageViewV2
from .prompts import HOMEPAGE_PROMPT
from .services.excel_service import ExcelProcessingService

logger = logging.getLogger(__name__)


class StateModelInline(admin.TabularInline):
    model = State
    extra = 1
    fields = ('state_name', 'abbreviation', 'county_city_zipcode')

    def state_name(self, obj: State) -> str:
        url = f'/admin/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/'
        return format_html(
            '<a href="{}" style="font-size: 13px; font-weight: 700">{}', url, obj.name
        )

    def county_city_zipcode(self, obj: State) -> str:
        context = {
            'project_id': obj.project.id,
            'state_id': obj.id,
            'counties': County.objects.filter(state=obj)[:20],
            'cities': City.objects.filter(county__state=obj)[:50],
            'zipcodes': Page.objects.filter(city__county__state=obj)[:100],
        }
        html = render_to_string('admin_project_change_form.html', context)
        return mark_safe(html)

    def has_delete_permission(self, request, obj: Optional[State] = None) -> bool:
        return False

    def has_add_permission(self, request, obj: Optional[State] = None) -> bool:
        return False

    readonly_fields = ['state_name', 'abbreviation', 'county_city_zipcode']
    county_city_zipcode.short_description = 'County / City / Zipcode'


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'view_button', 'edit_button')
    inlines = [StateModelInline,]

    def save_model(self, request, obj: Project, form, change: bool) -> None:
        super().save_model(request, obj, form, change)

    def generate_homepage_content(self, obj: Project) -> None:
        template_sections = (
            TemplateSection.objects.filter(template_id=obj.homepage_template_id)
            .select_related('section')
        )

        section_images: dict[str, str] = {}

        for t_section in template_sections:
            default_content = t_section.default_content
            if '{{image}}' in default_content:
                query = f'{t_section.section.name} {obj.service_type}'
                image_url = get_image(query)
                section_images[t_section.section.name] = (
                    image_url if image_url else get_placeholder()
                )

        section_images['general'] = get_images(obj.service_type, 15)

        obj.images = str(section_images)
        obj.save()

        sections_names = list(template_sections.values_list('section__name', flat=True))

        homepage_link = reverse('homepage', args=[obj.id])
        service_area_link = reverse('states', args=[obj.id])

        prompt = HOMEPAGE_PROMPT.format(
            service_type=obj.service_type,
            sections=sections_names,
            homepage_link=homepage_link,
            service_area_link=service_area_link,
        )
        ai_generated_content = generate_content(prompt, 0.7, obj.model.lower() == 'openai')
        obj.homepage_ai_response = ai_generated_content

        project_page_obj = ProjectPage(project=obj, name='homepage')
        project_page_obj.ai_response = ai_generated_content

        match = re.search(r'```html(.*?)```', ai_generated_content, re.DOTALL)
        project_page_obj.html = match.group(1) if match else ''

        match = re.search(r'```css(.*?)```', ai_generated_content, re.DOTALL)
        project_page_obj.css = (
            f'<style>{match.group(1)}</style>' if match else ''
        )

        match = re.search(r'<head>(.*?)</head>', ai_generated_content, re.DOTALL)
        project_page_obj.head = (
            f'<head>{match.group(1)}</head>' if match else ''
        )

        match = re.search(
            r'<header id="header"(.*?)</header>', ai_generated_content, re.DOTALL
        )
        project_page_obj.header = (
            f'<header id="header"{match.group(1)}</header>' if match else ''
        )

        match = re.search(
            r'<footer id="footer"(.*?)</footer>', ai_generated_content, re.DOTALL
        )
        project_page_obj.footer = (
            f'<footer id="footer"{match.group(1)}</footer>' if match else ''
        )

        project_page_obj.complete_html = f'{project_page_obj.html}{project_page_obj.css}'
        project_page_obj.save()

        obj.save()

    def view_button(self, obj: Project) -> str:
        html = f'''
        <a href="/project/{obj.pk}/homepage/" class="eye-icon-link" target="_blank" style="display: inline-flex;
        align-items: center; text-decoration: none; color: white; font-weight: 300; font-size: 12px;
        padding: 2px 10px; border-radius: 20px; background-color: transparent; transition: background-color 0.3s,
        color 0.3s;"><i class="fas fa-eye" style="margin-right: 5px; font-size: 16px;"></i></a>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        '''
        return mark_safe(html)

    def edit_button(self, obj: Project) -> str:
        html = f'''
        <a href="/project/{obj.pk}/homepage/edit/" class="edit-icon-link" target="_blank" style="display: inline-flex;
        align-items: center; text-decoration: none; color: white; font-weight: 300; font-size: 12px;
        padding: 2px 10px; border-radius: 20px; background-color: transparent; transition: background-color 0.3s,
        color 0.3s;"><i class="fas fa-edit" style="margin-right: 5px; font-size: 16px;"></i></a>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        '''
        return mark_safe(html)


class AIGeneratedContentModelInline(admin.TabularInline):
    model = AIGeneratedContent
    fields = ('section',)

    def section(self, obj: AIGeneratedContent) -> str:
        url = f'/admin/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/'
        return format_html(
            '<a href="{}" style="font-size: 13px; font-weight: 700">{}', url, obj.template_section.section.name
        )

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    readonly_fields = ['section']


@admin.register(Page)
class PageAdmin(GrapesJsAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'project', 'zip_code', 'template', 'temperature', 'view_button', 'edit_button')
    inlines = [AIGeneratedContentModelInline,]

    def save_model(self, request, obj: Page, form, change: bool) -> None:
        try:
            if not change:
                if obj.pk is None:
                    super().save_model(request, obj, form, change)
                    self.create_new_page(obj)
                    self.message_user(request, 'New page created.', level=messages.INFO)
            else:
                super().save_model(request, obj, form, change)
        except Exception as e:
            self.message_user(request, str(e), level=messages.ERROR)

    def create_new_page(self, obj: Page) -> None:
        """Handles page creation by calling the API endpoint."""
        factory = APIRequestFactory()
        post_data = {
            'name': obj.name,
            'target_region': obj.city.name,
            'temperature': obj.temperature,
            'template_id': obj.template_id,
            'page_id': obj.pk,
            'project_id': obj.city.county.state.project.id,
            'zip_code': obj.zip_code,
        }
        request = factory.post('/create/', post_data)
        view = CreatePageViewV2.as_view()
        return view(request)

    def update_ai_generated_content(self, obj: Page) -> None:
        """Regenerates AI-generated content when prompt or temperature changes."""
        ai_generated_content = json.loads(generate_content(obj.prompt, float(obj.temperature)))
        ai_generated_sections = AIGeneratedContent.objects.filter(page=obj)

        for section in ai_generated_sections:
            section.content = ai_generated_content.get(section.template_section.section.name, '')
            section.save()

    def project(self, obj: Page) -> str:
        return obj.city.county.state.project.name

    def view_button(self, obj: Page) -> str:
        html = f'''
        <a href="/project/{obj.city.county.state.project.id}/page/{obj.pk}/" class="eye-icon-link" target="_blank" style="display: inline-flex;
        align-items: center; text-decoration: none; color: white; font-weight: 300; font-size: 12px;
        padding: 2px 10px; border-radius: 20px; background-color: transparent; transition: background-color 0.3s,
        color 0.3s;"><i class="fas fa-eye" style="margin-right: 5px; font-size: 16px;"></i></a>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        '''
        return mark_safe(html)

    def edit_button(self, obj: Page) -> str:
        if obj.complete_html:
            html = f'''
            <a href="/project/{obj.city.county.state.project.id}/page/{obj.pk}/edit/" class="edit-icon-link" target="_blank" style="display: inline-flex;
            align-items: center; text-decoration: none; color: white; font-weight: 300; font-size: 12px;
            padding: 2px 10px; border-radius: 20px; background-color: transparent; transition: background-color 0.3s,
            color 0.3s;"><i class="fas fa-edit" style="margin-right: 5px; font-size: 16px;"></i></a>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
            '''
            return mark_safe(html)
        else:
            return ''

    view_button.short_description = 'View'
    edit_button.short_description = 'Edit'


class TemplateSectionModelInline(admin.TabularInline):
    model = TemplateSection
    fields = ('name', 'order')

    def name(self, obj: TemplateSection) -> str:
        url = f'/admin/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/'
        return format_html(
            '<a href="{}" style="font-size: 13px; font-weight: 700">{}', url, obj.section.name
        )

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    readonly_fields = ['name', 'order']


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name',)
    inlines = [TemplateSectionModelInline,]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(TemplateSection)
class TemplateSectionAdmin(admin.ModelAdmin):
    list_display = ('template', 'section', 'order')
    list_editable = ('order',)
    ordering = ['id', 'order']


@admin.register(AIGeneratedContent)
class AIGeneratedContentAdmin(admin.ModelAdmin):
    list_display = ('template_section', 'page', 'prompt', 'content')


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('file', 'project', 'uploaded_at')

    def save_model(self, request, obj: UploadedFile, form, change: bool) -> None:
        super().save_model(request, obj, form, change)
        ExcelProcessingService().process_uploaded_file(obj, obj.prompt or '')

    def get_or_create_city(self, row, project: Project) -> City:
        state, _ = State.objects.get_or_create(name=row[3], abbreviation=row[2], project=project)
        county, _ = County.objects.get_or_create(name=row[5], state=state)
        city, _ = City.objects.get_or_create(name=row[0], county=county)
        return city


class CountyModelInline(admin.TabularInline):
    model = County
    extra = 1
    fields = ('county_name', 'cities')

    def county_name(self, obj: County) -> str:
        url = f'/admin/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/'
        return format_html(
            '<a href="{}" style="font-size: 13px; font-weight: 700">{}, {}', url, obj.name, obj.state.abbreviation
        )

    def cities(self, obj: County) -> int:
        return obj.cities.count()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    readonly_fields = ['county_name', 'cities']


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'counties')
    inlines = [CountyModelInline,]

    def counties(self, obj: State) -> int:
        return obj.counties.count()


class CityModelInline(admin.TabularInline):
    model = City
    extra = 1
    fields = ('city_name', 'zip_codes')

    def city_name(self, obj: City) -> str:
        url = f'/admin/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/'
        return format_html(
            '<a href="{}" style="font-size: 13px; font-weight: 700">{}', url, obj.name
        )

    def zip_codes(self, obj: City) -> int:
        return obj.zip_codes.count()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    readonly_fields = ['city_name', 'zip_codes']


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ('name', 'cities')
    inlines = [CityModelInline,]

    def cities(self, obj: County) -> int:
        return obj.cities.count()


class PageModelInline(admin.TabularInline):
    model = Page
    extra = 1
    fields = ('zip_codes', 'view_button')

    def zip_codes(self, obj: Page) -> str:
        url = f'/admin/{obj._meta.app_label}/{obj._meta.model_name}/{obj.pk}/change/'
        return format_html(
            '<a href="{}" style="font-size: 13px; font-weight: 700">{}', url, obj.name
        )

    def view_button(self, obj: Page) -> str:
        html = f'''
        <a href="/project/html?page_id={obj.pk}" class="eye-icon-link" target="_blank" style="display: inline-flex;
        align-items: center; text-decoration: none; color: white; font-weight: 300; font-size: 12px;
        padding: 2px 10px; border-radius: 20px; background-color: transparent; transition: background-color 0.3s,
        color 0.3s;"><i class="fas fa-eye" style="margin-right: 5px; font-size: 16px;"></i></a>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css"></p>
        '''
        return mark_safe(html)

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    readonly_fields = ['zip_codes', 'view_button']


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_name', 'status')

    def project_name(self, obj: City) -> str:
        return obj.county.state.project.name

    inlines = [PageModelInline,]


@admin.register(ProjectPage)
class ProjectPageAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_name')

    def project_name(self, obj: ProjectPage) -> str:
        return obj.project.name


@admin.register(ProjectPageVersion)
class ProjectPageVersionAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'page_name', 'name', 'created_at')

    def project_name(self, obj: ProjectPageVersion) -> str:
        return obj.project_page.project.name

    def page_name(self, obj: ProjectPageVersion) -> str:
        return obj.project_page.name


@admin.register(CityPageVersions)
class CityPageVersionsAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'city_name', 'name', 'created_at')

    def project_name(self, obj: CityPageVersions) -> str:
        return obj.city_page.county.state.project.name

    def city_name(self, obj: CityPageVersions) -> str:
        return obj.city_page.name


@admin.register(ProjectPromptHistory)
class ProjectPromptHistoryAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'prompt', 'created_at')

    def project_name(self, obj: ProjectPromptHistory) -> str:
        return obj.project.name


@admin.register(CityPromptHistory)
class CityPromptHistoryAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'city_name', 'prompt', 'created_at')

    def project_name(self, obj: CityPromptHistory) -> str:
        return obj.city.county.state.project.name

    def city_name(self, obj: CityPromptHistory) -> str:
        return obj.city.name


@admin.register(RegeneratedImage)
class RegeneratedImageAdmin(admin.ModelAdmin):
    list_display = ('project', 'image', 'prompt')