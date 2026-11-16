# Wöchentliches Zeittracking (MONI + Odoo)

Ablauf täglich (Mo–Fr); die Dateien der laufenden Woche werden jeden Tag neu aufgebaut (bis heute):

1. **14:00 – Windows-Aufgabe "MONI Kalender-Export"** führt `export-outlook.ps1` aus und legt
   `calendar/KW<ww>_<yyyy>.csv` ab (Termine Mo–So, ohne abgesagte/abgelehnte, nur externe Domains statt Adressen).
2. **14:22 – Geplante Claude-Aufgabe** führt `build_week.py` aus, ergänzt Beschreibungen aus dem
   Knowledge-Wiki und schreibt nach `out/`:
   - `KW.._moni.md` – Zeilen im MONI-Format (Kürzel pm/mt/vt/cs bzw. `10030-0000(Urlaub)`)
   - `KW.._odoo.csv` – Odoo-Timesheet-Import (`date, project_id, task_id, name, unit_amount`)
   - `KW.._review.md` – Wochenübersicht mit Hinweisen zum Prüfen
3. **Du prüfst** die Review und
   - **MONI:** Zeilen in `Daten/<yyyy>_<mm>.md` übernehmen (oder `python3 build_week.py --week 2026-W46 --apply-moni`)
   - **Odoo:** Zeiterfassung → Favoriten → Datensätze importieren → `KW.._odoo.csv`

## Einmalige Einrichtung
- `powershell -ExecutionPolicy Bypass -File register-task.ps1` (legt die Windows-Aufgabe an)
- Test: `powershell -ExecutionPolicy Bypass -File export-outlook.ps1` → CSV in `calendar/` prüfen
- Benötigt das **klassische Outlook** (COM). Das „neue Outlook“ hat keine COM-Schnittstelle.

## Regeln (mapping.json)
- Kundentermin = Kunde im Betreff/Ort/Teilnehmer-Domain erkannt → `cs` (Bestandskunde) oder `vt` (Interessent)
- Externe Domain ohne Zuordnung → `vt` + Hinweis in der Review
- Team-Meetings (Daily, Jour fixe, Retro …) → `mt`; sonstige interne Termine und Restzeit → `pm`
- Ganztägig „Urlaub“/„krank“ → 10030 / 10020; NRW-Feiertage werden ausgelassen
- Tag: Start 6:00 (früher, wenn der erste Termin früher liegt), 8 h, Pause 12:00–12:30 (wie MONI), max. 10 h

## Offen / prüfen
- Odoo-Projektnamen in `mapping.json` (`odoo_project`, `odoo_task`) an die echten Namen in Odoo anpassen.
- MONI: halbe Stunden werden als `1.5` geschrieben – einmal prüfen, ob MONI das so parst.

## Python unter Windows (uv)
- Einmalig uv installieren: `winget install --id=astral-sh.uv -e`
- Skripte starten über `.\py.ps1 <skript> <argumente>`, z. B. `.\py.ps1 monlist_txt.py 2026-04 2026-11`
- uv lädt beim ersten Aufruf Python 3.12 selbst; das venv liegt unter `%LOCALAPPDATA%\moni-tracking\.venv` (nicht im OneDrive).
