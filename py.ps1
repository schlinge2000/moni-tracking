<#
  Fuehrt die Python-Skripte im uv-Environment aus (Python wird von uv selbst installiert).
  Das venv liegt NICHT im OneDrive-Ordner, sondern unter %LOCALAPPDATA%\moni-tracking\.venv.
  Beispiele:
    .\py.ps1 monlist_txt.py 2026-04 2026-11
    .\py.ps1 build_week.py --week 2026-W46
    .\py.ps1 dashboard_data.py
#>
$ErrorActionPreference = 'Stop'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  $uvLocal = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
  if (Test-Path $uvLocal) { $env:Path = (Split-Path $uvLocal) + ';' + $env:Path }
  else { throw 'uv nicht gefunden. Installieren:  winget install --id=astral-sh.uv -e   (oder: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex")' }
}
$env:UV_PROJECT_ENVIRONMENT = Join-Path $env:LOCALAPPDATA 'moni-tracking\.venv'
$env:PYTHONUTF8 = '1'
Push-Location $PSScriptRoot
try { uv run --project $PSScriptRoot python @args } finally { Pop-Location }
