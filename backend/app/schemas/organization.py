"""Request and response bodies for organizations and memberships."""

import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models.enums import OrgRole
from app.schemas.auth import NormalizedEmail


def _uppercase(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


OrgName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CurrencyCode = Annotated[str, BeforeValidator(_uppercase), StringConstraints(pattern=r"^[A-Z]{3}$")]
FiscalMonth = Annotated[int, Field(ge=1, le=12)]


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: OrgName
    base_currency: CurrencyCode = "USD"
    fiscal_year_start_month: FiscalMonth = 1


class OrganizationUpdate(BaseModel):
    """Partial update: only fields present in the request are changed."""

    model_config = ConfigDict(extra="forbid")

    name: OrgName | None = None
    base_currency: CurrencyCode | None = None
    fiscal_year_start_month: FiscalMonth | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        # Omitting a field means "don't change it"; sending null is not allowed.
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    base_currency: str
    fiscal_year_start_month: int
    created_at: datetime
    my_role: OrgRole


class MemberAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail
    role: OrgRole


class MemberRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: OrgRole


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: OrgRole
    joined_at: datetime
