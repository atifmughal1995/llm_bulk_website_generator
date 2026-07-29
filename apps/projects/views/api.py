import ast
import json
import os
import re
import logging
from typing import Any, Optional

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

import django.template as dt

from django.views.decorators.csrf import csrf_exempt
from bs4 import BeautifulSoup

from .models import (
    AIGeneratedContent,
    Page,
    Project,
    ProjectPage,
    ProjectPageVersion,
    CityPageVersions,
    Template,
    TemplateSection,
    City,
)
from .prompts import (
    INITIAL_PROMPT_STRUCTURE,
    REWRITE_SECTION_PROMPT,
    CITY_PAGE_PROMPT,
    NO_CONTENT_SECTION_HTML,
    REGENERATION_PROMPT,
    PROJECT_PAGE_PROMPT,
    DEFAULT_SERVICE_PAGE_SECTIONS,
    NGINX_TEMPLATE,
)
from .serializers import PageSerializer, TemplateSerializer
from .forms import ProjectForm, UploadFileForm, ProjectDomainForm, CreateServicePageForm
from .html_utils import remove_link_from_html, clean_html, extract_tag_content
from .tasks import process_project_creation, process_excel_task, create_project_page
from .ai_utils import generate_content
from .image_utils import get_image, get_placeholder, get_images
from .exceptions import NetlifyAPIError
from .clients.netlify_client import NetlifyClient
from .services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)


class ServicePageHTMLAPIView(APIView):
    """Generate HTML from AI-generated content for a given page."""

    def get(self, request: HttpRequest, page_id: int) -> HttpResponse:
        edit_mode = request.GET.get('edit', 'false').lower() == 'true'
        page = get_object_or_404(Page, id=page_id)

        if page.complete_html and not edit_mode:
            return HttpResponse(page.complete_html, status=200)

        project = page.city.county.state.project
        project_id = project.id
        project = get_object_or_404(Project, id=project_id)

        template = get_object_or_404(Template, id=project.service_page_template.id)

        css = f'<style>{template.css}</style>'
        template_header = dt.Template(template.header).render(
            dt.Context({'project_id': project_id})
        )

        if not page.ai_response:
            html = project.base_html.replace('||CONTENT||', NO_CONTENT_SECTION_HTML)
            return HttpResponse(html, status=200)

        ai_section_content = (
            AIGeneratedContent.objects.filter(
                page_id=page_id,
                content__isnull=False,
            )
            .exclude(template_section__section__name='Related Zip Codes')
            .order_by('template_section__order')
            .values_list('template_section__section__name', 'content', 'prompt')
        )

        ai_content: dict[str, Any] = {}
        ai_generated_content_prompts: dict[str, str] = {}

        for item in ai_section_content:
            try:
                ai_content[item[0]] = ast.literal_eval(item[1])
                ai_generated_content_prompts[item[0]] = item[2] if item[2] else ''
            except Exception as err:
                logger.warning('Failed to parse AI content: %s', err)

        ai_content = ai_content if ai_content else {}
        section_images = ast.literal_eval(page.images) if page.images else {}
        template_sections = (
            TemplateSection.objects.filter(template_id=template.id)
            .order_by('order')
        )
        content_html = ''
        general_images = section_images.get('general', [])
        testimonial_images = section_images.get('testimonial', [])

        template_head = template.head if template.head else ''
        template_footer = template.footer if template.footer else ''

        sections_data: dict[str, Any] = {
            'head': {'html': template_head},
            'header': {'html': template_header},
            'css': {'html': css},
        }

        for ts in template_sections:
            section_data = ai_content.get(ts.section.name, {})
            listing_data = section_data.get('data', [])
            section_image = section_images.get(ts.section.name, get_placeholder())

            for listing_item in listing_data:
                if 'testimonial' in ts.section.name.lower() or 'customer' in ts.section.name.lower():
                    listing_item['image'] = (
                        testimonial_images.pop() if testimonial_images else get_placeholder()
                    )
                else:
                    listing_item['image'] = (
                        general_images.pop() if general_images else section_image
                    )

            if ts.default_content:
                if ts.section.name.lower() == 'gallery':
                    html = ts.default_content
                    while '{{image}}' in html:
                        html = html.replace(
                            '{{image}}',
                            general_images.pop() if general_images else get_placeholder(),
                            1,
                        )
                else:
                    html = dt.Template(ts.default_content).render(
                        dt.Context(
                            {
                                'h1': section_data.get('h1', ''),
                                'h2': section_data.get('h2', ''),
                                'content': section_data.get('content', ''),
                                'data': listing_data,
                                'image': section_image,
                                'general_images': general_images,
                                'iframe_src': section_data.get('iframe_src', ''),
                            }
                        )
                    )

                content_html += html

                sections_data.update(
                    {
                        ts.section.name: {
                            'data': section_data,
                            'html': html,
                            'prompt': ai_generated_content_prompts.get(ts.section.name, ''),
                        }
                    }
                )

        template_header = dt.Template(template.header).render(
            dt.Context({'project_id': project_id})
        )

        sections_data['footer'] = {'html': template_footer}

        if edit_mode:
            return JsonResponse(sections_data, status=200)

        html = f'{template_head}{template_header}{css}{content_html}{template_footer}'

        page.html = html
        page.save()

        return HttpResponse(html, status=200)


