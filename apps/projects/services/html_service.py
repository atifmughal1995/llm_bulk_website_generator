"""Service for HTML rendering and processing."""

import logging
from typing import Any, Optional

from bs4 import BeautifulSoup
import django.template as dt

from .renderers.html_renderer import render_section_content
from .enums import SectionType

logger = logging.getLogger(__name__)


class HTMLRenderer:
    """Service for rendering HTML from AI-generated content."""

    def render_service_page(
        self,
        page: Any,
        project: Any,
        template: Any,
        edit_mode: bool = False,
    ) -> str:
        """Render a service page HTML from AI-generated content.

        Args:
            page: The Page model instance.
            project: The Project model instance.
            template: The Template model instance.
            edit_mode: Whether to return edit-mode data.

        Returns:
            The rendered HTML string.
        """
        if page.complete_html and not edit_mode:
            return page.complete_html

        if not page.ai_response:
            return project.base_html.replace('||CONTENT||', '')

        ai_content = self._parse_ai_content(page)
        section_images = self._parse_section_images(page)
        template_sections = (
            template.template_sections.all()
            .order_by('order')
            .select_related('section')
        )

        general_images = section_images.get(SectionType.GALLERY.value, [])
        testimonial_images = section_images.get(SectionType.TESTIMONIAL.value, [])

        sections_data = self._build_sections_data(
            template_sections, ai_content, section_images, general_images, testimonial_images
        )

        if edit_mode:
            from django.http import JsonResponse
            return JsonResponse(sections_data, status=200).content.decode()

        return self._assemble_page_html(template, sections_data, project)

    def _parse_ai_content(self, page: Any) -> dict:
        """Parse AI-generated content from page."""
        import ast
        ai_content: dict[str, Any] = {}
        ai_generated_content_prompts: dict[str, str] = {}

        ai_section_content = (
            page.ai_generated_contents.filter(
                content__isnull=False,
            )
            .exclude(template_section__section__name=SectionType.RELATED_ZIP_CODES.value)
            .order_by('template_section__order')
            .values_list('template_section__section__name', 'content', 'prompt')
        )

        for item in ai_section_content:
            try:
                ai_content[item[0]] = ast.literal_eval(item[1])
                ai_generated_content_prompts[item[0]] = item[2] if item[2] else ''
            except Exception as err:
                logger.warning('Failed to parse AI content for section: %s', err)

        return ai_content

    def _parse_section_images(self, page: Any) -> dict:
        """Parse section images from page."""
        import ast
        return ast.literal_eval(page.images) if page.images else {}

    def _build_sections_data(
        self,
        template_sections: Any,
        ai_content: dict,
        section_images: dict,
        general_images: list,
        testimonial_images: list,
    ) -> dict:
        """Build section data for rendering."""
        from .prompts import NO_CONTENT_SECTION_HTML
        sections_data: dict[str, Any] = {}

        for ts in template_sections:
            section_data = ai_content.get(ts.section.name, {})
            listing_data = section_data.get('data', [])
            section_image = section_images.get(ts.section.name, '')

            for item in listing_data:
                if ts.section.name.lower() in (
                    SectionType.TESTIMONIAL.value,
                    SectionType.CUSTOMER.value,
                ):
                    item['image'] = (
                        testimonial_images.pop() if testimonial_images else ''
                    )
                else:
                    item['image'] = (
                        general_images.pop() if general_images else section_image
                    )

            if ts.default_content:
                html = render_section_content(ts, section_data, general_images, section_image)
                content_html = html

                sections_data.update({
                    ts.section.name: {
                        'data': section_data,
                        'html': html,
                        'prompt': '',
                    }
                })

        return sections_data

    def _assemble_page_html(
        self, template: Any, sections_data: dict, project: Any
    ) -> str:
        """Assemble the final page HTML."""
        template_head = template.head if template.head else ''
        template_header = dt.Template(template.header).render(
            dt.Context({'project_id': project.id})
        )
        template_footer = template.footer if template.footer else ''

        return (
            f'{template_head}{template_header}{template_footer}'
        )