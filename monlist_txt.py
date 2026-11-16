#!/usr/bin/env python3
"""
MONI-Zeilen -> Monlist-Importdatei (monlist_<yyyy>_<mm>.txt), im selben Format, das MONI.exe erzeugt.

  python3 monlist_txt.py 2026-05            # ein Monat
  python3 monlist_txt.py 2026-04 2026-11    # Bereich

Quelle je Monat: Daten/<yyyy>_<mm>.md (falls vorhanden) plus fehlende Tage aus out/KW*_moni.md.
Ziel: tracking/out/monlist/monlist_<yyyy>_<mm>.txt (cp1252, CRLF). Pause 12:00-12:30 wie in MONI.
Die Datei ersetzt beim Import den GANZEN Monat in Monlist - deshalb enthaelt sie alle Tage des Monats.
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
st = json.load(open(os.path.join(ROOT, "settings.json"), encoding="utf-8-sig"))
P = st["ParserSettings"]
SHORT = {s["Key"]: s["Expansion"] for s in P["ShortCuts"]}
BREAK = P["DayBreakTime"]["Hour"] + P["DayBreakTime"]["Minute"] / 60 if P.get("InsertDayBreak", True) else None
BREAK_LEN = P.get("DayBreakDurationInMinutes", 30) / 60

def split_items(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(": depth += 1
        if ch == ")": depth = max(0, depth - 1)
        if ch == "," and depth == 0: out.append(cur); cur = ""
        else: cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]

def parse_code(code):
    """'pm ( Kommentar )' | '10030-0000(Urlaub)' -> (prj, pos, text)"""
    m = re.match(r"^([A-Za-z]\w*)\s*(?:\((.*)\))?\s*$", code)
    if m:
        if m.group(1) not in SHORT: raise ValueError(f"unbekanntes Kuerzel '{m.group(1)}'")
        prj, pos, txt = parse_code(SHORT[m.group(1)])
        return prj, pos, (" " + m.group(2).strip() + " ") if m.group(2) and m.group(2).strip() else txt
    m = re.match(r"^(\d{5})-(\d+)\s*\((.*)\)\s*$", code) or re.match(r"^(\d{5})-(\d+)()\s*$", code)
    if not m: raise ValueError(f"nicht lesbar: '{code}'")
    return m.group(1), m.group(2), m.group(3)

def parse_line(line):
    head, body = line.strip().split("|", 1)
    y, mo, d = map(int, head.split(","))
    items = split_items(body)
    t = float(items[0].split(",")[0]) if ";" not in items[0] else None
    if t is None: raise ValueError("Startzeit fehlt")
    rows = []
    for it in items[1:]:
        h, code = it.split(";", 1)
        rows.append((float(h), *parse_code(code.strip())))
    return (y, mo, d), t, rows

def hhmm(x):
    mins = int(round(x * 60)); return f"{mins // 60:02d}{mins % 60:02d}"

def day_rows(day, start, segs):
    out, t = [], start
    for h, prj, pos, txt in segs:
        rest = h
        while rest > 1e-9:
            if BREAK is not None and BREAK <= t < BREAK + BREAK_LEN: t = BREAK + BREAK_LEN
            end = t + rest
            if BREAK is not None and t < BREAK < end:
                end = BREAK
            out.append((day, t, end, prj, pos, txt)); rest -= end - t; t = end
    return out

def month_lines(y, mo):
    days = {}
    md = os.path.join(ROOT, "Daten", f"{y}_{mo:02d}.md")
    if os.path.exists(md):
        for ln in open(md, encoding="utf-8-sig"):
            if re.match(r"^\d{4},\d{1,2},\d{1,2}\|", ln): days[tuple(map(int, ln.split("|")[0].split(",")))] = (ln, "Daten")
    for f in sorted(glob.glob(os.path.join(HERE, "out", "KW*_moni.md"))):
        for ln in open(f, encoding="utf-8"):
            if re.match(rf"^{y},{mo},\d{{1,2}}\|", ln):
                k = tuple(map(int, ln.split("|")[0].split(",")))
                days.setdefault(k, (ln, "Vorschlag"))
    return [days[k] for k in sorted(days)]

def write_month(y, mo):
    rows, src = [], {"Daten": 0, "Vorschlag": 0}
    for ln, s in month_lines(y, mo):
        (yy, mm, d), start, segs = parse_line(ln)
        rows += day_rows(d, start, segs); src[s] += 1
    if not rows: print(f"{y}-{mo:02d}: keine Daten"); return
    out = os.path.join(HERE, "out", "monlist"); os.makedirs(out, exist_ok=True)
    p = os.path.join(out, f"monlist_{y}_{mo:02d}.txt")
    lines = ["Tag     Von     Bis     Std.    Prj-Nr   Pos.     durchgefuehrte Arbeiten", "=" * 72]
    for d, a, b, prj, pos, txt in rows:
        lines.append(f" {d:02d}     {hhmm(a)}    {hhmm(b)}    {b - a:05.2f}   {prj}    {pos}      {txt or ''}")
    with open(p, "w", encoding="cp1252", errors="replace", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")
    print(f"{y}-{mo:02d}: {src['Daten']} Tage aus Daten, {src['Vorschlag']} Tage aus Vorschlaegen, {sum(b - a for _, a, b, *_ in rows):.1f} h -> {p}")

if __name__ == "__main__":
    a = sys.argv[1]; b = sys.argv[2] if len(sys.argv) > 2 else a
    y, m = map(int, a.split("-")); y2, m2 = map(int, b.split("-"))
    while (y, m) <= (y2, m2):
        write_month(y, m); m += 1
        if m > 12: y, m = y + 1, 1
