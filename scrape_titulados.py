"""
ITAM Titulados Licenciatura Scraper.

Fetches the main programas page, collects only Licenciatura career links,
and in parallel scrapes each career's inner page into a separate CSV with
name split into: apellido_paterno, apellido_materno, primer_nombre, segundo_nombre, anio_titulacion.
"""

import csv
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# --- Constants ---
BASE_URL = "https://escolar1.rhon.itam.mx/titulacion"
PROGRAMAS_URL = f"{BASE_URL}/programas.asp"
OUTPUT_DIR = "output"
MAX_WORKERS = 5
RETRIES = 2
RETRY_DELAY = 2


def get_latest_html(url: str, force_encoding: str | None = None) -> str:
    """Fetch URL and return response text. Prefer server-declared charset (e.g. ISO-8859-1) so accents decode correctly."""
    for attempt in range(RETRIES + 1):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            if force_encoding:
                resp.encoding = force_encoding
            elif resp.encoding is None:
                resp.encoding = resp.apparent_encoding or "utf-8"
            # When server sends charset=iso-8859-1, keep it (do not override with apparent_encoding)
            return resp.text
        except requests.RequestException as e:
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            raise RuntimeError(f"Failed to fetch {url}: {e}") from e
    return ""


def sanitize_filename(name: str) -> str:
    """Sanitize career name for use as filename (replace invalid chars, keep accents)."""
    # Replace path-invalid and Excel-problematic chars with underscore
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    return sanitized.strip() or "unknown"


def parse_programas(html: str) -> list[tuple[str, str]]:
    """
    Parse programas.asp HTML and return list of (career_name, url) for Licenciatura only.
    Stops at DOCTORADO section. Page has nested tables; we use the inner table whose
    first row is exactly "LICENCIATURA" (one cell).
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for table in soup.find_all("table"):
        first_row = table.find("tr")
        if not first_row:
            continue
        header_cells = first_row.find_all(["th", "td"])
        if len(header_cells) != 1:
            continue
        section_name = header_cells[0].get_text(strip=True).upper()
        if section_name == "DOCTORADO":
            break
        if section_name != "LICENCIATURA":
            continue

        # This table is the Licenciatura table; collect links only from here
        for a in table.find_all("a", href=True):
            href = a.get("href", "").strip()
            if "titulados.asp" not in href or "prog=" not in href:
                continue
            name = a.get_text(strip=True)
            if not name:
                continue
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = f"https://escolar1.rhon.itam.mx{href}"
            else:
                url = f"{BASE_URL}/{href}"
            results.append((name, url))

    return results


def parse_titulados_table(html: str) -> list[tuple[str, str]]:
    """
    Parse a titulados.asp page and return list of (nombre_str, anio_str) for each data row.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows_data = []

    for table in soup.find_all("table"):
        header_cells = []
        thead = table.find("tr")
        if thead:
            header_cells = [th.get_text(strip=True) for th in thead.find_all(["th", "td"])]
        if not header_cells:
            continue
        # Encoding-robust: accept table when headers contain "Nombre"+"alumno" and "titulaci"
        header_text = " ".join(header_cells)
        has_nombre_alumno = "Nombre" in header_text and "alumno" in header_text
        has_anio_titulacion = "titulaci" in header_text
        if not (has_nombre_alumno and has_anio_titulacion):
            continue

        for tr in table.find_all("tr")[1:]:  # skip header
            cells = tr.find_all(["td", "th"])
            if len(cells) >= 2:
                nombre = cells[0].get_text(strip=True)
                anio = cells[1].get_text(strip=True)
                if nombre or anio:
                    rows_data.append((nombre, anio))
        break  # use first matching table

    return rows_data


def split_name(full_name: str) -> dict[str, str]:
    """
    Split full name into 4 components (Mexican convention: paternal, maternal, first, second).
    Heuristic: first two tokens = surnames, rest = first name and optional second name.
    For gender analysis later, use primer_nombre (and optionally segundo_nombre) with a name dictionary.
    """
    tokens = full_name.strip().split()
    n = len(tokens)
    if n >= 4:
        return {
            "apellido_paterno": tokens[0],
            "apellido_materno": tokens[1],
            "primer_nombre": tokens[2],
            "segundo_nombre": " ".join(tokens[3:]),
        }
    if n == 3:
        return {
            "apellido_paterno": tokens[0],
            "apellido_materno": tokens[1],
            "primer_nombre": tokens[2],
            "segundo_nombre": "",
        }
    if n == 2:
        return {
            "apellido_paterno": tokens[0],
            "apellido_materno": "",
            "primer_nombre": tokens[1],
            "segundo_nombre": "",
        }
    if n == 1:
        return {
            "apellido_paterno": tokens[0],
            "apellido_materno": "",
            "primer_nombre": "",
            "segundo_nombre": "",
        }
    return {
        "apellido_paterno": "",
        "apellido_materno": "",
        "primer_nombre": "",
        "segundo_nombre": "",
    }


def scrape_career(career_name: str, url: str, output_dir: Path) -> int:
    """
    Fetch one career's titulados page, parse table, split names, write one CSV.
    Returns row count. Raises on fetch/parse failure.
    If 0 rows and URL is titulados.asp, retry once with ISO-8859-1.
    """
    html = get_latest_html(url)
    rows = parse_titulados_table(html)
    if not rows and "titulados.asp" in url:
        html = get_latest_html(url, force_encoding="iso-8859-1")
        rows = parse_titulados_table(html)

    fieldnames = [
        "apellido_paterno",
        "apellido_materno",
        "primer_nombre",
        "segundo_nombre",
        "anio_titulacion",
        "nombre_completo",
    ]
    safe_name = sanitize_filename(career_name)
    out_path = output_dir / f"{safe_name}.csv"

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for nombre_str, anio_str in rows:
            parts = split_name(nombre_str)
            parts["anio_titulacion"] = anio_str
            parts["nombre_completo"] = nombre_str
            writer.writerow(parts)

    return len(rows)


def main() -> None:
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    print("Fetching programas page...")
    html = get_latest_html(PROGRAMAS_URL)
    careers = parse_programas(html)
    if not careers:
        print("No Licenciatura links found. Check page structure or URL.")
        return
    print(f"Found {len(careers)} Licenciatura programs.")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(scrape_career, name, url, output_path): (name, url)
            for name, url in careers
        }
        for future in as_completed(futures):
            name, url = futures[future]
            try:
                count = future.result()
                results.append((name, count, None))
                print(f"  OK: {name} -> {count} rows")
            except Exception as e:
                results.append((name, 0, str(e)))
                print(f"  FAIL: {name} -> {e}")

    ok = sum(1 for _, c, e in results if e is None)
    total_rows = sum(c for _, c, e in results if e is None)
    print(f"\nDone. {ok}/{len(careers)} careers written to {output_path.absolute()}. Total rows: {total_rows}.")
    if any(e for _, _, e in results if e):
        print("Some careers failed; check logs above.")


if __name__ == "__main__":
    main()
