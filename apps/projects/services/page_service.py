"""Service for page-related operations."""

import logging
from typing import Optional

from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import (
    AIGeneratedContent,
    City,
    CityPageVersions,
    Page,
    Project,
    ProjectPage,
    ProjectPageVersion,
    State,
    TemplateSection,
)
from .exceptions import PageBuildError
from .ai_service import AIService
from .enums import PageType

logger = logging.getLogger(__name__)


class PageService:
    """Service for creating and managing pages."""

    def __init__(self, ai_service: Optional[AIService] = None) -> None:
        self._ai_service = ai_service or AIService()

    def create_service_page(
        self,
        project: Project,
        name: str,
        target_region: str,
        template_id: int,
        temperature: float = 0.0,
        zip_code: Optional[str] = None,
        city_id: Optional[int] = None,
        page_id: Optional[int] = None,
    ) -> Page:
        """Create a service page with AI-generated content.

        Args:
            project: The project to create the page for.
            name: The page name.
            target_region: The target region for the page.
            template_id: The template ID to use.
            temperature: The AI temperature setting.
            zip_code: Optional zip code.
            city_id: Optional city ID.
            page_id: Optional existing page ID to update.

        Returns:
            The created or updated Page instance.
        """
        sections = (
            TemplateSection.objects.filter(template_id=template_id)
            .select_related('section')
            .values('id', 'section__name')
        )
        sections_names = ', '.join(s['section__name'] for s in sections)

        from .prompts import INITIAL_PROMPT_STRUCTURE

        prompt = INITIAL_PROMPT_STRUCTURE.format(
            company_name=project.name,
            service_type=project.service_type,
            target_region=target_region,
            sections=sections_names,
            zip_code=zip_code or '',
        )

        ai_generated_content = self._ai_service.generate(
            prompt, temperature, project.model.lower() == 'openai'
        )

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

        self._create_template_sections(ai_generated_content, sections, page)
        return page

    def _create_template_sections(
        self,
        ai_generated_content: dict,
        sections: list,
        page: Page,
    ) -> None:
        """Create AI generated content entries for template sections."""
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

    def create_city_page(
        self,
        project: Project,
        city: City,
        temperature: float = 0.0,
        prompt: str = '',
    ) -> City:
        """Create a city page with AI-generated content.

        Args:
            project: The project to create the page for.
            city: The city to create the page for.
            temperature: The AI temperature setting.
            prompt: Additional prompt guidance.

        Returns:
            The updated City instance.
        """
        from .prompts import CITY_PAGE_PROMPT, DEFAULT_SERVICE_PAGE_SECTIONS

        sections_names = DEFAULT_SERVICE_PAGE_SECTIONS

        formatted_prompt = CITY_PAGE_PROMPT.format(
            company_name=project.name,
            service_type=project.service_type,
            target_region=city.name,
            sections=sections_names,
            base_html=project.base_html,
            additional_guideline=prompt,
        )

        ai_generated_content = self._ai_service.generate(
            formatted_prompt, temperature, project.model.lower() == 'openai'
        )

        import re
        matches = re.findall(r'```html(.*?)```', ai_generated_content, re.DOTALL)
        head_tag = matches[0].strip() if matches else ''
        clean_content = (
            matches[1].strip() if len(matches) > 1 else ''
        )

        city.prompt = formatted_prompt
        city.ai_response = ai_generated_content
        city.content_html = clean_content
        city.complete_html = project.base_html.replace('||CONTENT||', clean_content)
        city.status = CityStatus.COMPLETED.value

        from .image_utils import html_regenerate_broken_img
        city.content_html = html_regenerate_broken_img(city.content_html, project.id)

        city.save()

        CityPageVersions.objects.create(
            city_page=city,
            complete_html=city.complete_html,
            name='Default',
        )

        return city

    def create_project_page(
        self,
        project: Project,
        name: str,
        additional_prompt: str = '',
    ) -> ProjectPage:
        """Create a project page with AI-generated content.

        Args:
            project: The project to create the page for.
            name: The page name.
            additional_prompt: Additional prompt guidance.

        Returns:
            The created ProjectPage instance.
        """
        from .prompts import PROJECT_PAGE_PROMPT
        from django.urls import reverse

        prompt = PROJECT_PAGE_PROMPT.format(
            page_name=name,
            company_name=project.name,
            service_type=project.service_type,
            base_html=project.base_html,
            additional_guideline=additional_prompt,
            page_link=reverse('other_page', args=[project.id, name.lower().replace(' ', '-')]),
        )

        ai_generated_content = self._ai_service.generate(
            prompt, 0.0, project.model.lower() == 'openai'
        )

        project_page = ProjectPage.objects.create(
            project=project,
            name=name,
            slug=name.lower().replace(' ', '-'),
            type='other',
            status='In progress',
            ai_response=ai_generated_content,
        )

        import re
        matches = re.findall(r'```html(.*?)```', ai_generated_content, re.DOTALL)
        project_page.content_html = (
            matches[0].strip() if len(matches) > 0 else ''
        )
        project_page.complete_html = project.base_html.replace(
            '||CONTENT||', project_page.content_html
        )
        project_page.status = 'Completed'
        project_page.save()

        return project_page