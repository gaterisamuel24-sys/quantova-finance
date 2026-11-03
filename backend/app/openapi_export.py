"""Write the API's OpenAPI schema to a JSON file, without a database or a running server.

Usage (from backend/):
    uv run python -m app.openapi_export ../frontend/openapi.json
"""

import json
import secrets
import sys
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


def build_schema() -> dict[str, Any]:
    """Build the schema from code. Nothing connects: the app's lifespan never runs."""
    settings = Settings(
        _env_file=None,
        environment="development",
        database_url=SecretStr("postgresql+asyncpg://unused:unused@127.0.0.1:5432/unused"),
        redis_url=SecretStr("redis://127.0.0.1:6379/0"),
        jwt_secret_key=SecretStr(secrets.token_hex(32)),
    )
    return create_app(settings).openapi()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: python -m app.openapi_export <output.json>\n")
        return 2
    output = Path(argv[1])
    output.write_text(json.dumps(build_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(f"OpenAPI schema written to {output}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
