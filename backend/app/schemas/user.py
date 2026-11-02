"""Public representation of a user. Deliberately excludes password_hash and internal flags."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import PlatformRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_email_verified: bool
    platform_role: PlatformRole
    created_at: datetime
