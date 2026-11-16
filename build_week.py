#!/usr/bin/env python3
"""
Wochen-Zeittracking: Outlook-Export + Knowledge-Wiki -> MONI-Zeilen, Odoo-Import-CSV, Review.

  python3 build_week.py [--week 2026-W46] [--wiki PATH] [--apply-moni]

Erwartet tracking/calendar/KW<ww>_<yyyy>.csv (von export-outlook.ps1).
Schreibt tracking/out/KW<ww>_<yyyy>_moni.md, _odoo.csv, _review.md.
--apply-moni haengt die Zeilen an Daten/<yyyy>_<mm>.md an (nur Tage, die dort noch fehlen).
"""
import argparse, csv, datetime as dt, json, os, re, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
MONI_ROOT = os.path.dirname(HERE)


# ---------- Hilfen ----------
def easter(y):
    a = y % 19; b = y // 100; c = y % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451; mon = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(y, mon, day)

def holidays_nrw(y):
    e = easter(y); D = dt.timedelta
    return {dt.date(y,1,1):"Neujahr", e-D(2):"Karfreitag", e+D(1):"Ostermontag", dt.date(y,5,1):"Tag der Arbeit",
            e+D(39):"Christi Himmelfahrt", e+D(50):"Pfingstmontag", e+D(60):"Fronleichnam",
            dt.date(y,10,3):"Tag der Deutschen Einheit", dt.date(y,11,1):"Allerheiligen",
            dt.date(y,12,25):"1. Weihnachtstag", dt.date(y,12,26):"2. Weihnachtstag"}

def hm(s):
    h, m = s.split(":"); return int(h) + int(m) / 60

def rnd(x, step):
    return round(x / step) * step

def fmt_h(x):
    return str(int(x)) if abs(x - round(x)) < 1e-9 else f"{x:.2f}".rstrip("0")

def clean(s, n=80):
    s = re.sub(r"[;,|()\[\]\r\n\t]+", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()[:n]

def matches_word(text, words):
    """Kundennamen nur als ganzes Wort (sonst trifft 'ktm' z.B. 'Produktmanagement')."""
    t = (text or "").lower()
    return next((w for w in words if re.search(r"(?<![a-z0-9äöüß])" + re.escape(w.lower()) + r"(?![a-z0-9äöüß])", t)), None)

def contains_any(text, words):
    t = (text or "").lower()
    return next((w for w in words if w.lower() in t), None)


# ---------- Eingaben ----------
def load_calendar(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))

def classify(ev, mp):
    subj = ev.get("Subject", ""); hay = " ".join([subj, ev.get("Location", ""), ev.get("Categories", "")])
    doms = [d for d in (ev.get("ExtDomains") or "").split(",") if d]
    if contains_any(subj, mp["ignore_subjects"]):
        return None
    for r in mp["subject_rules"]:
        if contains_any(subj, r["match"]):
            return dict(act=r["activity"], whole=r.get("whole_day", False), customer=None, desc=clean(subj), flag=None)
    for c in mp["customers"]:
        if matches_word(hay, c["match"]) or any(matches_word(d, c["match"]) for d in doms):
            return dict(act=c["activity"], whole=False, customer=c["name"], desc=clean(f"{c['name']}: {subj}"), flag=None)
    if doms:
        return dict(act=mp["unknown_external_activity"], whole=False, customer=doms[0],
                    desc=clean(f"Extern {doms[0]}: {subj}"), flag=f"Externer Termin ohne Kundenzuordnung ({', '.join(doms)})")
    if ev.get("Busy") in ("0",):   # frei markierte interne Termine ignorieren
        return None
    return dict(act=mp["default_activity"], whole=False, customer=None, desc=clean(f"Meeting: {subj}"), flag=None)