class CreatePageView(APIView):
    """
    Handles page creation by receiving input data, processing template sections,
    and generating HTML content based on the AI data.
    """

    def post(self, request: HttpRequest) -> Response:
        name = request.data.get('name')
        target_region = request.data.get('target_region')
        template_id = request.data.get('template_id')
        temperature = float(request.data.get('temperature', 0.0))
        page_id = request.data.get('page_id', None)
        zip_code = request.data.get('zip_code', None)
        city_id = request.data.get('city_id', None)
        project_id = request.data.get('project_id', None)

        project = get_object_or_404(Project, id=project_id)

        sections = (
            TemplateSection.objects.filter(template_id=template_id)
            .select_related('section')
            .values('id', 'section__name')
        )
        sections_names = ', '.join([section['section__name'] for section in sections])

        prompt = INITIAL_PROMPT_STRUCTURE.format(
            company_name=project.name,
            service_type=project.service_type,
            target_region=target_region,
            sections=sections_names,
            zip_code=zip_code,
        )

        ai_generated_content = generate_content(prompt, temperature)

        if page_id is None:
            page = Page.objects.create(
                name=name,
                template_id=template_id,
                prompt=prompt,
                ai_response=ai_generated_content,
                temperature=temperature,
                zip_code=zip_code,
                city_id=city_id,
            )
        else:
            page = get_object_or_404(Page, id=page_id)
            page.prompt = prompt
            page.ai_response = ai_generated_content
            page.save()

        self._create_template_sections(ast.literal_eval(ai_generated_content), sections, page)

        return Response('Page has been successfully created.')

    def _create_template_sections(
        self, ai_generated_content: dict[str, Any], sections: list[dict[str, Any]], page: Page
    ) -> None:
        instances = [
            AIGeneratedContent(
                template_section_id=section['id'],
                prompt=None,
                content=ai_generated_content.get(section['section__name']),
                page=page,
            )
            for section in sections
        ]
        AIGeneratedContent.objects.bulk_create(instances)


