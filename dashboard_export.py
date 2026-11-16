"""Sammelt alle Wochen aus out/ in out/dashboard.csv (fuer das Zeittracking-Dashboard).
Liest out/KW*_odoo.csv + out/KW*_review.md, prueft calendar/ und MONI/Daten auf Uebernahme."""
import csv, glob, json, os, re, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
MONI_ROOT = os.path.dirname(HERE)
mp = json.load(open(os.path.join(HERE, "mapping.json"), encoding="utf-8"))
by_proj = {a["odoo_project"]: (k, a["label"]) for k, a in mp["activities"].items()}
customers = [c["name"] for c in mp["customers"]]
WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

def review_flags(path):
    flags, glob_flags = {}, []
    if not os.path.exists(path): return flags, glob_flags
    for ln in open(path, encoding="utf-8"):
        if ln.startswith("> **Achtung:**"): glob_flags.append(ln.split("**", 2)[2].strip())
        m = re.match(r"\| \w\w (\d\d)\.(\d\d)\. \|.*\|(.*)\|\s*$", ln)
        if m: flags[(int(m.group(2)), int(m.group(1)))] = [f.strip() for f in m.group(3).split("<br>") if f.strip()]
    return flags, glob_flags

def moni_days(y, m):
    p = os.path.join(MONI_ROOT, "Daten", f"{y}_{m:02d}.md")
    if not os.path.exists(p): return set()
    return {int(x) for x in re.findall(rf"^{y},{m},(\d+)\|", open(p, encoding="utf-8-sig").read(), re.M)}

rows = []
for f in sorted(glob.glob(os.path.join(HERE, "out", "KW*_odoo.csv"))):
    tag = os.path.basename(f)[:-9]  # KWww_yyyy
    kw = re.match(r"KW(\d+)_(\d+)", tag); kwlabel = f"{kw.group(2)}-KW{kw.group(1)}"
    flags, gflags = review_flags(os.path.join(HERE, "out", f"{tag}_review.md"))
    has_cal = os.path.exists(os.path.join(HERE, "calendar", f"{tag}.csv"))
    moni_cache = {}
    for r in csv.DictReader(open(f, encoding="utf-8")):
        d = dt.date.fromisoformat(r["date"])
        code, label = by_proj.get(r["project_id"], ("?", r["project_id"]))
        kunde = next((c for c in customers if r["name"].startswith(c + ":")), "")
        key = (d.year, d.month)
        if key not in moni_cache: moni_cache[key] = moni_days(*key)
        fl = flags.get((d.month, d.day), [])
        rows.append({
            "datum": d.isoformat(), "kw": kwlabel, "tag": f"{WD[d.weekday()]} {d:%d.%m.}",
            "code": code, "taetigkeit": label, "stunden": r["unit_amount"],
            "beschreibung": r["name"], "kunde": kunde,
            "hinweise": " | ".join(fl), "kalenderexport": "ja" if has_cal else "nein",
            "moni_uebernommen": "ja" if d.day in moni_cache[key] else "nein",
        })
out = os.path.join(HERE, "out", "dashboard.csv")
with open(out, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"{len(rows)} Zeilen -> {out}")
