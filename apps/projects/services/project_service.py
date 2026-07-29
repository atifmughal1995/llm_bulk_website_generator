"""Service for project-related operations."""

import logging
from typing import Optional

from django.shortcuts import get_object_or_404

from .models import Project, ProjectPage, State, County, City, Page
from .exceptions import ProjectError
from .ai_service import AIService
from .enums import ProjectStatus

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for project-related operations."""

    def __init__(self, ai_service: Optional[AIService] = None) -> None:
        self._ai_service = ai_service or AIService()

    def get_project(self, project_id: int) -> Project:
        """Get a project by ID.

        Args:
            project_id: The project ID.

        Returns:
            The Project instance.

        Raises:
            ProjectError: If the project is not found.
        """
        project = get_object_or_404(Project, id=project_id)
        return project

    def get_project_pages(self, project: Project) -> list[ProjectPage]:
        """Get all pages for a project.

        Args:
            project: The Project instance.

        Returns:
            List of ProjectPage instances.
        """
        return list(project.pages.all())

    def get_project_states(self, project: Project) -> list[State]:
        """Get all states for a project.

        Args:
            project: The Project instance.

        Returns:
            List of State instances.
        """
        return list(project.states.all().distinct())

    def get_city_count(
        self, project: Project
    ) -> tuple[int, int]:
        """Get total and queued city counts for a project.

        Args:
            project: The Project instance.

        Returns:
            Tuple of (total_cities, queued_cities).
        """
        cities = City.objects.filter(county__state__project=project)
        total = cities.count()
        queued = cities.filter(status=City.Status.QUEUED).count()
        return total, queued

    def update_project_status(
        self, project: Project, status: str
    ) -> Project:
        """Update a project's status.

        Args:
            project: The Project instance.
            status: The new status.

        Returns:
            The updated Project instance.
        """
        project.status = status
        project.save()
        return project

    def delete_project(self, project_id: int) -> None:
        """Delete a project by ID.

        Args:
            project_id: The project ID.
        """
        project = get_object_or_404(Project, id=project_id)
        project.delete()
        logger.info('Project %s deleted', project_id)