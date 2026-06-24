# -*- coding: utf-8 -*-
"""
export_asistencia.py — Lee la pestaña "asistencias" del Sheet de registro manual
y genera docs/asistencia/data.json con conteos por sesión (sin PII).

Fundación ROFÉ | Jóvenes creaTIvos

Estructura de la hoja (2 filas de encabezado):
  Fila 1: nombre del módulo (celda fusionada — solo la primera col del grupo tiene valor)
  Fila 2: sub-encabezados — Nombre, Apellido, Correo electrónico, Identificación
  Fila 3+: datos de asistentes (un estudiante por fila dentro de cada grupo de 4 columnas)

Uso:
    python export_asistencia.py
    python export_asistencia.py --segmento "Logica-Nivel 2-2026"
"""

import argparse
import io
import json
import os
import subprocess
import sys
from datetime import datetime

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import gspread
from google.oauth2.service_account import Credentials

# ── Configuración ─────────────────────────────────────────────────────────────
SHEET_ID          = "1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8"
NOMBRE_HOJA       = "asistencias"
CREDENCIALES_JSON = "credenciales_service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_DATA_JSON    = os.path.join(PROYECTO_ROOT, "docs", "asistencia", "data.json")

# Número de columnas por módulo (Nombre, Apellido, Correo, Identificación)
COLS_POR_MODULO = 4


# ── Utilidades ─────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[export-asistencia] {msg}", flush=True)


def _cel(row: list, idx: int) -> str:
    return row[idx].strip() if idx < len(row) else ""


def _es_estudiante(row: list, col_inicio: int) -> bool:
    """Un estudiante existe si al menos uno de sus campos no está vacío."""
    return any(
        _cel(row, col_inicio + offset)
        for offset in range(COLS_POR_MODULO)
    )


# ── Google Sheets ──────────────────────────────────────────────────────────────
def conectar_hoja() -> gspread.Worksheet:
    log("Conectando a Google Sheets...")
    ruta_creds = os.path.join(DIRECTORIO_SCRIPT, CREDENCIALES_JSON)
    if not os.path.isfile(ruta_creds):
        raise FileNotFoundError(
            f"No se encontró '{CREDENCIALES_JSON}'.\n"
            "Colócalo en el mismo directorio que export_asistencia.py.\n"
            "Y comparte el Sheet con el Service Account como Lector:\n"
            "  q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com"
        )
    creds = Credentials.from_service_account_file(ruta_creds, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    hoja = sh.worksheet(NOMBRE_HOJA)
    log(f"  Conectado a '{NOMBRE_HOJA}' — Sheet ID: {SHEET_ID}")
    return hoja


# ── Parseo del multi-encabezado ────────────────────────────────────────────────
def detectar_modulos(row0: list) -> list:
    """
    Escanea la fila 1 para detectar los módulos.
    Las celdas fusionadas en Sheets devuelven el valor solo en la primera columna
    del grupo; las siguientes aparecen como "".

    Devuelve lista de dicts: [{"nombre": str, "col_inicio": int}, ...]
    """
    modulos = []
    for i, celda in enumerate(row0):
        if celda.strip():
            modulos.append({"nombre": celda.strip(), "col_inicio": i})
    return modulos


def procesar_asistencias(all_values: list) -> tuple:
    """
    Parsea la hoja de asistencias con estructura de doble encabezado.
    Retorna (sesiones, totales) — sin PII, solo conteos.

    sesiones = [{"nombre": "Bienvenida", "asistentes": 45}, ...]
    """
    if len(all_values) < 2:
        raise ValueError("La hoja 'asistencias' tiene menos de 2 filas — sin datos.")

    row0 = all_values[0]   # fila 1: nombres de módulos
    # row1 = all_values[1] # fila 2: sub-encabezados (no la necesitamos para parsear)
    filas_datos = all_values[2:]

    modulos = detectar_modulos(row0)
    if not modulos:
        raise ValueError(
            "No se detectaron módulos en la fila 1.\n"
            "Verifica que la fila 1 contiene los nombres de los módulos."
        )

    log(f"  Módulos detectados ({len(modulos)}): {[m['nombre'] for m in modulos]}")

    sesiones = []
    correos_unicos = set()
    ids_unicos = set()

    for idx, modulo in enumerate(modulos):
        col_inicio = modulo["col_inicio"]
        count = 0

        for row in filas_datos:
            if not _es_estudiante(row, col_inicio):
                continue

            correo = _cel(row, col_inicio + 2)
            id_num = _cel(row, col_inicio + 3)

            count += 1
            if correo:
                correos_unicos.add(correo.lower())
            if id_num:
                ids_unicos.add(id_num)

        sesiones.append({
            "nombre":     modulo["nombre"],
            "asistentes": count,
        })

        log(f"    {modulo['nombre']}: {count} asistentes")

    # Sesión con más y menos asistentes
    sesiones_con_datos = [s for s in sesiones if s["asistentes"] > 0]
    max_sesion = max(sesiones_con_datos, key=lambda s: s["asistentes"], default=None)
    min_sesion = min(sesiones_con_datos, key=lambda s: s["asistentes"], default=None)

    total_registros = sum(s["asistentes"] for s in sesiones)
    unicos_id       = len(ids_unicos)

    # Retención: asistentes de la última sesión sobre la primera
    retencion = None
    if len(sesiones_con_datos) >= 2:
        primera  = sesiones_con_datos[0]["asistentes"]
        ultima   = sesiones_con_datos[-1]["asistentes"]
        retencion = round(ultima / primera * 100, 1) if primera else None

    # Promedio de sesiones por estudiante (basado en IDs únicos)
    promedio_ses = round(total_registros / unicos_id, 1) if unicos_id else None

    totales = {
        "total_sesiones":                   len(sesiones),
        "total_registros":                  total_registros,
        "estudiantes_unicos_id":            unicos_id,
        "porcentaje_retencion":             retencion,
        "promedio_sesiones_por_estudiante": promedio_ses,
        "sesion_max": {"nombre": max_sesion["nombre"], "asistentes": max_sesion["asistentes"]} if max_sesion else None,
        "sesion_min": {"nombre": min_sesion["nombre"], "asistentes": min_sesion["asistentes"]} if min_sesion else None,
    }

    return sesiones, totales


# ── Generación de data.json ────────────────────────────────────────────────────
def generar_json(sesiones: list, totales: dict, segmento: str) -> dict:
    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        "segmento":  segmento,
        "sesiones":  sesiones,
        "totales":   totales,
    }


