<#
  Exportiert die Termine einer Kalenderwoche aus Outlook (klassisches Outlook, COM) nach
  tracking\calendar\KW<ww>_<yyyy>.csv  (Semikolon-getrennt, UTF-8).
  Aufruf:  powershell -ExecutionPolicy Bypass -File export-outlook.ps1 [-WeekStart 2026-11-09]
  Ohne Parameter: aktuelle Woche (Montag bis Sonntag).
  -NoAttendees: Teilnehmer nicht auslesen (schneller, keine Outlook-Sicherheitsabfrage; Kunden dann nur ueber Betreff/Ort).
  Nachpflege:  export-outlook.ps1 -From 2026-04-13 [-To 2026-11-13]  (eine CSV pro Woche)
  Es werden keine E-Mail-Adressen exportiert, nur die externen Domains der Teilnehmer.
#>
param([string]$WeekStart, [string]$From, [string]$To, [switch]$NoAttendees)
$ErrorActionPreference = 'Stop'
$internal = @('inform-software.com','inform-software.de','inform-ac.com')

function Monday([datetime]$d) { $d = $d.Date; return $d.AddDays(-(([int]$d.DayOfWeek + 6) % 7)) }
# Wochenliste: -From/-To (Nachpflege mehrerer Wochen), -WeekStart (eine Woche) oder aktuelle Woche
if ($From) {
  $first = Monday ([datetime]::Parse($From))
  $last  = if ($To) { Monday ([datetime]::Parse($To)) } else { Monday (Get-Date) }
  $weeks = @(); for ($w = $first; $w -le $last; $w = $w.AddDays(7)) { $weeks += $w }
} elseif ($WeekStart) { $weeks = @(Monday ([datetime]::Parse($WeekStart))) }
else { $weeks = @(Monday (Get-Date)) }

$outDir = Join-Path $PSScriptRoot 'calendar'
New-Item -ItemType Directory -Force $outDir | Out-Null

Write-Host "Verbinde mit Outlook ..."
$ol = $null
try { $ol = [Runtime.InteropServices.Marshal]::GetActiveObject('Outlook.Application') } catch {}
if (-not $ol) {
  try { $ol = New-Object -ComObject Outlook.Application }
  catch {
    Write-Host ""
    Write-Host "Keine Verbindung zu Outlook (COM)." -ForegroundColor Red
    Write-Host " - Laeuft das klassische Outlook (OUTLOOK.EXE)? Das neue Outlook (olk.exe) hat keine COM-Schnittstelle."
    Write-Host " - PowerShell und Outlook muessen mit derselben Berechtigung laufen (beide normal, nicht 'Als Administrator')."
    Write-Host " - Haengende OUTLOOK.EXE-Prozesse im Task-Manager beenden, Outlook normal starten, erneut versuchen."
    throw
  }
}
$ns = $ol.GetNamespace('MAPI')
$folder = $ns.GetDefaultFolder(9)          # olFolderCalendar
Write-Host "Kalender geoeffnet: $($folder.FolderPath)"
function Get-Domain($r) {
  try {
    $addr = $r.Address
    if ($addr -notmatch '@') {   # Exchange-intern (/o=...): SMTP direkt lesen, ohne langsamen GAL-Lookup
      $addr = $r.PropertyAccessor.GetProperty('http://schemas.microsoft.com/mapi/proptag/0x39FE001E')
    }
    if ($addr -match '@(.+)$') { return $Matches[1].ToLower() }
  } catch {}
  return $null
}

foreach ($ws in $weeks) {
$we = $ws.AddDays(7)
$thu = $ws.AddDays(3)                       # ISO-Woche (Windows PowerShell 5.1 kennt ISOWeek nicht)
$kw  = [int]([math]::Floor(($thu.DayOfYear - 1) / 7) + 1)
$yr  = $thu.Year
$outFile = Join-Path $outDir ('KW{0:D2}_{1}.csv' -f $kw, $yr)
$items = $folder.Items
$items.Sort('[Start]')
$items.IncludeRecurrences = $true
$filter = "[Start] < '" + $we.ToString('g') + "' AND [End] > '" + $ws.ToString('g') + "'"
$sel = $items.Restrict($filter)

$rows = @()
Write-Host ("KW{0:D2}/{1}: lese Termine ..." -f $kw, $yr)
$n = 0
foreach ($a in $sel) {
  $n++; if ($n % 10 -eq 0) { Write-Host "  $n Termine gelesen" }
  if ($a.Start -ge $we -or $a.End -le $ws) { continue }
  if ($a.MeetingStatus -eq 5 -or $a.MeetingStatus -eq 7) { continue }   # abgesagt
  if ($a.ResponseStatus -eq 4) { continue }                               # abgelehnt
  $domains = @()
  if (-not $NoAttendees -and $a.Recipients.Count -le 50) { foreach ($r in $a.Recipients) { $dm = Get-Domain $r; if ($dm -and ($internal -notcontains $dm)) { $domains += $dm } } }
  $rows += [pscustomobject]@{
    Start      = $a.Start.ToString('yyyy-MM-dd HH:mm')
    End        = $a.End.ToString('yyyy-MM-dd HH:mm')
    AllDay     = [bool]$a.AllDayEvent
    Busy       = $a.BusyStatus        # 0 frei, 1 mit Vorbehalt, 2 gebucht, 3 abwesend, 4 woanders
    Subject    = $a.Subject
    Location   = $a.Location
    Categories = $a.Categories
    ExtDomains = (($domains | Sort-Object -Unique) -join ',')
    Organizer  = $a.Organizer
  }
}
$rows | Export-Csv -Path $outFile -Delimiter ';' -NoTypeInformation -Encoding UTF8
Write-Host "Exportiert: $($rows.Count) Termine -> $outFile"
}
