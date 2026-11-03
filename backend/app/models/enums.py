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


_ORG_ROLE_RANK = {
    OrgRole.VIEWER: 1,
    OrgRole.ANALYST: 2,
    OrgRole.ADMIN: 3,
    OrgRole.OWNER: 4,
}


def org_role_at_least(role: OrgRole, minimum: OrgRole) -> bool:
    """True if `role` grants at least the permissions of `minimum`."""
    return _ORG_ROLE_RANK[role] >= _ORG_ROLE_RANK[minimum]


class AccountType(StrEnum):
    """Where money is held."""

    BANK = "bank"
    CASH = "cash"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    OTHER = "other"


class EntryKind(StrEnum):
    """Direction of money. Shared by categories and transactions so the two must agree."""

    INCOME = "income"
    EXPENSE = "expense"
