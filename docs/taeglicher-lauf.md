# Täglicher Claude-Lauf (geplante Aufgabe)

Name: „Tägliches Zeittracking (MONI + Odoo)“ – Mo–Fr 14:22 (Europe/Berlin), benötigt den verknüpften Rechner.
Davor: Windows-Aufgabe „MONI Kalender-Export“ Mo–Fr 14:00 (`register-task.ps1`).

Ablauf:
1. Prüfen, ob `calendar/KW<ww>_<jjjj>.csv` von heute existiert.
2. `build_week.py` → `out/KW.._moni.md`, `_odoo.csv`, `_review.md` (Woche bis heute).
3. Beschreibungen der Odoo-Restzeit aus Wiki-Signalen verbessern (nur Spalte `name`).
4. `dashboard_data.py` → `out/dashboard_data.csv` hochladen und Datensatz `zeiten` im Dashboard umstellen.
5. Nichts automatisch nach MONI/Daten oder Odoo schreiben.
6. Zusammenfassung an Christian; freitags Wochensumme + Erinnerung zur Übernahme.

Übernahme (manuell nach Prüfung):
- MONI: `uv run export_moni.py --dry-run`, dann `uv run export_moni.py` (Ziel in `config.json`)
- Monlist: in MONI „Monlist Daten-Import“ oder `monlist_txt.py` + `import-monlist.ps1`
- Odoo: Zeiterfassung → Import → `out/KW.._odoo.csv`
