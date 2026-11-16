#!/usr/bin/env python3
"""
Schreibt die MONI-Zeilen aus out/KW*_moni.md in den MONI-Datenordner (Ziel und Dateiname in config.json).

  uv run export_moni.py --dry-run   # nur anzeigen
  uv run export_moni.py             # schreiben (vorhandene Tage bleiben, ausser vorhandene_tage_ueberschreiben=true)
"""
import datetime as dt, glob, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
cfg = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))

def resolve(p):
    if os.name != "nt" and re.match(r"^[A-Za-z]:\\", p):   # Claude-Lauf: Windows-Pfad auf eingebundenen Ordner abbilden
        parts = p.split("\\"); name = os.path.basename(ROOT)
        if name in parts: return os.path.join(ROOT, *parts[parts.index(name) + 1:])
        sys.exit(f"Zielordner hier nicht erreichbar: {p}")
    return p if os.path.isabs(p) else os.path.join(ROOT, p)

def key(ln): return tuple(map(int, ln.split("|")[0].split(",")))

def main():
    dry = "--dry-run" in sys.argv
    target = resolve(cfg["moni_ziel_ordner"])
    if not os.path.isdir(target): sys.exit(f"Zielordner fehlt: {target}")
    ab = dt.date.fromisoformat(cfg.get("ab_datum", "2000-01-01"))
    files = defaultdict(list)
    for f in glob.glob(os.path.join(HERE, "out", "KW*_moni.md")):
        for ln in open(f, encoding="utf-8"):
            if not re.match(r"^\d{4},\d{1,2},\d{1,2}\|", ln): continue
            d = dt.date(*key(ln))
            if d < ab: continue
            iy, iw, _ = d.isocalendar()
            files[cfg["dateiname"].format(jahr=d.year, monat=d.month, kw=iw)].append(ln.strip())
    for name in sorted(files):
        dest = os.path.join(target, name)
        existing = [l for l in (open(dest, encoding="utf-8-sig").read().splitlines() if os.path.exists(dest) else []) if l.strip()]
        have = {key(l) for l in existing if "|" in l}
        new = sorted(set(files[name]), key=key)
        if cfg.get("vorhandene_tage_ueberschreiben"):
            nk = {key(l) for l in new}
            lines = sorted([l for l in existing if "|" in l and key(l) not in nk] + new, key=key); n = len(new)
        else:
            add = [l for l in new if key(l) not in have]; lines = sorted([l for l in existing if "|" in l] + add, key=key); n = len(add)
        print(f"{name}: +{n} Tage" + (" (dry-run)" if dry else ""))
        if n and not dry:
            with open(dest, "w", encoding="utf-8", newline="\n") as fh: fh.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