class CreatePageViewV2(APIView):
    """
    Handles page creation by receiving input data, processing template sections,
    and generating HTML content based on the AI data.
    """

    def post(self, request: HttpRequest) -> Response:
        temperature = float(request.data.get('temperature', 0.0))
        city_id = request.data.get('city_id', None)
        project_id = request.data.get('project_id', None)
        prompt = request.data.get('prompt', '')

        project = get_object_or_404(Project, id=project_id)
        city = get_object_or_404(City, id=city_id)

        prompt, ai_generated_content = self.generate_page_content(
            project, city.name, temperature, prompt
        )

        city.prompt = prompt
        city.ai_response = ai_generated_content
        city.content_html = ai_generated_content
        city.complete_html = project.base_html.replace('||CONTENT||', ai_generated_content)
        city.save()

        CityPageVersions.objects.create(
            city_page=city,
            complete_html=city.complete_html,
            name='Default',
        )

        return Response('Page has been successfully created.')

    def generate_page_content(
        self, project: Project, city_name: str, temperature: float, prompt: str
    ) -> tuple[str, str]:
        sections_names = DEFAULT_SERVICE_PAGE_SECTIONS

        prompt = CITY_PAGE_PROMPT.format(
            company_name=project.name,
            service_type=project.service_type,
            target_region=city_name,
            sections=sections_names,
            base_html=project.base_html,
            additional_guideline=prompt,
        )

        ai_generated_content = generate_content(
            prompt, temperature, project.model.lower() == 'openai'
        )

        matches = re.findall(r'```html(.*?)```', ai_generated_content, re.DOTALL)
        ai_generated_content = matches[0].strip() if len(matches) > 0 else ''

        return prompt, ai_generated_content

    def get_page_images(
        self, template_sections: list[TemplateSection], service_type: str
    ) -> dict[str, list[str]]:
        section_images: dict[str, list[str]] = {}

        for t_section in template_sections:
            default_content = t_section.default_content

            if '{{image}}' in str(default_content):
                query = f'{t_section.section.name} {service_type}'
                image_url = get_image(query)
                section_images[t_section.section.name] = (
                    image_url if image_url else get_placeholder()
                )

        section_images['general'] = get_images(service_type, 20)
        section_images['testimonial'] = get_images('Testimonial', 5)

        return section_images

    def _create_template_sections(
        self, ai_generated_content: dict[str, Any], sections: list[dict[str, Any]], page: Page
    ) -> None:
        instances = [
            AIGeneratedContent(
                template_section_id=section['id'],
                prompt=None,
                content=ai_generated_content.get(section['section__name']),
                page=page,
            )
            for section in sections
        ]
        AIGeneratedContent.objects.bulk_create(instances)


class RegenerateSectionView(APIView):
    """Regenerates a specific section of a page using AI."""

    def post(self, request: HttpRequest) -> JsonResponse:
        page_id = request.data.get('page_id')
        section_name = request.data.get('section_name')
        prompt = request.data.get('prompt')
        data = request.data.get('data')

        page = get_object_or_404(Page, id=page_id)
        project = page.city.county.state.project
        is_openai = project.model.lower() == 'openai'
        template = project.service_page_template

        prompt = REWRITE_SECTION_PROMPT.format(object=data, prompt=prompt)

        images = [item.get('image', '') for item in data.get('data', [])]

        ai_generated_content = generate_content(prompt, float(page.temperature), is_openai)
        ai_generated_content = ast.literal_eval(ai_generated_content)

        template_section = (
            TemplateSection.objects.filter(template_id=template.id, section__name=section_name)
            .first()
        )

        page_images = ast.literal_eval(page.images) if page.images else {}
        section_image = page_images.get(section_name, get_placeholder())
        general_images = page_images.get('general', [])[::-1]

        listing_data = ai_generated_content.get('data', [])

        for item in listing_data:
            if images:
                item['image'] = images.pop()
            else:
                item['image'] = (
                    general_images.pop() if general_images else get_placeholder()
                )

        updated_html = dt.Template(template_section.default_content).render(
            dt.Context(
                {
                    'h1': ai_generated_content.get('h1', ''),
                    'h2': ai_generated_content.get('h2', ''),
                    'content': ai_generated_content.get('content', ''),
                    'data': listing_data,
                    'image': section_image,
                    'general_images': general_images,
                    'iframe_src': ai_generated_content.get('iframe_src', ''),
                }
            )
        )

        updated_data = {
            section_name: {
                'data': ai_generated_content,
                'html': updated_html,
            }
        }

        return JsonResponse(updated_data, status=200)


