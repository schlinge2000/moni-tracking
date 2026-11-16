<#
  Legt in der Windows-Aufgabenplanung den Job "MONI Kalender-Export" an:
  Mo-Fr 14:00 wird export-outlook.ps1 ausgefuehrt (nur wenn angemeldet, da Outlook-COM).
  Einmalig ausfuehren:  powershell -ExecutionPolicy Bypass -File register-task.ps1
#>
$script = Join-Path $PSScriptRoot 'export-outlook.ps1'
$action  = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 14:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName 'MONI Kalender-Export' -Action $action -Trigger $trigger -Settings $settings -Description 'Outlook-Wochenexport fuer Zeittracking (MONI/Odoo)' -Force
Write-Host 'Aufgabe angelegt. Test:  Start-ScheduledTask -TaskName "MONI Kalender-Export"'
