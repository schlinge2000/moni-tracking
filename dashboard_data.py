#!/usr/bin/env python3
"""Sammelt alle Zeitdaten fuer das Dashboard -> out/dashboard_data.csv
   - gebucht:   MONI-Exporte Daten/json/monlist_*.json (bereits in Monlist uebertragen)
   - vorschlag: out/KW*_odoo.csv (aus Kalender + Wiki erzeugt, noch zu pruefen/uebernehmen)
"""
import csv, glob, json, os, re, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
mp = json.load(open(os.path.join(HERE, "mapping.json"), encoding="utf-8"))
labels = {"10030": "Urlaub", "10020": "Krankheit"}
for k, a in mp["activities"].items(): labels.setdefault(a["moni"][:5], a["label"])

def customer(text):
    t = (text or "").lower()
    for c in mp["customers"]:
        for m in c["match"]:
            if re.search(r"(?<![a-z0-9äöüß])" + re.escape(m.lower()) + r"(?![a-z0-9äöüß])", t): return c["name"]
    return ""

def read_monlist_txt(path, year, month):
    """Fallback, wenn die JSON-Datei nur in der Cloud liegt: Tag Von Bis Std Prj Pos Text"""
    items = []
    for line in open(path, encoding="cp1252", errors="replace"):
        m = re.match(r"\s*(\d{2})\s+(\d{4})\s+(\d{4})\s+[\d.]+\s+(\d{5})\s+\d+\s*(.*)$", line)
        if m:
            d, a, b, prj, txt = m.groups()
            items.append({"Year": year, "Month": month, "Day": int(d), "Start": f"{a[:2]}:{a[2:]}",
                          "End": f"{b[:2]}:{b[2:]}", "Project": prj, "Description": txt.strip()})
    return {"Items": items}

def hours(s, e):
    h1, m1 = map(int, s.split(":")); h2, m2 = map(int, e.split(":"))
    return (h2 * 60 + m2 - h1 * 60 - m1) / 60

rows, booked_days = [], set()
for f in sorted(glob.glob(os.path.join(ROOT, "Daten", "json", "monlist_*.json"))):
    y, mo = map(int, re.findall(r"(\d{4})_(\d{2})", f)[0])
    try: data = json.load(open(f, encoding="utf-8-sig"))
    except Exception:
        txt = os.path.join(ROOT, "Daten", f"monlist_{y}_{mo:02d}.txt")
        try: data = read_monlist_txt(txt, y, mo)
        except Exception as ex: print("uebersprungen", os.path.basename(f), ex); continue
    for it in data.get("Items", []):
        d = dt.date(it["Year"], it["Month"], it["Day"])
        booked_days.add(d)
        prj = str(it["Project"])
        rows.append([d.isoformat(), "gebucht", prj, labels.get(prj, (it.get("Description") or prj).strip()),
                     f"{hours(it['Start'], it['End']):.2f}", (it.get("Description") or "").strip(), customer(it.get("Description"))])
for f in sorted(glob.glob(os.path.join(HERE, "out", "KW*_odoo.csv"))):
    for r in csv.DictReader(open(f, encoding="utf-8")):
        d = dt.date.fromisoformat(r["date"])
        if d in booked_days: continue
        prj = r["project_id"][:5]
        rows.append([r["date"], "vorschlag", prj, labels.get(prj, r["project_id"]), r["unit_amount"], r["name"], customer(r["name"])])
rows.sort()
with open(os.path.join(HERE, "out", "dashboard_data.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["datum", "status", "projekt", "taetigkeit", "stunden", "beschreibung", "kunde"]); w.writerows(rows)
print(len(rows), "Zeilen,", min(r[0] for r in rows), "bis", max(r[0] for r in rows))