class SavePageView(APIView):
    """Saves edited page content from the GrapesJS editor."""

    def post(self, request: HttpRequest) -> JsonResponse:
        page_id = request.data.get('page_id')
        data = request.data.get('data')

        page = get_object_or_404(Page, id=page_id)
        page.html = ''
        page.save()

        for section_name, content in data.items():
            ai_generated_content = (
                AIGeneratedContent.objects.filter(
                    page_id=page.id,
                    template_section__section__name=section_name,
                )
                .first()
            )

            if ai_generated_content and 'data' in content:
                ai_generated_content.content = (
                    content['data'] if content['data'] else ai_generated_content.content
                )
                ai_generated_content.prompt = content.get('prompt', '')
                ai_generated_content.save()

        return JsonResponse({'message': 'Page has been saved.'}, status=200)


class GetAllPageView(ListAPIView):
    """Retrieves and lists all the pages."""

    queryset = Page.objects.all()
    serializer_class = PageSerializer


class GetAllTemplateView(ListAPIView):
    """Retrieves and lists all the templates."""

    queryset = Template.objects.all()
    serializer_class = TemplateSerializer


class CreateProjectView(APIView):
    """Handles project creation via a form submission."""

    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest) -> HttpResponse:
        form = ProjectForm()
        return render(request, 'project_create_form.html', {'form': form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            custom_prompt = form.cleaned_data.get('prompt', '') or 'None'
            create_service_page_flag = form.cleaned_data.get('create_service_pages_flag', False)

            project.status = 'In progress'
            project.save()

            process_project_creation.delay(project.id, custom_prompt, create_service_page_flag)

            return redirect('projects')
        return render(request, 'project_create_form.html', {'form': form})


class UploadFileView(APIView):
    """Handles Excel file upload for bulk page creation."""

    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest) -> HttpResponse:
        form = UploadFileForm()
        return render(request, 'upload_file_form.html', {'form': form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            prompt = form.cleaned_data.get('prompt', '')

            process_excel_task.delay(obj.id, prompt)

            return redirect('projects')
        else:
            return render(request, 'upload_file_form.html', {'form': form})


class ProjectDomainUpdateView(APIView):
    """Handles updating a project's custom domain."""

    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        project = get_object_or_404(Project, id=project_id)
        form = ProjectDomainForm(instance=project)
        domain = (
            project.netlify_site_url.replace('https://', '').replace('http://', '')
            if project.netlify_site_url
            else ''
        )
        netlify_urls = [url for url in str(project.netlify_site_url_history).split(',') if url]
        logger.info('Netlify URLs for project %s: %s', project.id, netlify_urls)
        return render(
            request,
            'project_update_domain.html',
            {
                'form': form,
                'project': project,
                'ip': domain,
                'netlify_urls': netlify_urls,
            },
        )

    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        project = get_object_or_404(Project, id=project_id)
        form = ProjectDomainForm(request.POST, instance=project)
        domain = (
            project.netlify_site_url.replace('https://', '').replace('http://', '')
            if project.netlify_site_url
            else ''
        )
        if form.is_valid():
            project = form.save()
            try:
                self.add_netlify_new_domain(project)
            except ValidationError as e:
                form.add_error(None, str(e))
                netlify_urls = [
                    url for url in str(project.netlify_site_url_history).split(',') if url
                ]
                logger.warning('Netlify URLs for project %s: %s', project.id, netlify_urls)
                return render(
                    request,
                    'project_update_domain.html',
                    {
                        'form': form,
                        'project': project,
                        'ip': domain,
                        'netlify_urls': netlify_urls,
                    },
                )
            return redirect('client_domain', project_id=project.id)

        domain = (
            project.netlify_site_url.replace('https://', '').replace('http://', '')
            if project.netlify_site_url
            else ''
        )
        return render(
            request,
            'project_update_domain.html',
            {'form': form, 'project': project, 'ip': domain},
        )

    def add_new_domain(self, project: Project) -> None:
        config = NGINX_TEMPLATE.format(domain=project.client_domain, project_id=project.id)
        conf_path = f'/etc/nginx/sites-available/{project.client_domain}'
        with open(conf_path, 'w') as f:
            f.write(config)

        os.system(f'ln -s {conf_path} /etc/nginx/sites-enabled/')
        os.system('nginx -s reload')

    def add_netlify_new_domain(self, project: Project) -> None:
        if not project.client_domain:
            return
        logger.info('Adding Netlify domain: %s', project.client_domain)
        client = NetlifyClient()
        try:
            client.update_site(
                project.netlify_site_id,
                {
                    'custom_domain': project.client_domain,
                    'record_txt_value': 'cpp',
                },
            )
            logger.info(
                'Domain %s assigned to site %s',
                project.client_domain,
                project.netlify_site_id,
            )
        except Exception as e:
            error_message = f'Failed to assign domain: {e}'
            logger.error(error_message)
            raise ValidationError(error_message)


class PublishProjectView(APIView):
    """Builds and deploys a project to Netlify."""

    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        project = get_object_or_404(Project, id=project_id)
        deployment_service = DeploymentService()
        base_output_dir = os.path.join(settings.BASE_DIR, 'project_zips')
        os.makedirs(base_output_dir, exist_ok=True)
        project_slug = slugify(project.name)
        project_folder = os.path.join(base_output_dir, project_slug)
        deployment_service.build_and_deploy(project, project_folder)
        return HttpResponse({'message': 'Project published successfully.'}, status=200)


class CreateProjectPageView(APIView):
    """Creates a new project page (service page) via a form."""

    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        form = CreateServicePageForm(request.POST)

        if form.is_valid():
            project = get_object_or_404(Project, id=project_id)
            data = form.cleaned_data
            name = data.get('name', '')
            prompt = data.get('prompt', '')

            project_page = ProjectPage(
                project=project,
                name=name,
                slug=slugify(name),
                type='other',
                status='In progress',
            )

            project_page.save()

            create_project_page.delay(project.id, project_page.id, name, prompt)

        return redirect('project_detail', project_id=project_id)


class ProjectDeleteAPIView(APIView):
    """Deletes a project and redirects to the projects listing."""

    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest, project_id: int, format: Optional[str] = None) -> HttpResponse:
        project = get_object_or_404(Project, pk=project_id)
        project.delete()
        return redirect(reverse('projects'))


class PageDeleteAPIView(APIView):
    """Deletes a project page and removes its link from the base HTML."""

    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest, project_id: int, page_id: int) -> HttpResponse:
        page = get_object_or_404(ProjectPage, pk=page_id)
        page.delete()

        project = get_object_or_404(Project, pk=project_id)
        base_html = project.base_html
        project.base_html = remove_link_from_html(base_html, page.name)
        project.save()

        return redirect('project_detail', project_id=project_id)


class CityDeleteAPIView(APIView):
    """Deletes a city and redirects to the project detail page."""

    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest, project_id: int, city_id: int) -> HttpResponse:
        city = get_object_or_404(City, pk=city_id)
        city.delete()
        return redirect('project_detail', project_id=project_id)


