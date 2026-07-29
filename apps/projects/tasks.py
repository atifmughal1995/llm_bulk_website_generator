import re
import logging
from typing import Any

from celery import shared_task
from django.urls import reverse

from .models import Project, ProjectPage, ProjectPageVersion
from .prompts import HOMEPAGE_PROMPT, DEFAULT_HOMEPAGE_SECTIONS, PROJECT_PAGE_PROMPT
from .html_utils import extract_meta_tags_html, remove_title_and_meta_tags, remove_head_tag
from .ai_utils import generate_content
from .models import (
    Project,
    UploadedFile,
    ProjectPage,
    State,
    County,
    City,
    CityPageVersions,
    CityStatus,
)
from .prompts import DEFAULT_SERVICE_PAGE_SECTIONS, CITY_PAGE_PROMPT
from .image_utils import html_regenerate_broken_img
from .services.page_service import PageService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_project_creation(
    self: Any, project_id: int, custom_prompt: str, create_service_page_flag: bool
) -> None:
    """Process project creation: generate homepage and service pages."""
    project = Project.objects.get(id=project_id)
    homepage_link = reverse('homepage', args=[project.id])
    service_area_link = reverse('states', args=[project.id])

    prompt = HOMEPAGE_PROMPT.format(
        service_type=project.service_type,
        sections=DEFAULT_HOMEPAGE_SECTIONS,
        homepage_link=homepage_link,
        service_detail_page_link=homepage_link.replace('homepage', 'service'),
        service_area_link=service_area_link,
        additional_guideline=custom_prompt if custom_prompt else 'None',
        create_service_page_flag='' if create_service_page_flag else '(IGNORE THIS POINT)',
    )

    project.prompt = prompt
    project.save()

    ai_generated_content = generate_content(prompt, 0.0, project.model.lower() == 'openai')

    project.homepage_ai_response = ai_generated_content

    project_page_obj = ProjectPage.objects.create(
        project=project,
        name='Homepage',
        slug='homepage',
        type='homepage',
        ai_response=ai_generated_content,
    )

    matches = re.findall(r'```html(.*?)```', ai_generated_content, re.DOTALL)
    base_html = matches[0].strip() if len(matches) > 0 else ''
    base_html = html_regenerate_broken_img(base_html, project_id)
    meta_tags = extract_meta_tags_html(base_html)
    project.base_html = remove_title_and_meta_tags(base_html)

    soup = BeautifulSoup(project.base_html, 'html.parser')
    script_tags = soup.find_all('script')
    all_scripts = ''
    for tag in script_tags:
        content = tag.string or tag.text or ''
        all_scripts += content.strip() + '\n'

    project.scripts = all_scripts

    project_page_obj.content_html = matches[1].strip() if len(matches) > 1 else ''
    project_page_obj.content_html = html_regenerate_broken_img(
        project_page_obj.content_html, project_id
    )
    project_page_obj.complete_html = project.base_html.replace(
        '||CONTENT||', project_page_obj.content_html
    )
    project_page_obj.meta_tags = meta_tags

    project_page_obj.save()

    ProjectPageVersion.objects.create(
        project_page=project_page_obj,
        complete_html=project_page_obj.complete_html,
        name='Default',
    )

    pattern = r'<!--\s*Service:\s*(.*?)\s*-->(.*?)<!--\s*/\s*(.*?)\s*-->'
    matches = re.findall(pattern, ai_generated_content, re.DOTALL)

    services = []
    for start_slug, content, end_slug in matches:
        slug = end_slug.strip()
        full_html = f'<!-- Service: {start_slug} -->{content}<!-- /{end_slug} -->'
        meta_tags = extract_meta_tags_html(full_html)
        full_html = remove_head_tag(full_html)

        services.append(
            {
                'slug': slug,
                'html': full_html.strip(),
                'meta_tags': meta_tags,
            }
        )

    project_pages = [
        ProjectPage(
            project=project,
            name=service['slug'].replace('-', ' ').title(),
            slug=service['slug'],
            ai_response=service['html'],
            content_html=service['html'],
            type='service',
            meta_tags=meta_tags,
        )
        for service in services
    ]
    ProjectPage.objects.bulk_create(project_pages)

    project.status = 'Created'
    project.save()


@shared_task(bind=True)
def process_excel_task(self: Any, obj_id: int, prompt: str) -> None:
    """Process an uploaded Excel file to create city pages."""
    obj = UploadedFile.objects.get(id=obj_id)
    workbook = load_workbook(obj.file.path)
    sheet = workbook.active
    page_service = PageService()

    for index, row in enumerate(sheet.iter_rows(values_only=True)):
        if index == 0 or not row[0] or not row[3] or not row[5]:
            continue

        state, _ = State.objects.get_or_create(
            name=row[3], abbreviation=row[2], project=obj.project
        )
        county, _ = County.objects.get_or_create(name=row[5], state=state)
        city, _ = City.objects.get_or_create(name=row[0], county=county)

        city.status = CityStatus.QUEUED.value
        city.save()

        logger.info('Processing city: %s', city.name)
        page_service.create_city_page(
            obj.project,
            city,
            obj.temperature or 0.0,
            prompt,
        )


@shared_task
def create_city_page(
    project_id: int, city_id: int, temperature: float = 0.0, prompt: str = ''
) -> None:
    """Create a city page with AI-generated content."""
    project = Project.objects.get(id=project_id)
    city = City.objects.get(id=city_id)
    page_service = PageService()
    page_service.create_city_page(project, city, temperature, prompt)


@shared_task(bind=True)
def create_project_page(
    self: Any, project_id: int, project_page_obj_id: int, name: str, additional_prompt: str
) -> None:
    """Create a project page with AI-generated content."""
    project = Project.objects.get(id=project_id)
    project_page_obj = ProjectPage.objects.get(id=project_page_obj_id)
    page_service = PageService()
    page_service.create_project_page(project, name, additional_prompt)