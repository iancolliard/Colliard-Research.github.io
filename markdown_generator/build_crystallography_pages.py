#!/usr/bin/env python3
"""
Build crystallography index pages from _crystallography/*.md front-matter.

Outputs to _pages/ (by default):
  - crystallography_records.md        (leaderboards & milestones)
  - crystallography_year.md           (by year)
  - crystallography_spacegroups.md    (space-group atlas by crystal system)

Keeps _pages/ as destination, per user request.

Requirements:
    pip install pyyaml
    # Optional (better crystal system classification):
    pip install gemmi

Usage:
    python build_crystallography_pages.py \
      --site-root "C:\\Users\\icoll\\Colliard-Research.github.io" \
      --verbose
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:
    raise SystemExit("pyyaml is required. Install with: pip install pyyaml")

HAS_GEMMI = False
try:
    import gemmi  # type: ignore
    HAS_GEMMI = True
except Exception:
    HAS_GEMMI = False

@dataclass
class Entry:
    title: str
    date: Optional[dt.date]
    permalink: Optional[str]
    space_group: Optional[str]
    a: Optional[float]
    b: Optional[float]
    c: Optional[float]
    alpha: Optional[float]
    beta: Optional[float]
    gamma: Optional[float]
    volume: Optional[float]
    Z: Optional[float]
    R1: Optional[float]
    path: Path

    @property
    def year(self) -> Optional[int]:
        return self.date.year if self.date else None

    @property
    def crystal_system(self) -> Optional[str]:
        if not self.space_group:
            return None
        if HAS_GEMMI:
            try:
                return str(gemmi.SpaceGroup(self.space_group).crystal_system)
            except Exception:
                pass
        # fallback heuristic (very rough)
        s = self.space_group.lower().replace(" ", "")
        if "p-1" in s or s in ("p1","1","-1"):
            return "triclinic"
        if any(x in s for x in ["2/m", "c2", "i2", "p2", "p21"]):
            return "monoclinic"
        if any(x in s for x in ["mmm", "nnn"]):
            return "orthorhombic"
        if any(x in s for x in ["p4", "i4"]):
            return "tetragonal"
        if any(x in s for x in ["r3", "p3"]):
            return "trigonal"
        if any(x in s for x in ["p6"]):
            return "hexagonal"
        if any(x in s for x in ["-3m", "m-3", "23", "432"]):
            return "cubic"
        return None

def _read_front_matter(md_path: Path) -> Tuple[Dict[str, Any], str]:
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    yml = parts[1]
    body = parts[2].lstrip("\n")
    try:
        fm = yaml.safe_load(yml) or {}
    except Exception:
        fm = {}
    return fm, body

def _to_float(x) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except Exception:
        s = str(x)
        m = re.match(r'^([-+]?\d*\.?\d+)', s)
        return float(m.group(1)) if m else None

def _to_date(x) -> Optional[dt.date]:
    if not x:
        return None
    s = str(x)[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except Exception:
            continue
    try:
        return dt.datetime.fromisoformat(s).date()
    except Exception:
        return None

def collect_entries(cryst_dir: Path, verbose: bool=False) -> List[Entry]:
    entries: List[Entry] = []
    for md in sorted(cryst_dir.glob("*.md")):
        fm, _ = _read_front_matter(md)
        if not fm:
            if verbose:
                print(f"[SKIP] No front-matter: {md}")
            continue
        e = Entry(
            title=str(fm.get("title") or md.stem),
            date=_to_date(fm.get("date")),
            permalink=fm.get("permalink"),
            space_group=fm.get("space_group"),
            a=_to_float(fm.get("a")),
            b=_to_float(fm.get("b")),
            c=_to_float(fm.get("c")),
            alpha=_to_float(fm.get("alpha")),
            beta=_to_float(fm.get("beta")),
            gamma=_to_float(fm.get("gamma")),
            volume=_to_float(fm.get("volume")),
            Z=_to_float(fm.get("Z")),
            R1=_to_float(fm.get("R1")),
            path=md
        )
        entries.append(e)
    if verbose:
        print(f"[INFO] Loaded {len(entries)} entries from {cryst_dir}")
    return entries

def link_of(e: Entry) -> str:
    if e.permalink:
        return f"[{e.title}]({e.permalink})"
    # fallback to relative URL by filename
    slug = e.path.stem
    return f"[{e.title}](/crystallography/{slug}/)"

def write_records_page(pages_dir: Path, entries: List[Entry], verbose: bool=False):
    out = pages_dir / "crystallography_records.md"
    entries_non_null_vol = [e for e in entries if e.volume is not None]
    entries_non_null_r1 = [e for e in entries if e.R1 is not None and e.R1 >= 0]
    entries_non_null_a  = [e for e in entries if e.a is not None]
    entries_non_null_b  = [e for e in entries if e.b is not None]
    entries_non_null_c  = [e for e in entries if e.c is not None]

    top_vol = sorted(entries_non_null_vol, key=lambda e: e.volume, reverse=True)[:10]
    low_r1  = sorted(entries_non_null_r1, key=lambda e: e.R1)[:10]
    top_a   = sorted(entries_non_null_a, key=lambda e: e.a, reverse=True)[:5]
    top_b   = sorted(entries_non_null_b, key=lambda e: e.b, reverse=True)[:5]
    top_c   = sorted(entries_non_null_c, key=lambda e: e.c, reverse=True)[:5]

    # Most common space groups
    sg_counts = collections.Counter([e.space_group for e in entries if e.space_group])
    common_sg = sg_counts.most_common(12)

    lines = []
    lines += [
        "---",
        "layout: archive",
        "title: Record Holders & Milestones",
        "permalink: /crystallography/records/",
        "---",
        "",
        "# Record Holders & Milestones",
        "Automatically generated from the `_crystallography` collection.",
        "",
        "## Largest Unit Cell (Top 10 by volume)",
    ]
    if top_vol:
        for i, e in enumerate(top_vol, 1):
            lines.append(f"{i}. {link_of(e)} — **V = {e.volume} Å³**, Z = {e.Z}, space group {e.space_group}")
    else:
        lines.append("_No volume data available yet._")

    lines += ["", "## Lowest R1 (Top 10)"]
    if low_r1:
        for i, e in enumerate(low_r1, 1):
            lines.append(f"{i}. {link_of(e)} — **R1 = {e.R1}**, space group {e.space_group}")
    else:
        lines.append("_No R1 data available yet._")

    lines += ["", "## Longest Lattice Parameters"]
    a_str = ", ".join([f"{link_of(e)} ({e.a} Å)" for e in top_a]) if top_a else "_No a data._"
    b_str = ", ".join([f"{link_of(e)} ({e.b} Å)" for e in top_b]) if top_b else "_No b data._"
    c_str = ", ".join([f"{link_of(e)} ({e.c} Å)" for e in top_c]) if top_c else "_No c data._"
    lines += [f"**a (Top 5):**  {a_str}", "", f"**b (Top 5):**  {b_str}", "", f"**c (Top 5):**  {c_str}"]

    lines += ["", "## Most Common Space Groups (Top 12)"]
    if common_sg:
        for sg, count in common_sg:
            lines.append(f"- **{sg}** — {count} structure(s)")
    else:
        lines.append("_No space-group data yet._")

    out.write_text("\n".join(lines), encoding="utf-8")
    if verbose:
        print(f"[OK] Wrote {out}")

def write_year_page(pages_dir: Path, entries: List[Entry], verbose: bool=False):
    out = pages_dir / "crystallography_year.md"
    # group by year
    year_groups: Dict[int, List[Entry]] = collections.defaultdict(list)
    for e in entries:
        if e.year:
            year_groups[e.year].append(e)
    years_sorted = sorted(year_groups.keys(), reverse=True)

    lines = []
    lines += [
        "---",
        "layout: archive",
        "title: Crystallography by Year",
        "permalink: /crystallography/year/",
        "---",
        "",
        "# Crystallography by Year",
    ]

    if not years_sorted:
        lines.append("\n_No dated entries found yet._")
    else:
        for y in years_sorted:
            group = sorted(year_groups[y], key=lambda e: (e.date or dt.date(1900,1,1)), reverse=True)
            lines.append(f"\n## {y}  (Total: {len(group)})\n")
            for e in group:
                lines.append(f"- {link_of(e)}")


    out.write_text("\n".join(lines), encoding="utf-8")
    if verbose:
        print(f"[OK] Wrote {out}")

def write_spacegroup_page(pages_dir: Path, entries: List[Entry], verbose: bool=False):
    out = pages_dir / "crystallography_spacegroups.md"

    # group entries by space_group
    sg_map: Dict[str, List[Entry]] = collections.defaultdict(list)
    for e in entries:
        if e.space_group:
            sg_map[e.space_group].append(e)

    # group space groups by crystal system
    cs_map: Dict[str, List[str]] = collections.defaultdict(list)
    for sg in sg_map.keys():
        e = sg_map[sg][0]
        cs = e.crystal_system or "unknown"
        cs_map[cs].append(sg)

    for cs in cs_map:
        cs_map[cs] = sorted(set(cs_map[cs]), key=lambda s: s)

    # order of crystal systems
    order = ["triclinic","monoclinic","orthorhombic","tetragonal","trigonal","hexagonal","cubic","unknown"]

    lines = []
    lines += [
        "---",
        "layout: archive",
        "title: Space-Group Atlas",
        "permalink: /crystallography/space-groups/",
        "---",
        "",
        "# Space-Group Atlas",
        "A “periodic-table style” overview of space groups observed in my dataset, grouped by crystal system.",
    ]
    if not HAS_GEMMI:
        lines += ["", "> _Note:_ Install `gemmi` for accurate crystal-system classification from H–M symbols.", ""]

    any_section = False
    for cs in order:
        if cs not in cs_map:
            continue
        any_section = True
        lines.append(f"\n## {cs.capitalize()}\n")
        # summary list
        for sg in cs_map[cs]:
            count = len(sg_map[sg])
            anchor = re.sub(r'[^a-zA-Z0-9]+', '-', sg.lower()).strip('-')
            lines.append(f"- **{sg}** — {count} structure(s)  ([jump](#sg-{anchor}))")
        # details
        lines.append("\n<details><summary>Show entries</summary>\n")
        for sg in cs_map[cs]:
            anchor = re.sub(r'[^a-zA-Z0-9]+', '-', sg.lower()).strip('-')
            lines.append(f"\n### <a id='sg-{anchor}'></a>{sg}\n")
            for e in sorted(sg_map[sg], key=lambda x: (x.date or dt.date(1900,1,1)), reverse=True):
                lines.append(f"- {link_of(e)}")
        lines.append("\n</details>\n")

    if not any_section:
        lines.append("\n_No space-group data available yet._\n")

    out.write_text("\n".join(lines), encoding="utf-8")
    if verbose:
        print(f"[OK] Wrote {out}")

def main():
    ap = argparse.ArgumentParser(description="Build crystallography subpages from _crystallography/*.md")
    default_site_root = r"C:\Users\icoll\Colliard-Research.github.io"
    ap.add_argument("--site-root", default=default_site_root, help="Path to Jekyll site root")
    ap.add_argument("--verbose", action="store_true", help="Print progress information")
    args = ap.parse_args()

    site_root = Path(args.site_root).expanduser().resolve()
    cryst_dir = site_root / "_crystallography"
    pages_dir = site_root / "_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    if args.verbose:
        print(f"[INFO] Site root: {site_root}")
        print(f"[INFO] Reading entries from: {cryst_dir}")
        print(f"[INFO] Writing pages to: {pages_dir}")

    entries = collect_entries(cryst_dir, verbose=args.verbose)

    write_records_page(pages_dir, entries, verbose=args.verbose)
    write_year_page(pages_dir, entries, verbose=args.verbose)
    write_spacegroup_page(pages_dir, entries, verbose=args.verbose)

    if args.verbose:
        print("[DONE] All pages written.")

if __name__ == "__main__":
    main()
