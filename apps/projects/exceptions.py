"""Custom exceptions for the projects app."""


class ProjectError(Exception):
    """Base exception for project-related errors."""


class DeploymentError(ProjectError):
    """Raised when a Netlify deployment fails."""


class AIContentError(ProjectError):
    """Raised when AI content generation fails."""


class PageBuildError(ProjectError):
    """Raised when project page building fails."""


class NetlifyAPIError(ProjectError):
    """Raised when a Netlify API call fails."""


class ExcelProcessingError(ProjectError):
    """Raised when Excel file processing fails."""