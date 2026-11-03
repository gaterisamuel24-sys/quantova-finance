"""Command-line entry point for maintenance jobs.

Usage (from the backend folder):

    uv run python -m app.cli purge-expired-tokens

It reads the same settings as the API (environment variables and backend/.env).
"""

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.config import get_settings
from app.db.session import create_engine, create_sessionmaker
from app.services.maintenance import purge_expired_refresh_tokens

COMMANDS = ("purge-expired-tokens",)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli", description="Quantova Finance maintenance jobs."
    )
    parser.add_argument("command", choices=COMMANDS, help="the job to run")
    return parser.parse_args(argv)


async def run(command: str) -> int:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        async with create_sessionmaker(engine)() as session:
            if command == "purge-expired-tokens":
                deleted = await purge_expired_refresh_tokens(session, now=datetime.now(UTC))
                print(f"Deleted {deleted} expired refresh tokens.")
    finally:
        await engine.dispose()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    return asyncio.run(run(args.command))


if __name__ == "__main__":
    sys.exit(main())
