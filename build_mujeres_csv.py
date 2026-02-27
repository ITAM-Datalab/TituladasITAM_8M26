"""
Build female first-name dictionary from output/*.csv and generate mujeres_{carrera}.csv.

Reads all career CSVs, collects unique first names, classifies with gender-guesser,
saves nombres_mujeres.txt (and .json), then filters each career CSV to rows
where primer_nombre is in the female set and writes output/mujeres_{carrera}.csv.
"""

import csv
import json
import re
from pathlib import Path

import gender_guesser.detector as gender

OUTPUT_DIR = Path("output")
NOMBRES_TXT = Path("nombres_mujeres.txt")
NOMBRES_JSON = Path("nombres_mujeres.json")
FIELDNAMES = [
    "apellido_paterno",
    "apellido_materno",
    "primer_nombre",
    "segundo_nombre",
    "anio_titulacion",
    "nombre_completo",
]


def sanitize_filename(name: str) -> str:
    """Sanitize for filename (match scrape_titulados)."""
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    return sanitized.strip() or "unknown"


def collect_unique_names(output_dir: Path):
    """Collect unique primer_nombre and segundo_nombre from all career CSVs (excl. mujeres_*.csv)."""
    unique = set()
    career_files = []
    for p in sorted(output_dir.glob("*.csv")):
        if p.name.startswith("mujeres_"):
            continue
        career_files.append(p)
        with open(p, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pn = (row.get("primer_nombre") or "").strip()
                sn = (row.get("segundo_nombre") or "").strip()
                if pn:
                    unique.add(pn)
                if sn:
                    unique.add(sn)
    return unique, career_files


def build_female_names_set(unique_names: set[str]) -> set[str]:
    """Classify names with gender-guesser; return set of names considered female (uppercase)."""
    d = gender.Detector()
    female = set()
    for name in unique_names:
        # detector works better with capitalized form
        guess = d.get_gender(name.capitalize())
        if guess in ("female", "mostly_female"):
            female.add(name.upper())
    return female


def save_dictionary(female_names: set[str]) -> None:
    """Write nombres_mujeres.txt and nombres_mujeres.json."""
    sorted_names = sorted(female_names)
    with open(NOMBRES_TXT, "w", encoding="utf-8") as f:
        for n in sorted_names:
            f.write(n + "\n")
    with open(NOMBRES_JSON, "w", encoding="utf-8") as f:
        json.dump(sorted_names, f, ensure_ascii=False, indent=0)
    print(f"Saved {len(sorted_names)} names to {NOMBRES_TXT} and {NOMBRES_JSON}.")


def load_female_names() -> set[str]:
    """Load female names from nombres_mujeres.txt."""
    if not NOMBRES_TXT.exists():
        return set()
    with open(NOMBRES_TXT, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def write_mujeres_csv(career_csv_path: Path, female_names: set[str], output_dir: Path) -> int:
    """Filter career CSV to rows with primer_nombre in female_names; write mujeres_{carrera}.csv. Returns row count."""
    career_stem = career_csv_path.stem  # e.g. ACTUARÍA
    out_path = output_dir / f"mujeres_{sanitize_filename(career_stem)}.csv"
    rows_written = 0
    with open(career_csv_path, "r", encoding="utf-8-sig", newline="") as fin:
        reader = csv.DictReader(fin)
        with open(out_path, "w", newline="", encoding="utf-8-sig") as fout:
            writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
            writer.writeheader()
            for row in reader:
                primer = (row.get("primer_nombre") or "").strip().upper()
                if primer in female_names:
                    writer.writerow(row)
                    rows_written += 1
    return rows_written


def main() -> None:
    if not OUTPUT_DIR.is_dir():
        print(f"Missing directory: {OUTPUT_DIR}")
        return

    unique_names, career_files = collect_unique_names(OUTPUT_DIR)
    print(f"Collected {len(unique_names)} unique first names from {len(career_files)} career CSVs.")

    female_names = build_female_names_set(unique_names)
    print(f"Classified {len(female_names)} names as female.")
    save_dictionary(female_names)

    total_mujeres = 0
    for p in career_files:
        n = write_mujeres_csv(p, female_names, OUTPUT_DIR)
        total_mujeres += n
        print(f"  mujeres_{p.stem}.csv -> {n} rows")
    print(f"\nDone. Total rows in mujeres_*.csv: {total_mujeres}.")


if __name__ == "__main__":
    main()
