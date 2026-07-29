"""Repository for project data access."""

import logging
from typing import Optional

from django.db.models import Q

from .models import (
    City,
    CityPageVersions,
    County,
    Page,
    Project,
    ProjectPage,
    ProjectPageVersion,
    State,
    Template,
    TemplateSection,
)

logger = logging.getLogger(__name__)


class ProjectRepository:
    """Repository for Project model queries."""

    def get_by_id(self, project_id: int) -> Project:
        """Get a project by ID.

        Args:
            project_id: The project ID.

        Returns:
            The Project instance.
        """
        return Project.objects.get(id=project_id)

    def get_all(self) -> list[Project]:
        """Get all projects ordered by ID descending.

        Returns:
            List of Project instances.
        """
        return list(Project.objects.all().order_by('-id'))

    def get_with_pages(self, project_id: int) -> Project:
        """Get a project with its pages prefetched.

        Args:
            project_id: The project ID.

        Returns:
            The Project instance with prefetched pages.
        """
        return Project.objects.prefetch_related('pages').get(id=project_id)

    def get_with_states(self, project_id: int) -> Project:
        """Get a project with its states prefetched.

        Args:
            project_id: The project ID.

        Returns:
            The Project instance with prefetched states.
        """
        return Project.objects.prefetch_related('states').get(id=project_id)


class PageRepository:
    """Repository for Page model queries."""

    def get_by_id(self, page_id: int) -> Page:
        """Get a page by ID.

        Args:
            page_id: The page ID.

        Returns:
            The Page instance.
        """
        return Page.objects.get(id=page_id)

    def get_by_project_and_slug(
        self, project: Project, slug: str
    ) -> Optional[Page]:
        """Get a page by project and slug.

        Args:
            project: The Project instance.
            slug: The page slug.

        Returns:
            The Page instance or None.
        """
        return project.pages.filter(slug=slug).first()

    def get_by_city(self, city: City) -> list[Page]:
        """Get all pages for a city.

        Args:
            city: The City instance.

        Returns:
            List of Page instances.
        """
        return list(Page.objects.filter(city=city))

    def get_by_template(self, template_id: int):
        """Get template sections for a template.

        Args:
            template_id: The template ID.

        Returns:
            QuerySet of TemplateSection instances.
        """
        return TemplateSection.objects.filter(
            template_id=template_id
        ).select_related('section')


class CityRepository:
    """Repository for City model queries."""

    def get_by_id(self, city_id: int) -> City:
        """Get a city by ID.

        Args:
            city_id: The city ID.

        Returns:
            The City instance.
        """
        return City.objects.get(id=city_id)

    def get_by_county(self, county: County) -> list[City]:
        """Get all cities for a county.

        Args:
            county: The County instance.

        Returns:
            List of City instances.
        """
        return list(county.cities.all())

    def get_by_state(self, state: State) -> list[City]:
        """Get all cities for a state.

        Args:
            state: The State instance.

        Returns:
            List of City instances.
        """
        return list(
            City.objects.filter(county__state=state).select_related(
                'county__state__project'
            )
        )

    def get_by_project(self, project: Project):
        """Get all cities for a project.

        Args:
            project: The Project instance.

        Returns:
            QuerySet of City instances.
        """
        return City.objects.filter(county__state__project=project)