class DeleteNetlifySiteView(APIView):
    """Deletes a Netlify site and updates the project's URL history."""

    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        project = get_object_or_404(Project, pk=project_id)
        site_url = request.POST.get('site_url')

        client = NetlifyClient()
        error = ''

        try:
            sites = client.get_sites()
        except NetlifyAPIError as e:
            error = f'Failed to fetch sites: {e}'

        site_id: Optional[str] = None
        if not error:
            for site in sites:
                if site.get('url') == site_url or site.get('ssl_url') == site_url:
                    site_id = site.get('id')
                    break

        if not site_id:
            project.netlify_site_url_history = ','.join(
                url
                for url in str(project.netlify_site_url_history).split(',')
                if url != site_url
            )
            project.netlify_site_url = (
                '' if project.netlify_site_url == site_url else project.netlify_site_url
            )
            project.save()
            return redirect('client_domain', project_id=project_id)

        try:
            client.delete_site(site_id)
        except NetlifyAPIError as e:
            error = f'Failed to delete site: {e}'

        project.netlify_site_url_history = ','.join(
            url
            for url in str(project.netlify_site_url_history).split(',')
            if url != site_url
        )
        project.netlify_site_url = (
            '' if project.netlify_site_url == site_url else project.netlify_site_url
        )
        project.save()

        if error:
            form = ProjectDomainForm(data={}, instance=project)
            form.is_valid()
            form.add_error(None, error)
            domain = (
                project.netlify_site_url.replace('https://', '').replace('http://', '')
                if project.netlify_site_url
                else ''
            )
            netlify_urls = str(project.netlify_site_url_history).split(',')
            return render(
                request,
                'project_update_domain.html',
                {'form': form, 'project': project, 'ip': domain, 'netlify_urls': netlify_urls},
            )

        return redirect('client_domain', project_id=project_id)


