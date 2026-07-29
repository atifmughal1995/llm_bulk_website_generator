"""Enums and constants for section types and project configuration."""

from enum import Enum


class SectionType(str, Enum):
    """Section type identifiers used in template rendering."""

    GALLERY = "gallery"
    TESTIMONIAL = "testimonial"
    CUSTOMER = "customer"
    RELATED_ZIP_CODES = "Related Zip Codes"


class PageType(str, Enum):
    """Project page type identifiers."""

    HOMEPAGE = "homepage"
    SERVICE = "service"
    OTHER = "other"


class CityStatus(str, Enum):
    """City processing status values."""

    QUEUED = "queued"
    COMPLETED = "completed"


class ProjectStatus(str, Enum):
    """Project status values."""

    IN_PROGRESS = "In progress"
    CREATED = "Created"


class AIProvider(str, Enum):
    """AI provider identifiers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"