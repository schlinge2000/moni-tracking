# Dashboard

`index.html` ist die Seite des Claude-Dashboards „Arbeitszeiten Christian“
(https://claude.ai/artifact/2sJiej193xCquHhk6SGzMG), Typ *Data*.

- Datenquelle: Datensatz `zeiten` = `out/dashboard_data.csv` (erzeugt von `dashboard_data.py`),
  vom täglichen Claude-Lauf als Datei hochgeladen.
- Berechnungen (`dash.calc`): `weekly`, `daily`, `kpi`, `woche`, `monthly`, `kunden`.
- Die Seite läuft nur innerhalb des Dashboard-Typs (`dash`, `d3` werden von dort bereitgestellt).
