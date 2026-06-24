# -*- coding: utf-8 -*-
"""
export_stats.py — Lee la pestaña "h2test" del Google Sheet y genera
docs/dashboard/data.json con estadísticas agregadas (sin PII).

Fundación ROFÉ | Jóvenes creaTIvos
"""

import io
import json
import os
import subprocess
import sys
from datetime import datetime

# truststore: en Windows con interceptación SSL corporativa, usa el cert store del SO
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# UTF-8 en consola Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import gspread
from google.oauth2.service_account import Credentials

# ── Configuración ─────────────────────────────────────────────────────────────
SHEET_ID          = "1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs"
NOMBRE_HOJA       = "h2test"
CREDENCIALES_JSON = "credenciales_service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_DATA_JSON    = os.path.join(PROYECTO_ROOT, "docs", "dashboard", "data.json")


# ── Utilidades ────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[export-stats] {msg}", flush=True)


def _limpiar_porcentaje(valor: str) -> float:
    limpio = valor.strip().replace("%", "").replace(",", ".").strip()
    if not limpio:
        return 0.0
    try:
        return round(float(limpio), 2)
    except ValueError:
        return 0.0


def _es_fila_vacia(row: list) -> bool:
    return all(c.strip() == "" for c in row)


# ── Google Sheets ─────────────────────────────────────────────────────────────
def conectar_hoja() -> gspread.Worksheet:
    log("Conectando a Google Sheets...")
    ruta_creds = os.path.join(DIRECTORIO_SCRIPT, CREDENCIALES_JSON)
    if not os.path.isfile(ruta_creds):
        raise FileNotFoundError(
            f"No se encontró '{CREDENCIALES_JSON}'.\n"
            "Colócalo en el mismo directorio que export_stats.py."
        )
    creds = Credentials.from_service_account_file(ruta_creds, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    hoja = sh.worksheet(NOMBRE_HOJA)
    log(f"  Conectado a '{NOMBRE_HOJA}' — Sheet ID: {SHEET_ID}")
    return hoja


# ── Procesamiento de h2test ───────────────────────────────────────────────────
def detectar_grupos(row0: list, row1: list) -> list:
    """
    h2test tiene doble encabezado con celdas fusionadas:
      Fila 1: nombre del curso (solo en la primera columna del grupo; el resto vacío)
      Fila 2: sub-headers por grupo — Identificacion, Nombre, Celular, Email, Avance, [sep], [sep]

    Retorna lista de dicts con la info de cada grupo de columnas.
    """
    posiciones = [(i, v.strip()) for i, v in enumerate(row0) if v.strip()]
    grupos = []
    for j, (col_inicio, nombre) in enumerate(posiciones):
        col_fin = posiciones[j + 1][0] if j + 1 < len(posiciones) else len(row0)
        sub = [
            (i - col_inicio, row1[i].strip().lower())
            for i in range(col_inicio, min(col_fin, len(row1)))
        ]
        offset_id     = next((o for o, h in sub if "identificac" in h), None)
        offset_avance = next((o for o, h in sub if "avance" in h), None)
        grupos.append({
            "nombre":         nombre,
            "col_inicio":     col_inicio,
            "col_fin":        col_fin,
            "offset_id":      offset_id,
            "offset_avance":  offset_avance,
        })
    return grupos


def _cel_grupo(row: list, col_inicio: int, offset) -> str:
    if offset is None:
        return ""
    idx = col_inicio + offset
    return row[idx].strip() if idx < len(row) else ""


def procesar_h2test(all_values: list) -> tuple:
    """
    h2test tiene estructura de doble encabezado:
      Fila 0: nombres de cursos (celdas fusionadas → valor solo en col inicial)
      Fila 1: sub-headers por grupo (Identificacion, Nombre, Celular, Email, Avance, [sep x2])
      Fila 2+: datos — cada fila es un estudiante × curso (grupos paralelos independientes)

    El grupo "SIN CURSO ASIGNADO" no tiene columna Avance → sus filas = SIN MATCH.
    """
    if len(all_values) < 2:
        raise ValueError("La hoja h2test está vacía o tiene menos de 2 filas.")

    grupos = detectar_grupos(all_values[0], all_values[1])
    filas  = all_values[2:]

    cursos_normales = [g for g in grupos if "sin curso" not in g["nombre"].lower()]
    grupo_sin_curso = next((g for g in grupos if "sin curso" in g["nombre"].lower()), None)

    por_curso  = []
    ids_unicos = set()
    avance_0   = 0
    avance_irr = 0

    for g in cursos_normales:
        avances = []
        for row in filas:
            id_val = _cel_grupo(row, g["col_inicio"], g["offset_id"])
            if not id_val:
                continue
            ids_unicos.add(id_val)
            av = _limpiar_porcentaje(_cel_grupo(row, g["col_inicio"], g["offset_avance"]))
            avances.append(av)
            if av == 0.0:
                avance_0 += 1
            if av > 100.0:
                avance_irr += 1

        n = len(avances)
        por_curso.append({
            "curso":       g["nombre"],
            "estudiantes": n,
            "promedio":    round(sum(avances) / n, 2) if n else 0.0,
            "min":         round(min(avances), 2) if avances else 0.0,
            "max":         round(max(avances), 2) if avances else 0.0,
        })

    sin_match = 0
    if grupo_sin_curso and grupo_sin_curso["offset_id"] is not None:
        for row in filas:
            if _cel_grupo(row, grupo_sin_curso["col_inicio"], grupo_sin_curso["offset_id"]):
                sin_match += 1

    anomalias = [
        {"categoria": "SIN MATCH",        "cantidad": sin_match},
        {"categoria": "AVANCE 0%",         "cantidad": avance_0},
        {"categoria": "AVANCE IRREGULAR",  "cantidad": avance_irr},
    ]

    log(f"  Cursos: {len(por_curso)} | SIN MATCH: {sin_match} | AVANCE 0%: {avance_0} | IRREGULAR: {avance_irr}")
    return por_curso, anomalias, len(ids_unicos)


# ── Generación de data.json ────────────────────────────────────────────────────
def generar_json(por_curso: list, anomalias: list, total_estudiantes_unicos: int) -> dict:
    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        "por_curso": por_curso,
        "anomalias": anomalias,
        "totales": {
            "total_cursos": len(por_curso),
            "total_estudiantes_unicos": total_estudiantes_unicos,
        },
    }


