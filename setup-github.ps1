<#
  Legt aus diesem Ordner ein privates GitHub-Repo an und pusht den Stack.
  Kalenderexporte (calendar\) und erzeugte Dateien (out\) bleiben lokal (.gitignore).
  Mit GitHub CLI:   powershell -ExecutionPolicy Bypass -File setup-github.ps1
  Ohne GitHub CLI:  vorher auf github.com ein leeres privates Repo "moni-tracking" anlegen, dann
                    powershell -ExecutionPolicy Bypass -File setup-github.ps1 -Remote https://github.com/<user>/moni-tracking.git
#>
param([string]$Name = 'moni-tracking', [string]$Remote)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path .git)) { git init -b main | Out-Null }
git add -A
git commit -m "Zeittracking-Stack: Outlook-Export, Wochenaufbau, MONI/Monlist/Odoo-Export, Dashboard" 2>$null
if ($Remote) {
  git remote remove origin 2>$null
  git remote add origin $Remote
  git push -u origin main
} elseif (Get-Command gh -ErrorAction SilentlyContinue) {
  gh repo create $Name --private --source . --remote origin --push --description "Zeittracking: Outlook + Knowledge-Wiki -> MONI / Monlist / Odoo + Dashboard"
} else {
  throw 'GitHub CLI (gh) fehlt. Entweder "winget install --id GitHub.cli" oder Repo im Browser anlegen und -Remote angeben.'
}
git status -sb | Select-Object -First 1