@csrf_exempt
def save_page(
    request: HttpRequest,
    page_id: Optional[int] = None,
    city_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> JsonResponse:
    """Save page content from the GrapesJS editor."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    data = json.loads(request.body)
    complete_html = clean_html(data.get('html', ''))
    new_version_dict: dict[str, Any] = {}

    soup = BeautifulSoup(complete_html, 'html.parser')
    content_div = soup.find('div', id='content-container')
    content_html = content_div.decode_contents() if content_div else ''
    content_div.clear()
    content_div.append('||CONTENT||')
    base_html = str(soup)

    if data.get('is_service_page'):
        if page_id:
            page = get_object_or_404(Page, id=page_id)
            page.complete_html = complete_html
            page.save()

        elif city_id:
            city = get_object_or_404(City, id=city_id)
            city.complete_html = complete_html
            city.content_html = content_html
            city.meta_tags = data.get('meta_tags', '')
            city.save()

            new_version = CityPageVersions.objects.create(
                city_page=city,
                complete_html=city.complete_html,
                name='Version',
            )
            new_version_dict = {
                'id': new_version.id,
                'name': new_version.name,
                'created_at': new_version.created_at.isoformat(),
            }
    else:
        project = get_object_or_404(Project, id=project_id)
        page_obj = project.pages.filter(id=page_id).first()
        page_obj.meta_tags = data.get('meta_tags', '')

        project.tracking_code_head = data.get('tracking_code_head', '')
        project.tracking_code_body = data.get('tracking_code_body', '')
        project.base_html = base_html
        project.save()

        if page_obj.name == 'homepage':
            page_obj.complete_html = complete_html
            page_obj.content_html = str(content_html)
            head_tags = re.findall(r'<head>(.*?)</head>', complete_html, re.DOTALL)
            style_tags = re.findall(r'<style>(.*?)</style>', complete_html, re.DOTALL)

            if head_tags:
                page_obj.head = ''.join(f'<head>{h}</head>' for h in head_tags)
            if style_tags:
                page_obj.css = f'<style>{" ".join(style_tags)}</style>'

            page_obj.header = extract_tag_content('header', complete_html) or page_obj.header
            page_obj.footer = extract_tag_content('footer', complete_html) or page_obj.footer
            page_obj.save()

            new_version = ProjectPageVersion.objects.create(
                project_page=page_obj,
                complete_html=page_obj.complete_html,
                name='Version',
            )
            new_version_dict = {
                'id': new_version.id,
                'name': new_version.name,
                'created_at': new_version.created_at.isoformat(),
            }

        else:
            page_obj.complete_html = complete_html
            page_obj.content_html = content_html
            page_obj.header = extract_tag_content('header', complete_html) or page_obj.header
            page_obj.footer = extract_tag_content('footer', complete_html) or page_obj.footer
            page_obj.save()

    return JsonResponse(
        {
            'success': True,
            'message': 'Page saved successfully.',
            'version': new_version_dict,
        }
    )


@csrf_exempt
def get_version_html(
    request: HttpRequest,
    page_id: Optional[int] = None,
    city_id: Optional[int] = None,
    project_id: Optional[int] = None,
    version_id: Optional[int] = None,
) -> JsonResponse:
    """Retrieve the HTML for a specific version of a page."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    data = json.loads(request.body)
    page_id = data.get('page_id')
    city_id = data.get('city_id')
    version_id = data.get('version_id')

    if data.get('is_service_page'):
        if page_id:
            pass
        elif city_id:
            city_page = get_object_or_404(CityPageVersions, id=version_id)
            return JsonResponse(
                {'html': city_page.complete_html, 'success': True}, status=200
            )
    else:
        homepage_obj = get_object_or_404(ProjectPageVersion, id=version_id)
        return JsonResponse(
            {'html': homepage_obj.complete_html, 'success': True}, status=200
        )


@csrf_exempt
def regenerate_html(request: HttpRequest, project_id: int) -> JsonResponse:
    """Regenerate HTML content using AI based on a prompt."""
    if request.method == 'POST':
        data = json.loads(request.body)
        prompt = data.get('prompt')
        html = data.get('html')
        page_id = data.get('page_id')
        city_id = data.get('city_id')
        is_service_page = data.get('is_service_page')

        html = re.sub(r'data-gjs-highlightable="true"', '', html)
        html = re.sub(r'class="[^"]*?gjs-selected"', '', html)
        html = re.sub(r'data-gjs-type="[^"]"', '', html)
        html = re.sub(r'draggable="true"', '', html)

        project = get_object_or_404(Project, id=project_id)

        if is_service_page:
            if page_id:
                page = get_object_or_404(Page, id=page_id)
                is_openai = project.model.lower() == 'openai'
            elif city_id:
                city = get_object_or_404(City, id=city_id)
                is_openai = project.model.lower() == 'openai'
        else:
            is_openai = project.model.lower() == 'openai'

            if data.get('save_history') == 'true':
                html = project.base_html

        ai_response = generate_content(
            REGENERATION_PROMPT.format(prompt=prompt, html=html), 0.0, is_openai
        )
        regenerated_html = ai_response

        if not is_service_page and data.get('save_history') == 'true':
            project.base_html = ai_response
            project.save()

            homepage_obj = project.pages.filter(slug='homepage').first()
            homepage_obj.complete_html = project.base_html.replace(
                '||CONTENT||', str(homepage_obj.content_html)
            )
            homepage_obj.save()

            regenerated_html = homepage_obj.complete_html

            ProjectPromptHistory.objects.create(
                complete_html=regenerated_html,
                prompt=prompt,
                project=project,
            )

        return JsonResponse(
            {'html': regenerated_html, 'success': True}, status=200
        )


def update_header_links(request: HttpRequest, project_id: int) -> HttpResponse:
    """Update the visibility of header links based on user selection."""
    if request.method == 'POST':
        data = json.loads(request.body)
        visible_links = data.get('visible_links', [])

        project = get_object_or_404(Project, id=project_id)

        soup = BeautifulSoup(project.base_html, 'html.parser')
        header = soup.find('header')

        for a in header.find_all('a'):
            if 'logo' in str(a):
                continue
            link_text = a.text.strip()
            tag = a.parent if a.parent.name == 'li' else a
            existing_style = tag.get('style', '')
            if link_text not in visible_links:
                if 'display: none' not in existing_style:
                    new_style = (
                        existing_style + '; display: none;'
                        if existing_style
                        else 'display: none;'
                    )
                    tag['style'] = new_style

            else:
                styles = [
                    s.strip()
                    for s in existing_style.split(';')
                    if s.strip() and s.strip().lower() != 'display: none'
                ]
                tag['style'] = '; '.join(styles)

        project.base_html = str(soup)
        project.save()

        return redirect('project_detail', project_id=project_id)