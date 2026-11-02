"""Enumerations shared by models, schemas and authorization logic."""

from enum import StrEnum


class PlatformRole(StrEnum):
    """Platform-wide role. Superadmins operate the SaaS itself (support, admin pages)."""

    USER = "user"
    SUPERADMIN = "superadmin"


class OrgRole(StrEnum):
    """Role within one organization, from most to least privileged."""

    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
