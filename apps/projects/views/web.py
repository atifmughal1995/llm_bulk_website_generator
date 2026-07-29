import json
import ast
import re
import os
from typing import Any, Optional

from bs4 import BeautifulSoup

import django.template as dt
from django.utils.text import slugify
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.contrib.auth.decorators import login_required

from .models import (
    TemplateSection,
    AIGeneratedContent,
    Page,
    Template,
    State,
    County,
    City,
    Project,
    ProjectPage,
    ProjectPageVersion,
    CityPageVersions,
    ProjectPromptHistory,
)
from .prompts import (
    INITIAL_PROMPT_STRUCTURE,
    REWRITE_SECTION_PROMPT,
    CITY_PAGE_PROMPT,
    NO_CONTENT_SECTION_HTML,
    HOMEPAGE_PROMPT,
    DEFAULT_HOMEPAGE_SECTIONS,
    DEFAULT_SERVICE_PAGE_SECTIONS,
    REGENERATION_PROMPT,
    NGINX_TEMPLATE,
    JAVASCRIPT_REDIRECTING_SNIPPET,
    EMAILJS_CODE_SNIPPET,
    PROJECT_PAGE_PROMPT,
)
from .serializers import PageSerializer, TemplateSerializer, ProjectDomainSerializer
from .ai_utils import generate_content
from .image_utils import get_image, get_placeholder, get_images
from .forms import ProjectForm, UploadFileForm, ProjectDomainForm, CreateServicePageForm
from .html_utils import update_meta_tag, clean_html, extract_tag_content
from .tasks import process_project_creation, process_excel_task
from .renderers.html_renderer import render_page_html, render_listing_html


def homepage(request: HttpRequest, project_id: int) -> HttpResponse:
    """Render the homepage for a project."""
    project = get_object_or_404(Project, id=project_id)
    homepage_obj = project.pages.filter(slug='homepage').first()
    html = _render_project_page(project, homepage_obj)
    html = f'{JAVASCRIPT_REDIRECTING_SNIPPET}{html}'
    html = update_meta_tag(homepage_obj, html)
    return _finalize_page_response(project, html, homepage_obj)


def service_detail_page(request: HttpRequest, project_id: int, slug: str) -> HttpResponse:
    """Render a service detail page for a project."""
    project = get_object_or_404(Project, id=project_id)
    service_page = project.pages.filter(slug=slug).first()
    html = _render_project_page(project, service_page)
    html = f'{JAVASCRIPT_REDIRECTING_SNIPPET}{html}'
    html = update_meta_tag(service_page, html)
    return _finalize_page_response(project, html, service_page)


def other_page(request: HttpRequest, project_id: int, slug: str) -> HttpResponse:
    """Render a generic project page."""
    project = get_object_or_404(Project, id=project_id)
    page = project.pages.filter(slug=slug).first()
    html = _render_project_page(project, page)
    html = f'{JAVASCRIPT_REDIRECTING_SNIPPET}{html}'
    html = update_meta_tag(page, html)
    return _finalize_page_response(project, html, page)


def city_page(request: HttpRequest, project_id: int, city_id: int) -> HttpResponse:
    """Render a city page for a project."""
    city = get_object_or_404(City, id=city_id)
    project = city.county.state.project
    html = _render_city_page(project, city)
    html = f'{JAVASCRIPT_REDIRECTING_SNIPPET}{html}'
    html = update_meta_tag(city, html)
    return _finalize_page_response(project, html, city)


def _render_project_page(project: Project, page: Optional[ProjectPage]) -> str:
    """Render a project page HTML from base template and page content."""
    if page and page.complete_html:
        return page.complete_html
    if page and page.content_html:
        return project.base_html.replace('||CONTENT||', page.content_html)
    return render_to_string('no_content.html', request=None)


def _render_city_page(project: Project, city: City) -> str:
    """Render a city page HTML from base template and city content."""
    if city and city.content_html:
        return project.base_html.replace('||CONTENT||', city.content_html)
    return project.base_html.replace('||CONTENT||', NO_CONTENT_SECTION_HTML)


