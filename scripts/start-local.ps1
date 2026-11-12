$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Create .venv and install requirements.lock.txt first. See README.md.'
}
if (-not (Test-Path -LiteralPath '.env')) {
    throw 'Create .env first. See README.md.'
}
if (Test-Path -LiteralPath '.local\pgdata\PG_VERSION') {
    & '.local\postgres\pgsql\bin\pg_ctl.exe' -D '.local\pgdata' status | Out-Null
    if ($LASTEXITCODE -ne 0) {
        & '.local\postgres\pgsql\bin\pg_ctl.exe' -D '.local\pgdata' -l '.local\postgres.log' -w start
        if ($LASTEXITCODE -ne 0) { throw 'Cannot start local PostgreSQL. Check .local/postgres.log.' }
    }
}
& '.venv\Scripts\python.exe' manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
& '.venv\Scripts\python.exe' manage.py runserver 127.0.0.1:8000
