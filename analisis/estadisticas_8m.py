"""
Estadísticas sobre mujeres tituladas en el ITAM para evento 8M.

Lee output/{carrera}.csv y output/mujeres_{carrera}.csv, calcula totales,
porcentajes y estadísticas por carrera y por año. Escribe resultados en analisis/.
"""

import csv
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
ANALISIS_DIR = Path(__file__).resolve().parent


def count_csv_rows(path: Path, encoding: str = "utf-8-sig") -> int:
    """Count data rows (exclude header) in a CSV."""
    with open(path, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return sum(1 for _ in reader)


def get_career_name_from_mujeres_file(path: Path) -> str:
    """mujeres_DERECHO.csv -> DERECHO."""
    stem = path.stem
    if stem.startswith("mujeres_"):
        return stem[8:]
    return stem


def main() -> None:
    ANALISIS_DIR.mkdir(parents=True, exist_ok=True)

    # Career CSVs (excl. mujeres_*)
    career_files = sorted(p for p in OUTPUT_DIR.glob("*.csv") if not p.name.startswith("mujeres_"))
    mujeres_files = sorted(OUTPUT_DIR.glob("mujeres_*.csv"))

    # Build career -> (path_carrera, path_mujeres)
    by_career = {}
    for p in career_files:
        by_career[p.stem] = {"carrera": p, "mujeres": None}
    for p in mujeres_files:
        name = get_career_name_from_mujeres_file(p)
        if name in by_career:
            by_career[name]["mujeres"] = p

    # Totals
    total_titulados = 0
    total_mujeres = 0
    rows_por_carrera = []
    mujeres_por_anio = {}

    for career_name, paths in by_career.items():
        n_carrera = count_csv_rows(paths["carrera"])
        n_mujeres = count_csv_rows(paths["mujeres"]) if paths["mujeres"] else 0
        # Solo contar en totales si la carrera tiene al menos 1 titulado (carreras nuevas vacías no cuentan)
        if n_carrera > 0:
            total_titulados += n_carrera
            total_mujeres += n_mujeres
        pct = (100.0 * n_mujeres / n_carrera) if n_carrera else 0.0
        rows_por_carrera.append({
            "carrera": career_name,
            "titulados_total": n_carrera,
            "mujeres_tituladas": n_mujeres,
            "porcentaje_mujeres": round(pct, 2),
        })
        # Mujeres por año (desde archivo mujeres_)
        if paths["mujeres"]:
            with open(paths["mujeres"], "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    anio = (row.get("anio_titulacion") or "").strip()
                    if anio:
                        mujeres_por_anio[anio] = mujeres_por_anio.get(anio, 0) + 1

    pct_global = (100.0 * total_mujeres / total_titulados) if total_titulados else 0.0

    # Resumen numérico (solo carreras con al menos 1 titulado)
    carreras_con_titulados = [r for r in rows_por_carrera if r["titulados_total"] > 0]
    resumen = {
        "total_titulados_itam": total_titulados,
        "total_mujeres_tituladas": total_mujeres,
        "porcentaje_mujeres_itam": round(pct_global, 2),
        "numero_carreras": len(carreras_con_titulados),
    }
    with open(ANALISIS_DIR / "resumen_8m.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    # Por carrera (CSV)
    with open(ANALISIS_DIR / "estadisticas_por_carrera.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["carrera", "titulados_total", "mujeres_tituladas", "porcentaje_mujeres"])
        w.writeheader()
        w.writerows(rows_por_carrera)

    # Mujeres por año (CSV) - evolución temporal
    anios_ordenados = sorted(mujeres_por_anio.keys(), key=int)
    with open(ANALISIS_DIR / "mujeres_por_anio.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["anio", "mujeres_tituladas"])
        for anio in anios_ordenados:
            w.writerow([anio, mujeres_por_anio[anio]])

    # Ranking carreras por % mujeres (solo carreras con al menos 1 titulado)
    ranking_pct = sorted(
        [r for r in rows_por_carrera if r["titulados_total"] > 0],
        key=lambda x: -x["porcentaje_mujeres"],
    )
    with open(ANALISIS_DIR / "ranking_porcentaje_mujeres.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["carrera", "titulados_total", "mujeres_tituladas", "porcentaje_mujeres"])
        w.writeheader()
        w.writerows(ranking_pct)

    # Reporte breve en texto para 8M
    with open(ANALISIS_DIR / "reporte_8m.txt", "w", encoding="utf-8") as f:
        f.write("ESTADÍSTICAS: MUJERES TITULADAS EN EL ITAM (8M)\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total titulados/as en el ITAM (Licenciatura): {total_titulados:,}\n")
        f.write(f"Total mujeres tituladas: {total_mujeres:,}\n")
        f.write(f"Porcentaje de mujeres tituladas en el ITAM: {pct_global:.2f}%\n\n")
        f.write("Top 10 carreras por porcentaje de mujeres tituladas:\n")
        for i, r in enumerate(ranking_pct[:10], 1):
            f.write(f"  {i}. {r['carrera']}: {r['porcentaje_mujeres']}% ({r['mujeres_tituladas']:,} de {r['titulados_total']:,})\n")
        f.write("\nTop 5 carreras por número absoluto de mujeres tituladas:\n")
        top_abs = sorted(
            [r for r in rows_por_carrera if r["titulados_total"] > 0],
            key=lambda x: -x["mujeres_tituladas"],
        )[:5]
        for i, r in enumerate(top_abs, 1):
            f.write(f"  {i}. {r['carrera']}: {r['mujeres_tituladas']:,} mujeres\n")

    print("Estadísticas 8M generadas en analisis/")
    print(f"  Total titulados ITAM: {total_titulados:,}")
    print(f"  Total mujeres tituladas: {total_mujeres:,}")
    print(f"  Porcentaje mujeres: {pct_global:.2f}%")
    print("  Archivos: resumen_8m.json, estadisticas_por_carrera.csv, mujeres_por_anio.csv, ranking_porcentaje_mujeres.csv, reporte_8m.txt")


if __name__ == "__main__":
    main()
