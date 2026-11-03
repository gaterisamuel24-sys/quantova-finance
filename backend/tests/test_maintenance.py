"""Housekeeping: expired refresh tokens are purged; live and revoked ones are kept."""

import asyncio
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.cli import parse_args
from app.core.config import Settings
from app.db.session import create_engine, create_sessionmaker
from app.main import create_app
from app.services.maintenance import purge_expired_refresh_tokens
from tests.helpers import create_user, run_query
from tests.test_analytics_api import execute_sql


def test_cli_accepts_only_known_commands() -> None:
    assert parse_args(["purge-expired-tokens"]).command == "purge-expired-tokens"
    with pytest.raises(SystemExit):
        parse_args(["drop-everything"])


@pytest.fixture
def client(integration_settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    with TestClient(create_app(integration_settings)) as test_client:
        yield test_client


def token_count(database_url: str, user_id: uuid.UUID) -> int:
    rows = run_query(
        database_url,
        "SELECT count(*) AS n FROM refresh_tokens WHERE user_id = :user_id",
        user_id=user_id,
    )
    return int(rows[0]["n"])


def set_expiry(database_url: str, user_id: uuid.UUID, ago: timedelta) -> None:
    execute_sql(
        database_url,
        "UPDATE refresh_tokens SET expires_at = :expires_at WHERE user_id = :user_id",
        expires_at=datetime.now(UTC) - ago,
        user_id=user_id,
    )


def purge(settings: Settings) -> int:
    async def _run() -> int:
        engine = create_engine(settings)
        try:
            async with create_sessionmaker(engine)() as session:
                return await purge_expired_refresh_tokens(session, now=datetime.now(UTC))
        finally:
            await engine.dispose()

    return asyncio.run(_run())


@pytest.mark.integration
def test_purges_only_tokens_expired_beyond_the_grace_period(
    client: TestClient, integration_settings: Settings, migrated_database: str
) -> None:
    long_expired, recently_expired, active = (create_user(client) for _ in range(3))
    set_expiry(migrated_database, long_expired.user_id, timedelta(days=30))
    set_expiry(migrated_database, recently_expired.user_id, timedelta(days=1))  # within grace

    deleted = purge(integration_settings)

    assert deleted >= 1  # other tests may have left expired tokens too
    assert token_count(migrated_database, long_expired.user_id) == 0
    assert token_count(migrated_database, recently_expired.user_id) == 1
    assert token_count(migrated_database, active.user_id) == 1
    audit = run_query(
        migrated_database,
        "SELECT count(*) AS n FROM audit_logs WHERE action = 'maintenance.refresh_tokens_purged'",
    )
    assert int(audit[0]["n"]) >= 1
