#!/usr/bin/env python3
"""
All-in-one: CIF -> Jekyll Markdown generator/updater for _crystallography.

Features
--------
- Recursively walks a CIF directory
- Extracts:
  * Space group
  * R1 (refine_ls_R_factor_gt/all)
  * R2 / wR2 (refine_ls_wR_factor_* variants)
  * Unit cell: a,b,c, alpha,beta,gamma, volume, Z
  * Optional metadata: temperature (K), wavelength (Å), formula, CCDC code, radiation type, journal year
- Generates or updates Markdown files in <site_root>/_crystallography/<slug>.md
  * Preserves your manual fields via merge (e.g., type, favorites, image, tags, excerpt, paper_url)
  * Applies per-slug overrides from a YAML file
  * Adds a permalink and optional image placeholder path
  * Optionally copies CIFs to <site_root>/<files-subdir>/<slug>.cif and links them
- Optionally writes a TSV index file

Dependencies
------------
    pip install gemmi pyyaml
    # Or fallback CIF parser:
    pip install PyCifRW pyyaml

Usage
-----
    python generate_crystallography_all_in_one.py \
      --cif-dir "C:\\Users\\you\\path\\to\\cifs" \
      --site-root "C:\\Users\\you\\Colliard-Research.github.io" \
      --images-subdir images/crystals \
      --files-subdir files \
      --overrides overrides.yaml \
      --tsv out/crystallography_index.tsv \
      --copy-cifs

Notes
-----
- Slug is derived from CIF filename (lowercase, hyphens). You can override per slug via overrides.yaml.
- Date is taken from journal_year if present (YYYY-01-01), else file mtime (YYYY-MM-DD).
- Merge strategy: we DO NOT override keys listed in FRONTMATTER_KEEP if they already exist.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Optional deps
HAS_GEMMI = False
try:
    import gemmi  # type: ignore
    HAS_GEMMI = True
except Exception:
    HAS_GEMMI = False

try:
    import yaml  # type: ignore
except Exception as e:
    raise SystemExit("pyyaml is required. Install with: pip install pyyaml")

# ---------------- Parsing helpers ----------------

def _float_clean(x: Optional[str]) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if s in ('.','?',''):
        return None
    # strip esd in parentheses: 12.345(6)
    m = re.match(r'^([-+]?\d*\.?\d+)', s)
    return float(m.group(1)) if m else None

def parse_cif_gemmi(p: Path) -> Dict[str, Any]:
    doc = gemmi.cif.read_file(str(p))
    b = doc.sole_block()

    def g(key: str, alt: Optional[str]=None) -> Optional[str]:
        v = b.find_value(key)
        if (v is None or v.strip() in ('.','?','')) and alt:
            v = b.find_value(alt)
        if v is None or v.strip() in ('.','?',''):
            return None
        return v

    def gf(key: str, alt: Optional[str]=None) -> Optional[float]:
        return _float_clean(g(key, alt))

    data: Dict[str, Any] = {}
    data["title"] = g("_chemical_name_common") or g("_publ_section_title") or g("_citation_title") or p.stem
    data["formula"] = g("_chemical_formula_sum")
    data["space_group"] = g("_symmetry_space_group_name_H-M") or g("_space_group_name_H-M_alt") or g("_space_group_name_Hall")

    # Unit cell
    data["a"] = gf("_cell_length_a")
    data["b"] = gf("_cell_length_b")
    data["c"] = gf("_cell_length_c")
    data["alpha"] = gf("_cell_angle_alpha")
    data["beta"] = gf("_cell_angle_beta")
    data["gamma"] = gf("_cell_angle_gamma")
    data["volume"] = gf("_cell_volume")
    data["Z"] = gf("_cell_formula_units_Z")

    # R-factors
    data["R1"] = gf("_refine_ls_R_factor_gt") or gf("_refine_ls_R_factor_all")
    wr2_keys = [
        "_refine_ls_wR_factor_ref",
        "_refine_ls_wR_factor_gt",
        "_refine_ls_wR_factor_obs",
        "_refine_ls_wR_factor_all",
    ]
    data["R2"] = None
    for k in wr2_keys:
        v = gf(k)
        if v is not None:
            data["R2"] = v
            break

    # Extra metadata
    data["temp_K"] = gf("_diffrn_ambient_temperature") or gf("_cell_measurement_temperature")
    data["wavelength_A"] = gf("_diffrn_radiation_wavelength")
    data["radiation_type"] = g("_diffrn_radiation_type")
    data["ccdc"] = g("_database_code_CSD") or g("_database_code_depnum_ccdc_archive")
    data["journal_year"] = g("_journal_year")

    return data

def parse_cif_pycifrw(p: Path) -> Dict[str, Any]:
    try:
        from CifFile import ReadCif  # type: ignore
    except Exception:
        raise SystemExit("Neither gemmi nor PyCifRW available. Install one of them.")
    cf = ReadCif(str(p))
    blockname = next(iter(cf.keys()))
    b = cf[blockname]

    def g(key: str) -> Optional[str]:
        v = b.get(key)
        if v is None:
            return None
        s = str(v).strip()
        return None if s in ('.','?','') else s

    def gf(key: str) -> Optional[float]:
        return _float_clean(g(key))

    data: Dict[str, Any] = {}
    data["title"] = g("_chemical_name_common") or g("_publ_section_title") or g("_citation_title") or p.stem
    data["formula"] = g("_chemical_formula_sum")
    data["space_group"] = g("_symmetry_space_group_name_H-M") or g("_space_group_name_H-M_alt") or g("_space_group_name_Hall")

    data["a"] = gf("_cell_length_a")
    data["b"] = gf("_cell_length_b")
    data["c"] = gf("_cell_length_c")
    data["alpha"] = gf("_cell_angle_alpha")
    data["beta"] = gf("_cell_angle_beta")
    data["gamma"] = gf("_cell_angle_gamma")
    data["volume"] = gf("_cell_volume")
    data["Z"] = gf("_cell_formula_units_Z")

    data["R1"] = gf("_refine_ls_R_factor_gt") or gf("_refine_ls_R_factor_all")
    wr2_keys = [
        "_refine_ls_wR_factor_ref",
        "_refine_ls_wR_factor_gt",
        "_refine_ls_wR_factor_obs",
        "_refine_ls_wR_factor_all",
    ]
    data["R2"] = None
    for k in wr2_keys:
        v = gf(k)
        if v is not None:
            data["R2"] = v
            break

    data["temp_K"] = gf("_diffrn_ambient_temperature") or gf("_cell_measurement_temperature")
    data["wavelength_A"] = gf("_diffrn_radiation_wavelength")
    data["radiation_type"] = g("_diffrn_radiation_type")
    data["ccdc"] = g("_database_code_CSD") or g("_database_code_depnum_ccdc_archive")
    data["journal_year"] = g("_journal_year")

    return data

def parse_cif(p: Path) -> Dict[str, Any]:
    if HAS_GEMMI:
        return parse_cif_gemmi(p)
    return parse_cif_pycifrw(p)

# ---------------- Utilities ----------------

FRONTMATTER_KEEP = {
    # Keys we NEVER clobber if they already exist in the MD:
    "type", "favorites", "favorite", "image", "thumb", "tags", "excerpt",
    "paper_url", "site_url", "notes", "doi", "publication", "ccdc_url",
}

def slugify(name: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9]+', '-', name.strip().lower())
    s = re.sub(r'-+', '-', s).strip('-')
    return s or "structure"

def guess_date(cif_path: Path, parsed: Dict[str, Any]) -> str:
    jy = parsed.get("journal_year")
    if jy:
        m = re.search(r'(\d{4})', str(jy))
        if m:
            return f"{m.group(1)}-01-01"
    # fallback to file mtime
    return dt.datetime.fromtimestamp(cif_path.stat().st_mtime).strftime("%Y-%m-%d")

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

def merge_front_matter(existing: Dict[str, Any], newvals: Dict[str, Any], force: bool=False) -> Dict[str, Any]:
    if force:
        # overwrite everything except the keep-keys
        out = dict(existing) if existing else {}
        out.update(newvals)
        for k in FRONTMATTER_KEEP:
            if k in existing:
                out[k] = existing[k]
        return out

    # default: only fill in missing fields; never clobber keep-keys
    out = dict(existing) if existing else {}
    for k, v in newvals.items():
        if k in FRONTMATTER_KEEP and k in existing:
            continue
        if v is not None:
            out.setdefault(k, v)
    return out

def build_markdown_body(parsed: Dict[str, Any], cif_link: Optional[str]) -> str:
    lines = []
    lines.append("## Summary\n")
    lines.append(f"- **Space group:** {parsed.get('space_group')}")
    if parsed.get("R1") is not None:
        lines.append(f"- **R1:** {parsed.get('R1')}")
    if parsed.get("R2") is not None:
        lines.append(f"- **R2 (wR2):** {parsed.get('R2')}")
    if parsed.get("temp_K") is not None:
        lines.append(f"- **Temperature (K):** {parsed.get('temp_K')}")
    if parsed.get("wavelength_A") is not None:
        lines.append(f"- **Wavelength (Å):** {parsed.get('wavelength_A')}")
    if parsed.get("ccdc"):
        lines.append(f"- **CCDC:** {parsed.get('ccdc')}")
    lines.append("")
    lines.append("## Unit Cell")
    lines.append(f"- a = {parsed.get('a')} Å, b = {parsed.get('b')} Å, c = {parsed.get('c')} Å")
    lines.append(f"- α = {parsed.get('alpha')}°, β = {parsed.get('beta')}°, γ = {parsed.get('gamma')}°")
    lines.append(f"- V = {parsed.get('volume')} Å³, Z = {parsed.get('Z')}")
    lines.append("")
    if cif_link:
        lines.append(f"**CIF:** [{cif_link}]({cif_link})")
        lines.append("")
    lines.append("## Notes")
    lines.append("_Add refinement details, synthesis context, or related publication links here._")
    lines.append("")
    return "\n".join(lines)

def load_overrides(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if not path or not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(data, dict):
        return {}
    # Ensure nested dict
    fixed = {}
    for k, v in data.items():
        if isinstance(v, dict):
            fixed[k] = v
    return fixed

# ---------------- Main ----------------

def main():
    ap = argparse.ArgumentParser(description="Generate/Update _crystallography MD files from CIFs.")

    # ✅ Set your personal defaults here so you can just press Run in Spyder
    default_cif_dir   = r"C:\Users\icoll\Colliard-Research.github.io\markdown_generator"
    default_site_root = r"C:\Users\icoll\Colliard-Research.github.io"

    ap.add_argument("--cif-dir",    default=default_cif_dir,   help="Directory containing .cif files (recursively scanned).")
    ap.add_argument("--site-root",  default=default_site_root, help="Path to your Jekyll site root (contains _crystallography).")

    # ✅ Give defaults for everything else, too
    ap.add_argument("--images-subdir", default="images/crystals", help="Relative images dir for default image path.")
    ap.add_argument("--files-subdir",  default="files",           help="Relative files dir used for CIF links/copies.")
    ap.add_argument("--overrides",     default=None,              help="Optional overrides.yaml path (per-slug).")
    ap.add_argument("--tsv",           default=None,              help="Optional TSV index output path.")
    ap.add_argument("--copy-cifs",     action="store_true",       help="Copy CIFs into <site_root>/<files-subdir>/<slug>.cif.")
    ap.add_argument("--force",         action="store_true",       help="Force overwrite of auto fields (keep custom keys).")
    ap.add_argument("--dry-run",       action="store_true",       help="Parse and preview, but do not write files.")

    args = ap.parse_args()

    from pathlib import Path
    import datetime as dt

    cif_dir   = Path(args.cif_dir).expanduser().resolve()
    site_root = Path(args.site_root).expanduser().resolve()
    md_dir = site_root / "_crystallography"

    # 🔒 Hardened reads in case Spyder passes something weird
    images_subdir = (getattr(args, "images_subdir", "images/crystals") or "images/crystals").strip("/")
    files_subdir  = (getattr(args, "files_subdir",  "files")            or "files").strip("/")
    overrides_arg = getattr(args, "overrides", None)
    tsv_arg       = getattr(args, "tsv", None)

    overrides_path = Path(overrides_arg).expanduser().resolve() if overrides_arg else None
    overrides = load_overrides(overrides_path)

    rows = []
    for cif_path in cif_dir.rglob("*.cif"):
        try:
            parsed = parse_cif(cif_path)
        except Exception as e:
            print(f"[WARN] Failed to parse {cif_path}: {e}")
            continue

        base_slug = slugify(cif_path.stem)
        slug = base_slug
        if overrides.get(base_slug) and overrides[base_slug].get("slug"):
            slug = slugify(str(overrides[base_slug]["slug"]))

        # CIF link & optional copy
        cif_rel  = f"/{files_subdir}/{slug}.cif"
        cif_dest = site_root / files_subdir / f"{slug}.cif"
        cif_link = None
        if args.copy_cifs:
            try:
                cif_dest.parent.mkdir(parents=True, exist_ok=True)
                if not args.dry_run:
                    import shutil
                    shutil.copy2(str(cif_path), str(cif_dest))
                cif_link = cif_rel
            except Exception as e:
                print(f"[WARN] Could not copy CIF {cif_path} -> {cif_dest}: {e}")
                cif_link = None
        else:
            cif_link = cif_rel  # optimistic link if you’ll commit CIFs later

        title = parsed.get("title") or cif_path.stem
        date  = guess_date(cif_path, parsed)

        new_fm = {
            "layout": "single",
            "collection": "crystallography",
            "title": title,
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
            "temp_K": parsed.get("temp_K"),
            "wavelength_A": parsed.get("wavelength_A"),
            "formula": parsed.get("formula"),
            "ccdc": parsed.get("ccdc"),
            "radiation_type": parsed.get("radiation_type"),
            "image": f"/{images_subdir}/{slug}.jpg",
            "cif_url": cif_link,
            "permalink": f"/crystallography/{slug}/",
        }

        # Apply overrides if present
        if overrides.get(base_slug):
            for k, v in overrides[base_slug].items():
                if k != "slug":
                    new_fm[k] = v

        md_path = md_dir / f"{slug}.md"
        existing_fm, existing_body = read_existing_front_matter(md_path)
        merged_fm = merge_front_matter(existing_fm, new_fm, force=args.force)
        body = existing_body or build_markdown_body(parsed, cif_link)

        if args.dry_run:
            print(f"[DRY] Would write {md_path}")
        else:
            write_front_matter(md_path, merged_fm, body)
            print(f"[OK] Wrote {md_path}")

        rows.append({
            "slug": slug,
            "title": merged_fm.get("title",""),
            "date": merged_fm.get("date",""),
            "type": merged_fm.get("type",""),
            "favorites": merged_fm.get("favorites", merged_fm.get("favorite","")),
            "space_group": merged_fm.get("space_group",""),
            "a": merged_fm.get("a",""),
            "b": merged_fm.get("b",""),
            "c": merged_fm.get("c",""),
            "alpha": merged_fm.get("alpha",""),
            "beta": merged_fm.get("beta",""),
            "gamma": merged_fm.get("gamma",""),
            "volume": merged_fm.get("volume",""),
            "Z": merged_fm.get("Z",""),
            "R1": merged_fm.get("R1",""),
            "R2": merged_fm.get("R2",""),
            "temp_K": merged_fm.get("temp_K",""),
            "wavelength_A": merged_fm.get("wavelength_A",""),
            "formula": merged_fm.get("formula",""),
            "ccdc": merged_fm.get("ccdc",""),
            "radiation_type": merged_fm.get("radiation_type",""),
            "cif_url": merged_fm.get("cif_url",""),
            "md_path": str(md_path),
            "src_cif": str(cif_path),
        })

    # TSV export
    if tsv_arg and rows:
        tsv_path = Path(tsv_arg).expanduser().resolve()
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        import csv
        with tsv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "slug","title","date","type","favorites","space_group",
                "a","b","c","alpha","beta","gamma","volume","Z","R1","R2",
                "temp_K","wavelength_A","formula","ccdc","radiation_type",
                "cif_url","src_cif","md_path"
            ], delimiter="\t")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        print(f"[OK] Wrote TSV: {tsv_path}")