def guardar_json(datos: dict) -> None:
    os.makedirs(os.path.dirname(RUTA_DATA_JSON), exist_ok=True)
    with open(RUTA_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    log(f"  data.json generado en: {RUTA_DATA_JSON}")


# ── Git commit y push ──────────────────────────────────────────────────────────
def git_commit_y_push(timestamp: str) -> None:
    ruta_relativa = os.path.join("docs", "asistencia", "data.json")
    pasos = [
        ["git", "add", ruta_relativa],
        ["git", "commit", "-m", f"chore: actualizar asistencias [{timestamp}]"],
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


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta asistencias a data.json")
    parser.add_argument("--segmento", default="Logica-Nivel 2-2026",
                        help="Nombre del segmento (default: Logica-Nivel 2-2026)")
    args = parser.parse_args()

    try:
        hoja = conectar_hoja()

        log(f"Leyendo hoja '{NOMBRE_HOJA}'...")
        all_values = hoja.get_all_values()
        log(f"  {len(all_values)} filas leídas.")

        sesiones, totales = procesar_asistencias(all_values)

        datos = generar_json(sesiones, totales, args.segmento)
        guardar_json(datos)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
        log("Ejecutando git commit y push...")
        git_commit_y_push(timestamp)

        log("=" * 60)
        log(f"  Segmento            : {args.segmento}")
        log(f"  Sesiones procesadas : {len(sesiones)}")
        log(f"  Total registros     : {totales['total_registros']}")
        log(f"  Estudiantes únicos  : {totales['estudiantes_unicos_id']} (por ID)")
        log(f"  Retención           : {totales['porcentaje_retencion']}%")
        log(f"  Archivo generado    : {RUTA_DATA_JSON}")
        log("=" * 60)
        print(f"EXPORT: sesiones={len(sesiones)} registros={totales['total_registros']} estado=exito", flush=True)

    except FileNotFoundError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except gspread.exceptions.SpreadsheetNotFound:
        print(
            f"\nERROR: Sheet no encontrado.\n"
            f"Comparte el Sheet con el Service Account como Lector:\n"
            f"  q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com\n"
            f"  URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}",
            file=sys.stderr,
        )
        sys.exit(1)
    except gspread.exceptions.WorksheetNotFound:
        print(
            f"\nERROR: No existe la pestaña '{NOMBRE_HOJA}'.\n"
            "Verifica el nombre exacto de la pestaña (sensible a mayúsculas).",
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
