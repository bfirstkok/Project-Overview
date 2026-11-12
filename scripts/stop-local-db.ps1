$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
& '.local\postgres\pgsql\bin\pg_ctl.exe' -D '.local\pgdata' -m fast -w stop
