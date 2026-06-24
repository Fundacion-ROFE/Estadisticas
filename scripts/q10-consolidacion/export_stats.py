# -*- coding: utf-8 -*-
"""
export_stats.py — Lee la pestaña "estadísticas" del Google Sheet de h2test
y genera docs/dashboard/data.json con estadísticas agregadas (sin datos PII).

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
NOMBRE_HOJA       = "estadísticas"
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


def _normalizar(s: str) -> str:
    return (
        s.strip().lower()
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ü", "u")
        .replace("ñ", "n")
    )


def _limpiar_porcentaje(valor: str) -> float:
    limpio = valor.strip().replace("%", "").replace(",", ".").strip()
    if not limpio:
        return 0.0
    try:
        return round(float(limpio), 2)
    except ValueError:
        return 0.0


def _limpiar_entero(valor: str) -> int:
    limpio = valor.strip().replace(",", "").replace(".", "")
    if not limpio:
        return 0
    try:
        return int(limpio)
    except ValueError:
        return 0


def _celda(row: list, idx: int) -> str:
    if idx is None or idx >= len(row):
        return ""
    return row[idx]


def _es_fila_vacia(row: list) -> bool:
    return all(c.strip() == "" for c in row)


def _es_header_cursos(row: list) -> bool:
    celdas = [c.strip() for c in row if c.strip()]
    if len(celdas) < 3:
        return False
    return (
        _normalizar(celdas[0]) == "curso"
        and "estudiantes" in _normalizar(" ".join(celdas))
    )


def _es_header_anomalias(row: list) -> bool:
    celdas = [c.strip() for c in row if c.strip()]
    if len(celdas) < 2:
        return False
    return (
        _normalizar(celdas[0]) == "categoria"
        and "cantidad" in _normalizar(" ".join(celdas))
    )


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


# ── Parseo de tablas ──────────────────────────────────────────────────────────
def parsear_tablas(all_values: list) -> tuple:
    """
    Detecta ambas tablas escaneando las celdas de encabezado.
    No depende de posiciones fijas de fila — funciona si se agregan cursos.
    """
    curso_header_idx     = None
    anomalias_header_idx = None

    for i, row in enumerate(all_values):
        if _es_header_cursos(row) and curso_header_idx is None:
            curso_header_idx = i
            log(f"  Tabla POR CURSO detectada en fila {i + 1}.")
        if _es_header_anomalias(row) and anomalias_header_idx is None:
            anomalias_header_idx = i
            log(f"  Tabla ANOMALÍAS detectada en fila {i + 1}.")

    if curso_header_idx is None:
        raise ValueError(
            "No se encontró la cabecera de la tabla POR CURSO.\n"
            "Verifica que la hoja 'estadísticas' existe y contiene 'Curso | Estudiantes | Promedio %'."
        )
    if anomalias_header_idx is None:
        raise ValueError(
            "No se encontró la cabecera de la tabla ANOMALÍAS.\n"
            "Verifica que la hoja contiene 'Categoría | Cantidad'."
        )

    # Mapear columnas de POR CURSO por nombre
    col_map = {
        _normalizar(c): j
        for j, c in enumerate(all_values[curso_header_idx])
        if c.strip()
    }
    col_curso       = col_map.get("curso")
    col_estudiantes = col_map.get("estudiantes")
    col_promedio    = col_map.get("promedio %")
    col_min         = col_map.get("min %")
    col_max         = col_map.get("max %")

    faltantes = [
        nombre
        for nombre, idx in [
            ("Curso", col_curso), ("Estudiantes", col_estudiantes),
            ("Promedio %", col_promedio), ("Mín %", col_min), ("Máx %", col_max),
        ]
        if idx is None
    ]
    if faltantes:
        raise ValueError(f"Columnas no encontradas en POR CURSO: {faltantes}")

    # Recolectar filas POR CURSO (detener al llegar a la tabla de anomalías)
    por_curso = []
    for i in range(curso_header_idx + 1, len(all_values)):
        if i == anomalias_header_idx:
            break
        row = all_values[i]
        if _es_fila_vacia(row):
            continue
        nombre_curso = _celda(row, col_curso).strip()
        est_val      = _celda(row, col_estudiantes).strip()
        # Saltar filas de título como "ANOMALÍAS" que no tienen datos numéricos
        if not nombre_curso or not est_val:
            continue
        por_curso.append({
            "curso":       nombre_curso,
            "estudiantes": _limpiar_entero(est_val),
            "promedio":    _limpiar_porcentaje(_celda(row, col_promedio)),
            "min":         _limpiar_porcentaje(_celda(row, col_min)),
            "max":         _limpiar_porcentaje(_celda(row, col_max)),
        })

    # Mapear columnas de ANOMALÍAS por nombre
    col_map_a = {
        _normalizar(c): j
        for j, c in enumerate(all_values[anomalias_header_idx])
        if c.strip()
    }
    col_categoria = col_map_a.get("categoria")
    col_cantidad  = col_map_a.get("cantidad")

    if col_categoria is None or col_cantidad is None:
        raise ValueError("Columnas 'Categoría'/'Cantidad' no encontradas en ANOMALÍAS.")

    # Recolectar filas ANOMALÍAS — cortar en la primera fila vacía tras recoger datos
    # (el Sheet tiene RESUMEN GENERAL debajo separado por una fila vacía)
    anomalias = []
    for i in range(anomalias_header_idx + 1, len(all_values)):
        row = all_values[i]
        if _es_fila_vacia(row):
            if anomalias:
                break
            continue
        cat_val = _celda(row, col_categoria).strip()
        if not cat_val:
            continue
        anomalias.append({
            "categoria": cat_val,
            "cantidad":  _limpiar_entero(_celda(row, col_cantidad)),
        })

    log(f"  POR CURSO: {len(por_curso)} cursos | ANOMALÍAS: {len(anomalias)} categorías")
    return por_curso, anomalias


def parsear_resumen_general(all_values: list) -> dict:
    """
    Lee el bloque RESUMEN GENERAL (Métrica | Valor) de la hoja estadísticas.
    Devuelve un dict con las métricas normalizadas como claves.
    """
    in_bloque = False
    resultado = {}
    for row in all_values:
        celdas = [c.strip() for c in row]
        celdas_nv = [c for c in celdas if c]
        if not celdas_nv:
            continue
        primera = _normalizar(celdas_nv[0])
        if primera in ("resumen general", "metrica"):
            in_bloque = True
            continue
        if in_bloque and len(celdas_nv) >= 2:
            resultado[_normalizar(celdas_nv[0])] = celdas_nv[1]
    return resultado


# ── Generación de data.json ────────────────────────────────────────────────────
def generar_json(por_curso: list, anomalias: list, resumen: dict) -> dict:
    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        "por_curso": por_curso,
        "anomalias": anomalias,
        "totales": {
            "total_cursos": len(por_curso),
            # "Estudiantes únicos" normaliza a "estudiantes unicos"
            "total_estudiantes_unicos": _limpiar_entero(
                resumen.get("estudiantes unicos", "0")
            ),
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

        log("Leyendo hoja 'estadísticas'...")
        all_values = hoja.get_all_values()
        log(f"  {len(all_values)} filas leídas.")

        por_curso, anomalias = parsear_tablas(all_values)
        resumen = parsear_resumen_general(all_values)
        log(f"  Estudiantes únicos (RESUMEN GENERAL): {resumen.get('estudiantes unicos', 'no encontrado')}")

        datos = generar_json(por_curso, anomalias, resumen)
        guardar_json(datos)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
        log("Ejecutando git commit y push...")
        git_commit_y_push(timestamp)

        filas_cursos = len(por_curso)
        log("=" * 60)
        log(f"  Cursos procesados   : {filas_cursos}")
        log(f"  Anomalías procesadas: {len(anomalias)}")
        log(f"  Archivo generado    : {RUTA_DATA_JSON}")
        log("=" * 60)
        print(f"EXPORT: filas_cursos={filas_cursos} estado=exito", flush=True)

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
            "Créala manualmente en la hoja de cálculo.",
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
