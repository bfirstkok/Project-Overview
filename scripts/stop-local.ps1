$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Test-Path -LiteralPath '.local\web.pid') {
    $taskWebPid = [int](Get-Content -LiteralPath '.local\web.pid')
    $taskWebProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $taskWebPid"
    $taskPythonPath = (Resolve-Path -LiteralPath '.venv\Scripts\python.exe').Path
    if ($taskWebProcess -and $taskWebProcess.ExecutablePath -eq $taskPythonPath -and $taskWebProcess.CommandLine -like '*manage.py*runserver*127.0.0.1:8000*') {
        Stop-Process -Id $taskWebPid
    }
}
if (Test-Path -LiteralPath '.local\pgdata\PG_VERSION') {
    & '.local\postgres\pgsql\bin\pg_ctl.exe' -D '.local\pgdata' status | Out-Null
    if ($LASTEXITCODE -eq 0) { & '.local\postgres\pgsql\bin\pg_ctl.exe' -D '.local\pgdata' -m fast -w stop }
}
