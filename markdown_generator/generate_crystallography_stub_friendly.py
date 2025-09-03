#!/usr/bin/env python3
# (Short header kept minimal due to state reset constraints)
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

STUB = False
HAS_GEMMI = False
try:
    import gemmi  # type: ignore
    HAS_GEMMI = True
except Exception:
    try:
        from CifFile import ReadCif  # type: ignore
    except Exception:
        STUB = True

try:
    import yaml  # type: ignore
except Exception:
    raise SystemExit("pyyaml is required. Install with: pip install pyyaml")

FRONTMATTER_KEEP = {
    "type","favorites","favorite","image","thumb","tags","excerpt",
    "paper_url","site_url","notes","doi","publication","ccdc_url",
}

def slugify(name: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]+', '-', name.strip().lower())
    s = re.sub(r'-+', '-', s).strip('-')
    return s or "structure"

def read_existing_front_matter(md_path: Path) -> Tuple[Dict[str, Any], str]:
    if not md_path.exists():
        return {}, ""
    text = md_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            yml = parts[1]
            body = parts[2].lstrip("\n")
            try:
                data = yaml.safe_load(yml) or {}
            except Exception:
                data = {}
            return data, body
    return {}, text

def write_front_matter(md_path: Path, fm: Dict[str, Any], body: str):
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with md_path.open("w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(fm, f, sort_keys=False, allow_unicode=True)
        f.write("---\n\n")
        f.write(body or "")

def merge_front_matter(existing: Dict[str, Any], newvals: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(existing) if existing else {}
    for k, v in newvals.items():
        if k in FRONTMATTER_KEEP and k in existing:
            continue
        if v is not None:
            out.setdefault(k, v)
    return out

def parse_full_gemmi(p: Path) -> Dict[str, Any]:
    doc = gemmi.cif.read_file(str(p))
    b = doc.sole_block()
    def g(key: str):
        v = b.find_value(key)
        if v is None or v.strip() in ('.','?',''):
            return None
        return v
    def gf(key: str):
        v = g(key)
        if v is None:
            return None
        m = re.match(r'^([-+]?\d*\.?\d+)', str(v))
        return float(m.group(1)) if m else None
    d = {}
    d["title"] = g("_chemical_name_common") or g("_publ_section_title") or g("_citation_title") or p.stem
    d["formula"] = g("_chemical_formula_sum")
    d["space_group"] = g("_symmetry_space_group_name_H-M") or g("_space_group_name_H-M_alt") or g("_space_group_name_Hall")
    d["a"] = gf("_cell_length_a"); d["b"] = gf("_cell_length_b"); d["c"] = gf("_cell_length_c")
    d["alpha"] = gf("_cell_angle_alpha"); d["beta"] = gf("_cell_angle_beta"); d["gamma"] = gf("_cell_angle_gamma")
    d["volume"] = gf("_cell_volume"); d["Z"] = gf("_cell_formula_units_Z")
    d["R1"] = gf("_refine_ls_R_factor_gt") or gf("_refine_ls_R_factor_all")
    for k in ["_refine_ls_wR_factor_ref","_refine_ls_wR_factor_gt","_refine_ls_wR_factor_obs","_refine_ls_wR_factor_all"]:
        d["R2"] = gf(k)
        if d["R2"] is not None: break
    d["temp_K"] = gf("_diffrn_ambient_temperature") or gf("_cell_measurement_temperature")
    d["wavelength_A"] = gf("_diffrn_radiation_wavelength")
    d["radiation_type"] = g("_diffrn_radiation_type")
    d["ccdc"] = g("_database_code_CSD") or g("_database_code_depnum_ccdc_archive")
    return d

def parse_stub(p: Path) -> Dict[str, Any]:
    return {
        "title": p.stem,
        "formula": None,
        "space_group": None,
        "a": None, "b": None, "c": None,
        "alpha": None, "beta": None, "gamma": None,
        "volume": None, "Z": None,
        "R1": None, "R2": None,
        "temp_K": None, "wavelength_A": None,
        "radiation_type": None, "ccdc": None,
    }

def parse_cif(p: Path) -> Dict[str, Any]:
    if STUB:
        return parse_stub(p)
    if HAS_GEMMI:
        return parse_full_gemmi(p)
    return parse_stub(p)

def build_markdown_body(parsed: Dict[str, Any]) -> str:
    lines = ["## Summary\n"]
    lines.append(f"- **Space group:** {parsed.get('space_group')}")
    if parsed.get("R1") is not None:
        lines.append(f"- **R1:** {parsed.get('R1')}")
    if parsed.get("R2") is not None:
        lines.append(f"- **R2 (wR2):** {parsed.get('R2')}")
    lines.append("")
    lines.append("## Unit Cell")
    lines.append(f"- a = {parsed.get('a')} Å, b = {parsed.get('b')} Å, c = {parsed.get('c')} Å")
    lines.append(f"- α = {parsed.get('alpha')}°, β = {parsed.get('beta')}°, γ = {parsed.get('gamma')}°")
    lines.append(f"- V = {parsed.get('volume')} Å³, Z = {parsed.get('Z')}")
    lines.append("")
    if STUB:
        lines.append("> _Stub mode:_ Install `gemmi` to auto-populate values, then re-run this script.")
        lines.append("")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description="Stub-friendly CIF -> Markdown generator for _crystallography.")
    default_cif_dir   = r"C:\Users\icoll\Colliard-Research.github.io\markdown_generator"
    default_site_root = r"C:\Users\icoll\Colliard-Research.github.io"
    ap.add_argument("--cif-dir",   default=default_cif_dir,   help="Directory containing .cif/.CIF files.")
    ap.add_argument("--site-root", default=default_site_root, help="Jekyll site root (contains _crystallography).")
    args = ap.parse_args()

    cif_dir   = Path(args.cif_dir).expanduser().resolve()
    site_root = Path(args.site_root).expanduser().resolve()
    md_dir = site_root / "_crystallography"
    md_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] STUB MODE: {STUB}")
    print(f"[INFO] CIF dir:   {cif_dir}")
    print(f"[INFO] Site root: {site_root}")
    print(f"[INFO] Writing to: {md_dir}")

    cif_paths = list(cif_dir.rglob("*.[cC][iI][fF]"))
    print(f"[INFO] Found {len(cif_paths)} CIFs")
    if not cif_paths:
        print("[WARN] No CIFs found. Check path and extensions.")
        return

    for idx, cif in enumerate(cif_paths, 1):
        parsed = parse_cif(cif)
        slug = slugify(cif.stem)
        date = dt.datetime.fromtimestamp(cif.stat().st_mtime).strftime("%Y-%m-%d")
        fm = {
            "layout": "single",
            "collection": "crystallography",
            "title": parsed.get("title") or cif.stem,
            "date": date,
            "space_group": parsed.get("space_group"),
            "a": parsed.get("a"),
            "b": parsed.get("b"),
            "c": parsed.get("c"),
            "alpha": parsed.get("alpha"),
            "beta": parsed.get("beta"),
            "gamma": parsed.get("gamma"),
            "volume": parsed.get("volume"),
            "Z": parsed.get("Z"),
            "R1": parsed.get("R1"),
            "R2": parsed.get("R2"),
            "permalink": f"/crystallography/{slug}/",
        }
        md_path = md_dir / f"{slug}.md"
        existing_fm, existing_body = read_existing_front_matter(md_path)
        merged = merge_front_matter(existing_fm, fm)
        body = existing_body or build_markdown_body(parsed)
        write_front_matter(md_path, merged, body)
        print(f"[OK] ({idx}/{len(cif_paths)}) Wrote {md_path}")

if __name__ == "__main__":
    main()
