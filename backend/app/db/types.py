"""Reusable column types."""

from enum import StrEnum

from sqlalchemy import Enum


def str_enum_column_type(enum_cls: type[StrEnum], name: str) -> Enum:
    """Store a StrEnum as VARCHAR plus a CHECK constraint listing the allowed values.

    We deliberately avoid native PostgreSQL ENUM types: adding or renaming a value
    requires awkward migrations, while a CHECK constraint is just as strict and
    trivial to alter.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