def _finalize_page_response(
    project: Project, html: str, page: Optional[ProjectPage] = None
) -> HttpResponse:
    """Add tracking code, phone number, and scripts to page HTML."""
    html = html.replace(
        '</head>',
        f'{project.tracking_code_head if project.tracking_code_head else ""}</head>',
    )
    html = html.replace(
        '</body>',
        f'{project.tracking_code_body if project.tracking_code_body else ""}</body>',
    )

    if project.contact_phone_number:
        html = html.replace('||CONTACT_PHONE_NO||', project.contact_phone_number)

    if 'gjs-dashed' in project.base_html:
        soup = BeautifulSoup(html, 'html.parser')
        new_script_tag = soup.new_tag('script')
        new_script_tag.string = project.scripts if project.scripts else ''
        footer = soup.find('footer')
        if footer and footer.parent:
            footer.insert_after(new_script_tag)
        return HttpResponse(str(soup), status=200)

    return HttpResponse(html, status=200)


@login_required
def projects_listing(request: HttpRequest) -> HttpResponse:
    """Render the projects listing page."""
    template = Template.objects.get(name='Default')
    css = f'<style>{template.css}</style>'
    projects = Project.objects.all().order_by('-id')
    html = render_to_string('projects_listing.html', {'projects': projects}, request=request)
    html = f'{JAVASCRIPT_REDIRECTING_SNIPPET}{html}'
    return HttpResponse(html, status=200)


@login_required
def project_detail(request: HttpRequest, project_id: int) -> HttpResponse:
    """Render the project detail page."""
    project = get_object_or_404(Project, id=project_id)
    states = project.states.all()
    services = project.pages.filter(type='service')
    other_pages = project.pages.exclude(type='service').order_by('id')
    total_cities = City.objects.filter(county__state__project=project).count()
    queued_cities = City.objects.filter(
        county__state__project=project, status='queued'
    ).count()
    form = CreateServicePageForm()

    header_links: list[dict[str, Any]] = []
    soup = BeautifulSoup(project.base_html, 'html.parser')
    header = soup.find('header')
    unique_links: set[str] = set()
    for a in header.find_all('a'):
        if 'logo' in str(a):
            continue
        link_text = a.text.strip()
        tag = a.parent if a.parent.name == 'li' else a
        style = tag.get('style', '')
        is_visible = (
            'display: none' not in style or 'display: none' not in str(tag)
        )

        link = a.get('href')
        if link in unique_links:
            continue

        unique_links.add(link)

        header_links.append(
            {'name': link_text, 'link': a['href'], 'show': is_visible}
        )

    return render(
        request,
        'project_detail.html',
        {
            'project': project,
            'states': states,
            'services': services,
            'other_pages': other_pages,
            'form': form,
            'total_cities': total_cities,
            'queued_cities': queued_cities,
            'header_links': header_links,
        },
    )


def states_listing(request: HttpRequest, project_id: int) -> HttpResponse:
    """Render the states listing page for a project."""
    project = get_object_or_404(Project, id=project_id)
    states = State.objects.filter(project_id=project_id).distinct()
    content_html = render_to_string(
        'states_listing.html',
        {'states': states, 'project_id': project_id},
        request=request,
    )
    html = render_listing_html(project.base_html, content_html, project)
    return HttpResponse(html, status=200)


def counties_listing(
    request: HttpRequest, project_id: int, state_id: int
) -> HttpResponse:
    """Render the counties listing page for a state."""
    project = get_object_or_404(Project, id=project_id)
    counties = County.objects.filter(state_id=state_id)
    if counties:
        content_html = render_to_string(
            'counties_listing.html',
            {'counties': counties, 'project_id': project_id},
            request=request,
        )
    else:
        content_html = NO_CONTENT_SECTION_HTML
    html = render_listing_html(project.base_html, content_html, project)
    return HttpResponse(html, status=200)


