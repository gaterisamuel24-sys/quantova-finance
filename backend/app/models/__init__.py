"""Import every model so it registers on Base.metadata (Alembic relies on this)."""

from app.models.ai_insight import AIInsight
from app.models.audit_log import AuditLog
from app.models.billing_event import BillingEvent
from app.models.category import Category
from app.models.enums import AccountType, EntryKind, OrgRole, PlatformRole
from app.models.financial_account import FinancialAccount
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.subscription import Subscription
from app.models.transaction import Transaction
from app.models.user import User

__all__ = [
    "AIInsight",
    "AccountType",
    "AuditLog",
    "BillingEvent",
    "Category",
    "EntryKind",
    "FinancialAccount",
    "Membership",
    "OrgRole",
    "Organization",
    "PlatformRole",
    "RefreshToken",
    "Subscription",
    "Transaction",
    "User",
]