def wiki_mtimes(wdir, budget_s=60):
    """Aenderungsdatum aller Wiki-Seiten; 1 h im Home-Verzeichnis zwischengespeichert (OneDrive-Scan ist langsam)."""
    cache = os.path.expanduser("~/.wiki_mtimes_cache.json")
    try:
        if time.time() - os.path.getmtime(cache) < 3600:
            return json.load(open(cache, encoding="utf-8"))
    except OSError:
        pass
    res, t0 = defaultdict(list), time.time()
    for root, dirs, files in os.walk(wdir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if time.time() - t0 > budget_s: break
        for fn in files:
            if not fn.endswith(".md") or fn in ("log.md", "index.md"): continue
            try: d = dt.date.fromtimestamp(os.path.getmtime(os.path.join(root, fn))).isoformat()
            except OSError: continue
            res[d].append(fn[:-3])
    try: json.dump(res, open(cache, "w", encoding="utf-8"))
    except OSError: pass
    return res

def wiki_signals(wiki, days, budget_s=60):
    """Tag -> Liste von Themen aus log.md und an dem Tag geaenderten Wiki-Seiten."""
    sig = defaultdict(list)
    if not wiki or not os.path.isdir(wiki):
        return sig
    wdir = os.path.join(wiki, "wiki")
    dayset = set(days)
    log = os.path.join(wdir, "log.md")
    if os.path.exists(log):
        cur = None
        for line in open(log, encoding="utf-8-sig", errors="replace"):
            m = re.match(r"^## (\d{4}-\d{2}-\d{2})[^—-]*[—-]+\s*(.+)$", line.strip())
            if m:
                d = dt.date.fromisoformat(m.group(1)); cur = d if d in dayset else None
                if cur: sig[cur].append(m.group(2).strip())
            elif cur and line.startswith("Notiz:"):
                sig[cur][-1] += ": " + clean(line[6:], 120)
    lo, hi = min(days), max(days)
    for d, pages in wiki_mtimes(wdir, budget_s).items():
        d = dt.date.fromisoformat(d)
        if lo <= d <= hi: sig[d].extend("Wiki: " + p for p in pages)
    return sig


# ---------- Tagesaufbau ----------
def build_day(day, events, mp):
    cfg = mp["day"]; step = cfg["round_to_hours"]
    bstart = hm(cfg["break_start"]); blen = cfg["break_minutes"] / 60
    whole = [e for e in events if e["cls"]["whole"]]
    if whole:
        c = whole[0]["cls"]
        return dict(start=8, segs=[(cfg["hours_per_day"], c["act"], c["desc"])], flags=[])
    start = cfg["default_start_hour"]
    timed = sorted([e for e in events if e["s"].date() == day], key=lambda e: e["s"])
    if timed:
        first = timed[0]["s"].hour + timed[0]["s"].minute / 60
        start = min(start, int(first))

    def off(clock):  # Uhrzeit -> Arbeitsstunden ab Start (MONI fuegt die Pause selbst ein)
        x = clock - start
        if clock >= bstart + blen: x -= blen
        elif clock > bstart: x -= (clock - bstart)
        return max(0.0, x)

    blocks, flags = [], []
    for e in timed:
        a = rnd(off(e["s"].hour + e["s"].minute / 60), step)
        endc = e["e"].hour + e["e"].minute / 60 if e["e"].date() == day else 23.99
        b = rnd(off(endc), step)
        if blocks and a < blocks[-1][1]:
            a = blocks[-1][1]
        if b - a >= step:
            blocks.append([a, b, e["cls"]["act"], e["cls"]["desc"]])
        if e["cls"]["flag"]: flags.append(e["cls"]["flag"])
    total = cfg["hours_per_day"]
    if blocks and blocks[-1][1] > total:
        total = min(blocks[-1][1], cfg["max_hours_per_day"])
        flags.append(f"Termine reichen bis {fmt_h(blocks[-1][1])} h Arbeitszeit - auf {fmt_h(total)} h gesetzt, bitte pruefen")
    segs, pos = [], 0.0
    for a, b, act, desc in blocks:
        a, b = min(a, total), min(b, total)
        if a > pos: segs.append((a - pos, mp["default_activity"], None))
        if b > a: segs.append((b - a, act, desc))
        pos = max(pos, b)
    if pos < total: segs.append((total - pos, mp["default_activity"], None))
    merged = []
    for s in segs:
        if merged and merged[-1][1] == s[1] and merged[-1][2] == s[2]:
            merged[-1] = (merged[-1][0] + s[0], s[1], s[2])
        else: merged.append(s)
    return dict(start=start, segs=merged, flags=flags)


# ---------- Ausgaben ----------
def moni_line(day, d, mp, shortcuts):
    parts = []
    for h, act, desc in d["segs"]:
        a = mp["activities"][act]
        if act in shortcuts:
            parts.append(f"{fmt_h(h)};{act}" + (f" ( {desc} )" if desc else ""))
        else:
            parts.append(f"{fmt_h(h)};{a['moni']}({clean(desc or a['label'])})")
    return f"{day.year},{day.month},{day.day}|{fmt_h(d['start'])}," + ", ".join(parts)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", help="ISO-Woche, z.B. 2026-W46 (Default: aktuelle Woche)")
    _wiki_default = next((w for w in (os.path.expanduser("~/mnt/knowledge-wiki"), os.path.join(os.path.dirname(MONI_ROOT), "knowledge-wiki")) if os.path.isdir(w)), "")
    ap.add_argument("--wiki", default=_wiki_default)
    ap.add_argument("--apply-moni", action="store_true")
    ap.add_argument("--until", help="letzter Tag (YYYY-MM-DD), Default: heute - spaetere Tage werden nicht erzeugt")
    args = ap.parse_args()

    mp = json.load(open(os.path.join(HERE, "mapping.json"), encoding="utf-8"))
    try:
        st = json.load(open(os.path.join(MONI_ROOT, "settings.json"), encoding="utf-8-sig"))
        shortcuts = {s["Key"] for s in st["ParserSettings"]["ShortCuts"]}
    except Exception:
        shortcuts = set()

    if args.week:
        y, w = re.match(r"(\d{4})-?W(\d{1,2})", args.week).groups()
        monday = dt.date.fromisocalendar(int(y), int(w), 1)
    else:
        t = dt.date.today(); monday = t - dt.timedelta(days=t.weekday())
    iy, iw, _ = monday.isocalendar()
    tag = f"KW{iw:02d}_{iy}"
    until = dt.date.fromisoformat(args.until) if args.until else dt.date.today()
    days = [monday + dt.timedelta(days=i) for i in range(5) if monday + dt.timedelta(days=i) <= until]
    if not days:
        sys.exit("Keine Arbeitstage bis --until in dieser Woche.")
    hol = {**holidays_nrw(monday.year), **holidays_nrw(days[-1].year)}

    cal = load_calendar(os.path.join(HERE, "calendar", f"{tag}.csv"))
    global_flags = []
    if cal is None:
        global_flags.append(f"Kein Kalenderexport calendar/{tag}.csv gefunden - nur Standardtage erzeugt. export-outlook.ps1 ausfuehren.")
        cal = []
    events = defaultdict(list)
    for r in cal:
        try:
            s = dt.datetime.strptime(r["Start"], "%Y-%m-%d %H:%M"); e = dt.datetime.strptime(r["End"], "%Y-%m-%d %H:%M")
        except (KeyError, ValueError): continue
        cls = classify(r, mp)
        if not cls: continue
        allday = str(r.get("AllDay", "")).lower() == "true"
        if allday and not cls["whole"] and cls["customer"] is None:
            continue  # ganztaegige interne Hinweise (z.B. Geburtstage) ignorieren
        d = s.date()
        while d < e.date() or d == s.date():
            if d in days:
                ev = dict(s=s, e=e, cls=dict(cls))
                if allday and not cls["whole"]:
                    ev["cls"]["whole"] = True  # ganztaegiger Kundentermin, z.B. Vor-Ort-Tag
                events[d].append(ev)
            d += dt.timedelta(days=1)
            if allday and d >= e.date(): break

    sig = wiki_signals(args.wiki, days)
    result = {}
    for d in days:
        if d in hol:
            result[d] = None; continue
        result[d] = build_day(d, events[d], mp)

    out = os.path.join(HERE, "out"); os.makedirs(out, exist_ok=True)
    # MONI
    lines = [moni_line(d, r, mp, shortcuts) for d, r in result.items() if r]
    with open(os.path.join(out, f"{tag}_moni.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    # Odoo
    with open(os.path.join(out, f"{tag}_odoo.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["date", "project_id", "task_id", "name", "unit_amount"])
        for d, r in result.items():
            if not r: continue
            agg = defaultdict(float); order = []
            for h, act, desc in r["segs"]:
                if desc is None:
                    topics = "; ".join(dict.fromkeys(sig.get(d, [])))[:200]
                    desc = mp["activities"][act]["label"] + (f" - {topics}" if topics else "")
                k = (act, desc)
                if k not in agg: order.append(k)
                agg[k] += h
            for act, desc in order:
                a = mp["activities"][act]
                w.writerow([d.isoformat(), a["odoo_project"], a.get("odoo_task", ""), desc, f"{agg[(act, desc)]:.2f}"])
    # Review
    tot = defaultdict(float)
    rv = [f"# Zeittracking {tag} ({monday:%d.%m.} - {days[-1]:%d.%m.%Y}, Stand {dt.datetime.now():%d.%m. %H:%M})", ""]
    for g in global_flags: rv.append(f"> **Achtung:** {g}")
    rv += ["", "| Tag | Start | Std. | Buchungen | Hinweise |", "|---|---|---|---|---|"]
    for d, r in result.items():
        wd = ["Mo","Di","Mi","Do","Fr"][d.weekday()]
        if not r:
            rv.append(f"| {wd} {d:%d.%m.} | - | 0 | Feiertag: {hol[d]} | |"); continue
        book = "<br>".join(f"{fmt_h(h)} h {act}" + (f" - {desc}" if desc else "") for h, act, desc in r["segs"])
        for h, act, _ in r["segs"]: tot[act] += h
        fl = list(r["flags"])
        if not events[d] and not sig.get(d): fl.append("keine Signale - Standardtag angenommen")
        rv.append(f"| {wd} {d:%d.%m.} | {fmt_h(r['start'])}:00 | {fmt_h(sum(s[0] for s in r['segs']))} | {book} | {'<br>'.join(fl)} |")
    rv += ["", "## Summe je Taetigkeit", ""]
    for act, h in sorted(tot.items(), key=lambda x: -x[1]):
        rv.append(f"- {mp['activities'][act]['label']} ({mp['activities'][act]['moni']}): {fmt_h(h)} h")
    rv += ["", "## Wiki-Signale", ""]
    for d in days:
        if sig.get(d): rv.append(f"- {d:%a %d.%m.}: " + "; ".join(dict.fromkeys(sig[d]))[:400])
    rv += ["", "## MONI-Zeilen", "", "```", *lines, "```"]
    with open(os.path.join(out, f"{tag}_review.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(rv) + "\n")

    if args.apply_moni:
        for ln in lines:
            y, m, dd = map(int, ln.split("|")[0].split(","))
            p = os.path.join(MONI_ROOT, "Daten", f"{y}_{m:02d}.md")
            existing = open(p, encoding="utf-8-sig").read() if os.path.exists(p) else ""
            if re.search(rf"^{y},{m},{dd}\|", existing, re.M): continue
            with open(p, "a", encoding="utf-8") as f:
                f.write(("" if existing.endswith("\n") or not existing else "\n") + ln + "\n")
    print(f"{tag}: {len(cal)} Kalendereintraege, {sum(1 for r in result.values() if r)} Arbeitstage -> out/{tag}_*")

if __name__ == "__main__":
    main()
