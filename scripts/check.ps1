#Requires -Version 7
<#
.SYNOPSIS
    Runs every quality check locally, mirroring the CI pipeline.
.EXAMPLE
    ./scripts/check.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root "backend/.venv/Scripts/python.exe"
$script:failed = @()

function Invoke-Check([string]$Name, [string]$Dir, [scriptblock]$Command) {
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    Push-Location (Join-Path $root $Dir)
    try {
        & $Command
        if ($LASTEXITCODE -ne 0) { throw "exit code $LASTEXITCODE" }
        Write-Host "[PASS] $Name" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] $Name ($_)" -ForegroundColor Red
        $script:failed += $Name
    } finally {
        Pop-Location
    }
}

if (-not (Test-Path $py)) {
    Write-Host "Backend venv not found at $py. See README > First-time setup." -ForegroundColor Red
    exit 1
}

# Infrastructure
Invoke-Check "Docker services healthy" "infra" {
    $lines = docker compose ps --format "{{.Service}}={{.Health}}"
    $unhealthy = $lines | Where-Object { $_ -notmatch "=healthy$" }
    if (-not $lines -or $unhealthy) { throw "not healthy: $($unhealthy -join ', ')" }
}

# Backend
Invoke-Check "Backend: Ruff lint"      "backend" { & $py -m ruff check . }
Invoke-Check "Backend: Ruff format"    "backend" { & $py -m ruff format --check . }
Invoke-Check "Backend: mypy"           "backend" { & $py -m mypy }
Invoke-Check "Backend: tests"          "backend" { & $py -m pytest -q }

# Frontend
Invoke-Check "Frontend: Prettier"      "frontend" { npm run --silent format:check }
Invoke-Check "Frontend: ESLint"        "frontend" { npm run --silent lint }
Invoke-Check "Frontend: tests"         "frontend" { npm run --silent test }
Invoke-Check "Frontend: build"         "frontend" { npm run --silent build }

# Repository hygiene
Invoke-Check "Pre-commit hooks"        "." { & $py -m pre_commit run --all-files }

Write-Host ""
if ($script:failed.Count -gt 0) {
    Write-Host "FAILED: $($script:failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "All checks passed." -ForegroundColor Green
