"""Service for Netlify deployment operations."""

import hashlib
import logging
import os
import shutil
from typing import Optional, tuple

import requests
from django.conf import settings

from .exceptions import DeploymentError, NetlifyAPIError

logger = logging.getLogger(__name__)


class NetlifyClient:
    """Client for interacting with the Netlify API."""

    BASE_URL = 'https://api.netlify.com/api/v1'

    def __init__(self, access_token: Optional[str] = None) -> None:
        self._access_token = access_token or settings.NETLIFY_ACCESS_KEY
        self._headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json',
        }

    def get_sites(self) -> list[dict]:
        """Fetch all Netlify sites."""
        response = requests.get(
            f'{self.BASE_URL}/sites', headers=self._headers
        )
        if response.status_code != 200:
            raise NetlifyAPIError(
                f'Failed to fetch sites: {response.status_code} {response.text}'
            )
        return response.json()

    def create_site(self, payload: dict) -> dict:
        """Create a new Netlify site."""
        response = requests.post(
            f'{self.BASE_URL}/sites', headers=self._headers, json=payload
        )
        if response.status_code not in (200, 201):
            raise NetlifyAPIError(
                f'Failed to create site: {response.status_code} {response.text}'
            )
        return response.json()

    def get_site(self, site_id: str) -> dict:
        """Fetch a Netlify site by ID."""
        response = requests.get(
            f'{self.BASE_URL}/sites/{site_id}', headers=self._headers
        )
        if response.status_code != 200:
            raise NetlifyAPIError(
                f'Failed to fetch site: {response.status_code} {response.text}'
            )
        return response.json()

    def update_site(self, site_id: str, payload: dict) -> dict:
        """Update a Netlify site."""
        response = requests.patch(
            f'{self.BASE_URL}/sites/{site_id}', headers=self._headers, json=payload
        )
        if response.status_code != 200:
            raise NetlifyAPIError(
                f'Failed to update site: {response.status_code} {response.text}'
            )
        return response.json()

    def delete_site(self, site_id: str) -> None:
        """Delete a Netlify site."""
        response = requests.delete(
            f'{self.BASE_URL}/sites/{site_id}', headers=self._headers
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
            f'{self.BASE_URL}/sites/{site_id}/deploys',
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
            f'{self.BASE_URL}/deploys/{deploy_id}/files/{relative_path}'
        )
        response = requests.put(file_url, headers=self._headers, data=content)
        if response.status_code not in (200, 201):
            raise NetlifyAPIError(
                f'Failed to upload file {relative_path}: {response.status_code}'
            )


class DeploymentService:
    """Service for building and deploying projects to Netlify."""

    def __init__(
        self,
        netlify_client: Optional[NetlifyClient] = None,
    ) -> None:
        self._netlify_client = netlify_client or NetlifyClient()

    def build_and_deploy(
        self,
        project: Any,
        output_dir: str,
    ) -> tuple[str, str]:
        """Build project files and deploy to Netlify.

        Args:
            project: The Project model instance.
            output_dir: The output directory for built files.

        Returns:
            Tuple of (site_id, site_url).
        """
        site_id, site_url = self._deploy_project(project, output_dir)
        return site_id, site_url

    def _deploy_project(
        self, project: Any, project_folder: str
    ) -> tuple[str, str]:
        """Deploy a project folder to Netlify."""
        payload = {
            'force_ssl': True,
            'processing_settings': {
                'html': {
                    'pretty_urls': True,
                }
            },
        }

        site_id: Optional[str] = None
        site_url: Optional[str] = None

        create_site_resp = self._netlify_client.create_site(payload)
        site_id = create_site_resp.get('site_id')
        site_url = create_site_resp.get('url')

        project.netlify_site_id = site_id
        project.netlify_site_url = site_url
        project.netlify_site_url_history = (
            ','.join([site_url] + str(project.netlify_site_url_history).split(','))
            if project.netlify_site_url_history
            else site_url
        )
        project.save()

        if not site_id:
            raise DeploymentError('Site not found.')

        file_paths, files_map = self._hash_files(project_folder)

        deploy_data = self._netlify_client.initiate_deploy(site_id, files_map)
        deploy_id = deploy_data.get('id')

        self._upload_files(site_id, deploy_id, file_paths)

        logger.info('Site deployed successfully: %s', site_url)
        return site_id, site_url

    def _hash_files(self, project_folder: str) -> tuple[list[tuple[str, str]], dict[str, str]]:
        """Hash all files in the project folder."""
        file_paths: list[tuple[str, str]] = []
        files_map: dict[str, str] = {}

        for root, _, files in os.walk(project_folder):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, project_folder).replace('\\', '/')
                file_paths.append((full_path, relative_path))
                with open(full_path, 'rb') as f:
                    content = f.read()
                    sha = hashlib.sha1(content).hexdigest()
                    files_map[relative_path] = sha

        return file_paths, files_map

    def _upload_files(
        self, site_id: str, deploy_id: str, file_paths: list[tuple[str, str]]
    ) -> None:
        """Upload files to a Netlify deployment."""
        for full_path, relative_path in file_paths:
            with open(full_path, 'rb') as f:
                file_url = (
                    f'https://api.netlify.com/api/v1/deploys/{deploy_id}/files/{relative_path}'
                )
                requests.put(file_url, headers=self._netlify_client._headers, data=f.read())