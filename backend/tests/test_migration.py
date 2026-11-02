"""Migration integrity: models and migrations agree, and migrations reverse cleanly."""

import pytest
from alembic import command

from tests.conftest import make_alembic_config

pytestmark = pytest.mark.integration


def test_models_and_migrations_are_in_sync(migrated_database: str) -> None:
    # Fails if a model was changed without generating a matching migration.
    command.check(make_alembic_config(migrated_database))


def test_migrations_downgrade_and_upgrade_cleanly(migrated_database: str) -> None:
    config = make_alembic_config(migrated_database)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
