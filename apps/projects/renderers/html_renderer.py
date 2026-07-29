"""Renderer for HTML sections and templates."""

import logging
from typing import Any

import django.template as dt
from bs4 import BeautifulSoup

from .prompts import NO_CONTENT_SECTION_HTML
from ..html_utils import inject_tracking_code, inject_javascript_redirect

logger = logging.getLogger(__name__)


def render_section_content(
    template_section: Any,
    section_data: dict,
    general_images: list,
    section_image: str,
) -> str:
    """Render a single section's content from template and data.

    Args:
        template_section: The TemplateSection instance.
        section_data: The AI-generated data for this section.
        general_images: List of general images to use.
        section_image: Default image for this section.

    Returns:
        The rendered HTML string.
    """
    if template_section.section.name.lower() == 'gallery':
        html = template_section.default_content or ''
        while '{{image}}' in html:
            html = html.replace(
                '{{image}}',
                general_images.pop() if general_images else section_image,
                1,
            )
        return html

    return dt.Template(template_section.default_content).render(
        dt.Context(
            {
                'h1': section_data.get('h1', ''),
                'h2': section_data.get('h2', ''),
                'content': section_data.get('content', ''),
                'data': section_data.get('data', []),
                'image': section_image,
                'general_images': general_images,
                'iframe_src': section_data.get('iframe_src', ''),
            }
        )
    )


def render_page_html(
    base_html: str,
    content_html: str,
    project: Any,
    page: Any,
) -> str:
    """Render a complete page HTML with base template and content.

    Args:
        base_html: The base HTML template.
        content_html: The content HTML to inject.
        project: The Project instance.
        page: The page instance (Page or ProjectPage or City).

    Returns:
        The complete rendered HTML string.
    """
    html = base_html.replace('||CONTENT||', content_html)
    html = inject_tracking_code(html, project)
    html = inject_javascript_redirect(html)

    if project.contact_phone_number:
        html = html.replace('||CONTACT_PHONE_NO||', project.contact_phone_number)

    if 'gjs-dashed' in base_html:
        html = _inject_scripts(html, project)

    return html


def render_listing_html(
    base_html: str,
    content_html: str,
    project: Any,
) -> str:
    """Render a listing page (states, counties, cities) HTML.

    Args:
        base_html: The base HTML template.
        content_html: The content HTML to inject.
        project: The Project instance.

    Returns:
        The complete rendered HTML string.
    """
    html = base_html.replace('||CONTENT||', content_html)
    html = inject_tracking_code(html, project)
    html = inject_javascript_redirect(html)

    if project.contact_phone_number:
        html = html.replace('||CONTACT_PHONE_NO||', project.contact_phone_number)

    if 'gjs-dashed' in base_html:
        html = _inject_scripts(html, project)

    return html


def _inject_scripts(html: str, project: Any) -> str:
    """Inject project scripts into HTML before closing footer tag."""
    soup = BeautifulSoup(html, 'html.parser')
    new_script_tag = soup.new_tag('script')
    new_script_tag.string = project.scripts if project.scripts else ''
    footer = soup.find('footer')
    if footer and footer.parent:
        footer.insert_after(new_script_tag)
    return str(soup)