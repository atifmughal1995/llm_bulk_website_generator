"""HTML utility functions."""

import re
from typing import Any, Optional

from bs4 import BeautifulSoup


def update_meta_tag(page: Any, html: str) -> str:
    """Inject page-specific meta tags into HTML head.

    Args:
        page: The page model instance with meta_tags attribute.
        html: The HTML string to update.

    Returns:
        The updated HTML string.
    """
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.find('head')

    if head:
        new_head_content = BeautifulSoup(page.meta_tags, 'html.parser')
        for tag in new_head_content.contents:
            head.append(tag)

    return str(soup)


def clean_html(html: str) -> str:
    """Remove unwanted attributes and tags from HTML.

    Args:
        html: The HTML string to clean.

    Returns:
        The cleaned HTML string.
    """
    html = re.sub(r'data-gjs-highlightable="true"', '', html)
    html = re.sub(r'class="[^"]*?gjs-selected"', '', html)
    html = re.sub(r'draggable="true"', '', html)
    html = re.sub(r'data-gjs-type="[^"]+"', '', html)
    html = re.sub(r'<iframe class=.*?</iframe>', '', html)
    return html


def extract_tag_content(tag: str, html: str) -> str:
    """Extract specific tag content from HTML.

    Args:
        tag: The tag name to extract.
        html: The HTML string.

    Returns:
        The extracted tag content or empty string.
    """
    match = re.search(rf'<{tag}(.*?)</{tag}>', html, re.DOTALL)
    return f'<{tag}{match.group(1)}</{tag}>' if match else ''


def add_tracking_code(project: Any, html: str) -> str:
    """Add tracking code snippets to HTML head and body.

    Args:
        project: The Project instance with tracking_code_head and tracking_code_body.
        html: The HTML string to update.

    Returns:
        The updated HTML string.
    """
    html = html.replace(
        '</head>',
        f'{project.tracking_code_head if project.tracking_code_head else ""}</head>',
    )
    html = html.replace(
        '</body>',
        f'{project.tracking_code_body if project.tracking_code_body else ""}</body>',
    )
    return html


def remove_link_from_html(html: str, link_name: str) -> str:
    """Remove a navigation link from the header or footer of HTML.

    Args:
        html: The HTML string.
        link_name: The text of the link to remove.

    Returns:
        The updated HTML string.
    """
    soup = BeautifulSoup(html, 'html.parser')

    for section_tag in ['header', 'footer']:
        section = soup.find(section_tag)
        if not section:
            continue

        for a in section.find_all('a'):
            if 'logo' in str(a).lower():
                continue

            link_text = a.text.strip()
            if link_text == link_name:
                tag_to_remove = a.parent if a.parent.name == 'li' else a
                tag_to_remove.decompose()
                break

    return str(soup)


def update_links(
    html: str,
    pages_links_mapping: dict[str, str] = {},
    states_links_mapping: dict[int, str] = {},
    counties_links_mapping: dict[int, str] = {},
    cities_links_mapping: dict[int, str] = {},
) -> str:
    """Update internal links in HTML to use relative paths.

    Args:
        html: The HTML string to update.
        pages_links_mapping: Mapping of page slugs to relative links.
        states_links_mapping: Mapping of state IDs to relative links.
        counties_links_mapping: Mapping of county IDs to relative links.
        cities_links_mapping: Mapping of city IDs to relative links.

    Returns:
        The updated HTML string.
    """
    html = re.sub(r'"/project/\d+/homepage/"', '"./index.html"', html)
    html = re.sub(r'"/project/\d+/states/"', '"./states.html"', html)
    html = re.sub(r'"/project/\d+/page/([\w-]+)/"', r'"/\1.html"', html)
    html = re.sub(r'"/project/\d+/service/([\w-]+)/"', r'"/\1.html"', html)
    html = re.sub(r'<a.*?project/\d+/city/\d+/edit/.*?</a>', '', html)
    html = html.replace('/media/regenerated_images/', './')

    for id, link in states_links_mapping.items():
        html = re.sub(rf'"/project/\d+/counties/{id}/"', f'"{link}"', html)

    for id, link in counties_links_mapping.items():
        html = re.sub(rf'"/project/\d+/cities/{id}/"', f'"{link}"', html)

    for id, link in cities_links_mapping.items():
        html = re.sub(rf'"/project/\d+/city/{id}/"', f'"{link}"', html)

    return html


def extract_meta_tags_html(html: str, extract_all: bool = False) -> str:
    """Extract meta tags and title from HTML head.

    Args:
        html: The HTML string.
        extract_all: Whether to extract all meta tags or skip common ones.

    Returns:
        The extracted meta tags as HTML string.
    """
    soup = BeautifulSoup(html, 'html.parser')
    tags: list[str] = []

    title_tag = soup.find('title')
    if title_tag:
        tags.append(str(title_tag))

    for tag in soup.find_all('meta'):
        if not extract_all:
            if tag.get('charset') == 'UTF-8':
                continue
            if tag.get('name') == 'viewport':
                continue
            if tag.get('name') == 'robots':
                continue
            if 'google' in tag.get('name', '').lower():
                continue
            tags.append(str(tag))

    pretty_output = BeautifulSoup('\n'.join(tags), 'html.parser').prettify()
    return pretty_output


def remove_title_and_meta_tags(html: str, remove_all: bool = False) -> str:
    """Remove title and meta tags from HTML head.

    Args:
        html: The HTML string.
        remove_all: Whether to remove all meta tags or just common ones.

    Returns:
        The HTML string without title and meta tags.
    """
    soup = BeautifulSoup(html, 'html.parser')
    head = soup.find('head')

    if head:
        title_tag = head.find('title')
        if title_tag:
            title_tag.decompose()

        for tag in head.find_all('meta'):
            if not remove_all:
                if tag.get('charset') == 'UTF-8':
                    continue
                if tag.get('name') == 'viewport':
                    continue
                if tag.get('name') == 'robots':
                    continue
                if 'google' in tag.get('name', '').lower():
                    continue
            tag.decompose()

    return str(soup)


def remove_head_tag(html: str) -> str:
    """Remove the head tag and its contents from HTML.

    Args:
        html: The HTML string.

    Returns:
        The HTML string without the head tag.
    """
    soup = BeautifulSoup(html, 'html.parser')

    if soup.head:
        soup.head.decompose()

    return str(soup)


def inject_tracking_code(html: str, project: Any) -> str:
    """Inject tracking code snippets into HTML head and body.

    Args:
        html: The HTML string to update.
        project: The Project instance with tracking_code_head and tracking_code_body.

    Returns:
        The updated HTML string.
    """
    html = html.replace(
        '</head>',
        f'{project.tracking_code_head if project.tracking_code_head else ""}</head>',
    )
    html = html.replace(
        '</body>',
        f'{project.tracking_code_body if project.tracking_code_body else ""}</body>',
    )
    return html


def inject_javascript_redirect(html: str) -> str:
    """Inject JavaScript redirect snippet into HTML.

    Args:
        html: The HTML string to update.

    Returns:
        The updated HTML string.
    """
    from django.conf import settings

    snippet = f"""
<script>
document.addEventListener("DOMContentLoaded", function() {{
    if (!window.location.href.includes("{settings.BACKEND_IP}") && !window.location.href.includes("127.0.0.1")) {{
        const links = document.querySelectorAll("a[href]");
        links.forEach(link => {{
            link.href = link.href.replace(/\\/project\\/\\d+\\//, "/");
        }});
    }}
}});
</script>
"""
    html = html.replace('</body>', f'{snippet}</body>')
    return html