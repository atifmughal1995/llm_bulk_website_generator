"""Client for Netlify API operations."""

import logging
from typing import Optional

import requests
from django.conf import settings

from .exceptions import NetlifyAPIError

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.netlify.com/api/v1'


class NetlifyClient:
    """Client for interacting with the Netlify API."""

    def __init__(self, access_token: Optional[str] = None) -> None:
        self._access_token = access_token or settings.NETLIFY_ACCESS_KEY
        self._headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json',
        }

    def get_sites(self) -> list[dict]:
        """Fetch all Netlify sites."""
        response = requests.get(f'{BASE_URL}/sites', headers=self._headers)
        if response.status_code != 200:
            raise NetlifyAPIError(
                f'Failed to fetch sites: {response.status_code} {response.text}'
            )
        return response.json()

    def create_site(self, payload: dict) -> dict:
        """Create a new Netlify site."""
        response = requests.post(
            f'{BASE_URL}/sites', headers=self._headers, json=payload
        )
        if response.status_code not in (200, 201):
            raise NetlifyAPIError(
                f'Failed to create site: {response.status_code} {response.text}'
            )
        return response.json()

    def update_site(self, site_id: str, payload: dict) -> dict:
        """Update a Netlify site."""
        response = requests.patch(
            f'{BASE_URL}/sites/{site_id}', headers=self._headers, json=payload
        )
        if response.status_code != 200:
            raise NetlifyAPIError(
                f'Failed to update site: {response.status_code} {response.text}'
            )
        return response.json()

    def delete_site(self, site_id: str) -> None:
        """Delete a Netlify site."""
        response = requests.delete(
            f'{BASE_URL}/sites/{site_id}', headers=self._headers
        )
        if response.status_code != 204:
            raise NetlifyAPIError(
                f'Failed to delete site: {response.status_code} {response.text}'
            )

    def initiate_deploy(
        self, site_id: str, files_map: dict[str, str]
    ) -> dict:
        """Initiate a deployment for a site."""
        response = requests.post(
            f'{BASE_URL}/sites/{site_id}/deploys',
            headers=self._headers,
            json={'files': files_map},
        )
        if response.status_code not in (200, 201):
            raise NetlifyAPIError(
                f'Failed to initiate deploy: {response.status_code} {response.text}'
            )
        return response.json()

    def upload_deploy_file(
        self, site_id: str, deploy_id: str, relative_path: str, content: bytes
    ) -> None:
        """Upload a file to a deployment."""
        file_url = (
            f'{BASE_URL}/deploys/{deploy_id}/files/{relative_path}'
        )
        response = requests.put(file_url, headers=self._headers, data=content)
        if response.status_code not in (200, 201):
            raise NetlifyAPIError(
                f'Failed to upload file {relative_path}: {response.status_code}'
            )