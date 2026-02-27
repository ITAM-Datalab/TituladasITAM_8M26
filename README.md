# Tituladas ITAM — 8M 2026

Proyecto del **ITAM-DataLab** para visibilizar a las mujeres tituladas del ITAM en el marco del **8 de marzo (8M)**. A partir de los datos públicos de titulación en Licenciatura, se extrajeron, clasificaron por género (primer nombre) y se generaron estadísticas para el evento.

---

## Resultados principales

### Cifras globales (Licenciatura, datos al 01 de enero de 2026)


| Indicador                                     | Valor      |
| --------------------------------------------- | ---------- |
| **Total de tituladas y titulados en el ITAM** | 22,916     |
| **Mujeres tituladas**                         | 7,717      |
| **Porcentaje de mujeres tituladas**           | **33.68%** |
| Carreras con al menos un titulado             | 20         |


*(Se excluyen del conteo las carreras aún sin titulados, por ser programas nuevos.)*

### Carreras con mayor porcentaje de mujeres tituladas (Top 5 con datos representativos)

1. **Relaciones Internacionales** — 57.55% (770 de 1,338)
2. **Ciencias Sociales** — 54.37% (56 de 103)
3. **Ciencia Política** — 41.09% (348 de 847)
4. **Actuaría** — 40.05% (646 de 1,613)
5. **Contaduría Pública** — 38.74% (788 de 2,034)

### Carreras con más mujeres tituladas en números absolutos (Top 5)

1. **Administración** — 1,831 mujeres
2. **Economía** — 1,176 mujeres
3. **Derecho** — 813 mujeres
4. **Contaduría Pública** — 788 mujeres
5. **Relaciones Internacionales** — 770 mujeres

Todos los resultados detallados (por carrera, por año, rankings) están en la carpeta `analisis/`.

---

## Cómo se hizo

### Fuente de datos

- **Origen:** listado público de titulados del ITAM (Licenciatura), disponible en la página oficial de titulación.
- **Alcance:** solo programas de **Licenciatura** (no se incluye Doctorado).
- **Corte:** titulados y tituladas al **01 de enero de 2026**.

### Pipeline del proyecto

1. **Extracción**
  Se obtuvieron los datos de la página del ITAM: un CSV por carrera con columnas de nombre completo y año de titulación. El nombre se partió en: apellido paterno, apellido materno, primer nombre y segundo nombre para poder analizar por género usando el primer nombre.
2. **Clasificación por género**
  Con la librería `gender-guesser` (nombres en español) se identificaron nombres femeninos. Se generó un diccionario de nombres de mujer (`nombres_mujeres.txt` / `.json`) y, para cada carrera, un CSV `mujeres_{carrera}.csv` con solo las filas clasificadas como mujeres.
3. **Estadísticas 8M**
  Un script en `analisis/` suma totales, calcula porcentajes por carrera y genera rankings y evolución por año. Las carreras sin ningún titulado (programas nuevos) no se incluyen en los totales ni en el conteo de carreras.

### Estructura del repositorio

```
TituladasITAM/
├── scrape_titulados.py    # Scraper: programas.asp → titulados por carrera → CSVs
├── build_mujeres_csv.py   # Diccionario de nombres mujer + CSVs mujeres_{carrera}.csv
├── requirements.txt       # Dependencias Python
├── output/                # CSVs por carrera y mujeres_{carrera}.csv
├── analisis/
│   ├── estadisticas_8m.py # Cálculo de estadísticas para 8M
│   ├── resumen_8m.json    # Totales y porcentaje global
│   ├── estadisticas_por_carrera.csv
│   ├── mujeres_por_anio.csv
│   ├── ranking_porcentaje_mujeres.csv
│   └── reporte_8m.txt    # Resumen en texto
├── nombres_mujeres.txt    # Diccionario de nombres clasificados como mujer
└── README.md
```

### Cómo reproducir

**Requisitos:** Python 3.x, `venv` recomendado.

```bash
# Entorno y dependencias
python -m venv venv
# En Windows: venv\Scripts\activate
# En Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

# 1. Extraer datos de la web (genera output/*.csv)
python scrape_titulados.py

# 2. Construir diccionario de nombres mujer y CSVs mujeres_{carrera}.csv
python build_mujeres_csv.py

# 3. Generar estadísticas 8M (genera analisis/*.csv, .json, reporte_8m.txt)
python analisis/estadisticas_8m.py
```

---

*Proyecto ITAM-DataLab — 8M 2026*