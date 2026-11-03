"""The OpenAPI exporter works without services and describes the real API."""

import json
from pathlib import Path

from app.openapi_export import build_schema, main


def test_schema_describes_the_api() -> None:
    schema = build_schema()

    assert schema["info"]["title"] == "Quantova Finance API"
    for path in ("/api/v1/auth/login", "/api/v1/orgs", "/api/v1/orgs/{org_id}/members"):
        assert path in schema["paths"]


def test_main_writes_a_stable_json_file(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    assert main(["openapi_export", str(output)]) == 0
    first = output.read_text(encoding="utf-8")
    assert main(["openapi_export", str(output)]) == 0

    assert json.loads(first)["openapi"].startswith("3.")
    assert output.read_text(encoding="utf-8") == first  # identical output on every run