def cities_listing(
    request: HttpRequest, project_id: int, county_id: int
) -> HttpResponse:
    """Render the cities listing page for a county."""
    project = get_object_or_404(Project, id=project_id)
    cities = City.objects.filter(county_id=county_id)
    if cities:
        state_id = cities.first().county.state.id
        content_html = render_to_string(
            'cities_listing.html',
            {
                'cities': cities,
                'project_id': project_id,
                'state_id': state_id,
            },
            request=request,
        )
    else:
        content_html = NO_CONTENT_SECTION_HTML
    html = render_listing_html(project.base_html, content_html, project)
    return HttpResponse(html, status=200)


def zipcodes_listing(
    request: HttpRequest, project_id: int, city_id: int
) -> HttpResponse:
    """Render the zipcodes listing page for a city."""
    city = get_object_or_404(City, id=city_id)

    if city.complete_html:
        return HttpResponse(city.complete_html, status=200)

    project = get_object_or_404(Project, id=project_id)
    zipcodes = Page.objects.filter(city_id=city_id)
    if zipcodes:
        county_id = zipcodes.first().city.county.id
        content_html = render_to_string(
            'zipcodes_listing.html',
            {
                'zipcodes': zipcodes,
                'project_id': project_id,
                'county_id': county_id,
                'city_id': city_id,
            },
            request=request,
        )
    else:
        content_html = NO_CONTENT_SECTION_HTML
    html = render_listing_html(project.base_html, content_html, project)
    return HttpResponse(html, status=200)


@login_required
def grapesjs_editor(
    request: HttpRequest,
    page_id: Optional[int] = None,
    project_id: Optional[int] = None,
    city_id: Optional[int] = None,
    slug: Optional[str] = None,
) -> HttpResponse:
    """Render the GrapesJS editor for editing page content."""
    if settings.BACKEND_IP not in request.get_host() and '127.0.0.1' not in request.get_host():
        html = 'Permission denied.'
        return HttpResponse(html, status=200)

    if page_id:
        page = get_object_or_404(Page, id=page_id)
        project = page.city.county.state.project
        return render(
            request,
            'grapesjs_editor.html',
            {
                'page': page,
                'is_service_page': 'true',
                'project_id': project.id,
                'prompt_history': project.prompts.all(),
            },
        )
    elif slug:
        project = get_object_or_404(Project, id=project_id)
        page_obj = ProjectPage.objects.filter(project=project, slug=slug).first()

        page_obj.complete_html = project.base_html.replace(
            '||CONTENT||', page_obj.content_html
        )

        versions = page_obj.versions.all().order_by('-created_at')
        return render(
            request,
            'grapesjs_editor.html',
            {
                'page': page_obj,
                'is_service_page': 'false',
                'project_id': project.id,
                'project': project,
                'versions': versions,
                'prompt_history': project.prompts.all(),
            },
        )

    elif city_id:
        city = get_object_or_404(City, id=city_id)
        project = city.county.state.project
        city.complete_html = project.base_html.replace('||CONTENT||', city.content_html)
        versions = city.versions.all().order_by('-created_at')
        return render(
            request,
            'grapesjs_editor.html',
            {
                'page': city,
                'is_service_page': 'true',
                'project_id': project.id,
                'versions': versions,
                'prompt_history': project.prompts.all(),
            },
        )

    elif project_id:
        project = get_object_or_404(Project, id=project_id)
        homepage_obj = project.pages.filter(slug='homepage').first()
        homepage_obj.complete_html = project.base_html.replace(
            '||CONTENT||', homepage_obj.content_html
        )
        versions = homepage_obj.versions.all().order_by('-created_at')
        return render(
            request,
            'grapesjs_editor.html',
            {
                'page': homepage_obj,
                'is_service_page': 'false',
                'project_id': project.id,
                'project': project,
                'versions': versions,
                'prompt_history': project.prompts.all(),
            },
        )