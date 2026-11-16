<#
  Importiert eine erzeugte Monlist-Datei (out\monlist\monlist_<yyyy>_<mm>.txt) mit Monlist2.exe -
  derselbe Aufruf, den MONI.exe beim "Monlist Daten-Import" verwendet.
  ACHTUNG: Der Import ersetzt den GESAMTEN Monat in Monlist.
  Aufruf:  powershell -ExecutionPolicy Bypass -File import-monlist.ps1 -Monat 2026-05
  Login wird abgefragt und nicht gespeichert.
#>
param([Parameter(Mandatory=$true)][string]$Monat)
$ErrorActionPreference = 'Stop'
$settings = Get-Content (Join-Path (Split-Path $PSScriptRoot) 'settings.json') -Raw | ConvertFrom-Json
$exe = $settings.MainSettings.MonlistExecutablePath
$y, $m = $Monat.Split('-'); $m = [int]$m
$file = Join-Path $PSScriptRoot ('out\monlist\monlist_{0}_{1:D2}.txt' -f $y, $m)
if (-not (Test-Path $file)) { throw "Datei fehlt: $file  (zuerst: python3 monlist_txt.py $Monat)" }
if (-not (Test-Path $exe)) { throw "Monlist2.exe nicht erreichbar: $exe (VPN/Netzlaufwerk?)" }
$lines = (Get-Content $file | Select-Object -Skip 2).Count
Write-Host "Datei: $file  ($lines Zeilen)"
Write-Host "Der gesamte Monat $Monat wird in Monlist ERSETZT." -ForegroundColor Yellow
if ((Read-Host 'Fortfahren? (ja/nein)') -ne 'ja') { Write-Host 'Abgebrochen.'; exit }
$cred = Get-Credential -Message 'Monlist Login'
$pw = $cred.GetNetworkCredential().Password
& $exe "--user=$($cred.UserName)" "--pw=$pw" "--monat=$m" "--jahr=$y" "--file=$file"
Write-Host "Monlist2 beendet mit Code $LASTEXITCODE"