def guardar_json(datos: dict) -> None:
    os.makedirs(os.path.dirname(RUTA_DATA_JSON), exist_ok=True)
    with open(RUTA_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    log(f"  data.json generado en: {RUTA_DATA_JSON}")


# ── Git commit y push ──────────────────────────────────────────────────────────
def git_commit_y_push(timestamp: str) -> None:
    ruta_relativa = os.path.join("docs", "dashboard", "data.json")
    pasos = [
        ["git", "add", ruta_relativa],
        ["git", "commit", "-m", f"chore: actualizar estadisticas [{timestamp}]"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in pasos:
        resultado = subprocess.run(
            cmd,
            cwd=PROYECTO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if resultado.returncode != 0:
            stderr = resultado.stderr.strip() or resultado.stdout.strip()
            log(f"ADVERTENCIA git ({' '.join(cmd)}): {stderr}")
            return
        log(f"  git {cmd[1]}: OK")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    try:
        hoja = conectar_hoja()

        log(f"Leyendo hoja '{NOMBRE_HOJA}'...")
        all_values = hoja.get_all_values()
        log(f"  {len(all_values)} filas leídas.")

        por_curso, anomalias, total_unicos = procesar_h2test(all_values)
        log(f"  Estudiantes únicos (Identificacion): {total_unicos}")

        datos = generar_json(por_curso, anomalias, total_unicos)
        guardar_json(datos)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
        log("Ejecutando git commit y push...")
        git_commit_y_push(timestamp)

        log("=" * 60)
        log(f"  Cursos procesados   : {len(por_curso)}")
        log(f"  Anomalías           : {len(anomalias)}")
        log(f"  Archivo generado    : {RUTA_DATA_JSON}")
        log("=" * 60)
        print(f"EXPORT: cursos={len(por_curso)} estado=exito", flush=True)

    except FileNotFoundError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except gspread.exceptions.SpreadsheetNotFound:
        print(
            f"\nERROR: Hoja de cálculo no encontrada.\n"
            f"Comparte el Sheet con el Service Account como Editor:\n"
            f"  q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com\n"
            f"  URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}",
            file=sys.stderr,
        )
        sys.exit(1)
    except gspread.exceptions.WorksheetNotFound:
        print(
            f"\nERROR: No existe la pestaña '{NOMBRE_HOJA}'.\n"
            "Verifica que la pestaña 'h2test' existe en el Sheet de Fundación ROFÉ.",
            file=sys.stderr,
        )
        sys.exit(1)
    except ValueError as e:
        print(f"\nERROR de parseo: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\nERROR inesperado: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
