import requests
import openai
import logging
import os
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.conf import settings
from typing import Optional

from .models import RegeneratedImage

logger = logging.getLogger(__name__)


ACCESS_KEY = 'Szt1RzfsmiV1UE8aXkEXUsNz2ajCkmfw68JYd6cEWJ4'
PLACEHOLDER = 'https://eadn-wc04-920528.nxedge.io/wp-content/uploads/2023/02/placeholder-726.png'
url = 'https://api.unsplash.com/photos/random'
headers = {'Authorization': f'Client-ID {ACCESS_KEY}'}


def get_image(query: str) -> str:
    """Fetch a single image URL from Unsplash for a given query."""
    try:
        params = {'query': query, 'count': 1}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            images = response.json()
            return images[0]['urls']['regular']
        else:
            logger.warning('Unsplash API error: %s %s', response.status_code, response.text)
            return PLACEHOLDER
    except Exception as e:
        logger.error('Failed to fetch image for query "%s": %s', query, e)
        return PLACEHOLDER


def get_images(query: str, count: int = 10) -> list[str]:
    """Fetch multiple image URLs from Unsplash for a given query."""
    try:
        params = {'query': query, 'count': count}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            images = response.json()
            return [img['urls']['regular'] for img in images]
        else:
            logger.warning('Unsplash API error: %s %s', response.status_code, response.text)
            return [PLACEHOLDER]
    except Exception as e:
        logger.error('Failed to fetch images for query "%s": %s', query, e)
        return [PLACEHOLDER]


def get_placeholder() -> str:
    """Return the placeholder image URL."""
    return PLACEHOLDER


def html_regenerate_broken_img(html: str, project_id: int) -> str:
    """Regenerate broken images in HTML using OpenAI's image API."""
    try:
        openai.api_key = settings.OPENAI_IMG_KEY
        soup = BeautifulSoup(html, 'html.parser')

        img_tags = soup.find_all('img')
        images: list[dict[str, str]] = []
        for img in img_tags:
            src = img.get('src')
            if src:
                alt_text = img.get('alt', '').strip()
                images.append({'url': src, 'alt': alt_text})

        broken_images: list[dict[str, str]] = []
        for img in images:
            try:
                r = requests.head(img['url'], allow_redirects=True, timeout=5)
                if r.status_code == 404:
                    broken_images.append(img)
            except requests.RequestException:
                broken_images.append(img)

        for img in broken_images:
            prompt = img['alt']
            try:
                response = openai.Image.create(
                    prompt=prompt,
                    n=1,
                    size='1024x1024',
                )
                image_url = response['data'][0]['url']

                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    img_content = image_response.content

                    parsed_url = urlparse(image_url)
                    filename = os.path.basename(parsed_url.path)
                    if not filename:
                        filename = f'{prompt.replace(" ", "_")}.png'

                    image_obj = RegeneratedImage(prompt=prompt, project_id=project_id)
                    image_obj.image.save(filename, ContentFile(img_content))
                    image_obj.save()

                    db_image_url = image_obj.image.url
                    html = html.replace(img['url'], db_image_url)
                    logger.info('Replaced broken image: alt="%s" -> %s', prompt, db_image_url)

            except Exception as e:
                logger.error('Failed to regenerate image for "%s": %s', prompt, e)

        return html

    except Exception as e:
        logger.error('Image regeneration exception: %s', e)
        return html