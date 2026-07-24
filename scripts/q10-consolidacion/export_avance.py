# -*- coding: utf-8 -*-
"""
export_avance.py — Lee la pestaña "Avance" del Sheet manual y genera
docs/avance/data.json con estadísticas de avance por curso (sin PII).

Fundación ROFÉ | Jóvenes creaTIvos

Estructura de la hoja (2 filas de encabezado):
  Fila 1: nombre del curso (celda fusionada — valor solo en primera col del grupo)
          Los primeros grupos sin nombre se cuentan como SIN ETIQUETA.
  Fila 2: sub-headers por grupo — Número identificación, Celular, Email, Porcentaje progreso, [sep]
  Fila 3+: datos (un estudiante por fila dentro de cada grupo de 5 columnas)

Uso:
    python export_avance.py
    python export_avance.py --segmento "Logica-Nivel 2-2026"
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

# ── Configuración ──────────────────────────────────────────────────────────────
SHEET_ID          = "1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8"
NOMBRE_HOJA       = "Avance"
CREDENCIALES_JSON = "credenciales_service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_DATA_JSON    = os.path.join(PROYECTO_ROOT, "docs", "avance", "data.json")


# ── Utilidades ─────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[export-avance] {msg}", flush=True)


def _limpiar_porcentaje(valor: str) -> float:
    limpio = valor.strip().replace("%", "").replace(",", ".").strip()
    if not limpio:
        return 0.0
    try:
        return round(float(limpio), 2)
    except ValueError:
        return 0.0


def _cel(row: list, idx: int) -> str:
    return row[idx].strip() if idx is not None and idx < len(row) else ""


# ── Conexión ───────────────────────────────────────────────────────────────────
def conectar_hoja() -> gspread.Worksheet:
    log("Conectando a Google Sheets...")
    ruta_creds = os.path.join(DIRECTORIO_SCRIPT, CREDENCIALES_JSON)
    if not os.path.isfile(ruta_creds):
        raise FileNotFoundError(
            f"No se encontró '{CREDENCIALES_JSON}'.\n"
            "Colócalo en el mismo directorio que export_avance.py."
        )
    creds = Credentials.from_service_account_file(ruta_creds, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    hoja = sh.worksheet(NOMBRE_HOJA)
    log(f"  Conectado a '{NOMBRE_HOJA}' — Sheet ID: {SHEET_ID}")
    return hoja


# ── Parseo de grupos ───────────────────────────────────────────────────────────
def detectar_grupos(row0: list, row1: list) -> list:
    """
    Detecta grupos de columnas a partir de los sub-headers (fila 2).
    Cada grupo comienza donde aparece 'identificac' o 'número id' en row1.
    El nombre del curso se toma de row0 en la misma columna.
    """
    grupos = []
    for i, h in enumerate(row1):
        h_lower = h.strip().lower()
        if "identificac" in h_lower or "número id" in h_lower or "numero id" in h_lower:
            nombre = row0[i].strip() if i < len(row0) else ""
            grupos.append({"nombre": nombre, "col_inicio": i})

    for j, g in enumerate(grupos):
        col_fin = grupos[j + 1]["col_inicio"] if j + 1 < len(grupos) else len(row0)
        sub = [
            (i - g["col_inicio"], row1[i].strip().lower())
            for i in range(g["col_inicio"], min(col_fin, len(row1)))
        ]
        g["col_fin"]        = col_fin
        g["offset_id"]      = 0
        g["offset_avance"]  = next((o for o, h in sub if "progreso" in h or "porcentaje" in h or "avance" in h), None)
        g["offset_email"]   = next((o for o, h in sub if "email" in h or "correo" in h), None)

    return grupos


# ── Procesamiento ──────────────────────────────────────────────────────────────
def procesar_avance(all_values: list) -> tuple:
    """
    Retorna (por_curso, totales, anomalias) — sin PII.

    por_curso = [
      {"nombre": "Bienvenida", "estudiantes": N, "promedio": 87.3, "min": 0.0, "max": 100.0}
    ]
    """
    if len(all_values) < 2:
        raise ValueError("La pestaña 'Avance' tiene menos de 2 filas.")

    grupos = detectar_grupos(all_values[0], all_values[1])
    filas  = all_values[2:]

    nombrados   = [g for g in grupos if g["nombre"]]
    sin_nombre  = [g for g in grupos if not g["nombre"]]

    log(f"  Grupos detectados: {len(grupos)} total — {len(nombrados)} nombrados, {len(sin_nombre)} sin etiqueta")
    log(f"  Cursos: {[g['nombre'] for g in nombrados]}")

    por_curso    = []
    ids_unicos   = set()
    sin_progreso = 0
    avance_0     = 0
    avance_irr   = 0

    for g in nombrados:
        avances = []
        for row in filas:
            id_val = _cel(row, g["col_inicio"] + g["offset_id"])
            if not id_val:
                continue
            ids_unicos.add(id_val)
            av_raw = _cel(row, g["col_inicio"] + g["offset_avance"]) if g["offset_avance"] is not None else ""
            if not av_raw.strip():
                sin_progreso += 1
                # No se incluye en avances para no distorsionar el promedio
            else:
                av = _limpiar_porcentaje(av_raw)
                avances.append(av)
                if av == 0.0:
                    avance_0 += 1
                if av > 100.0:
                    avance_irr += 1

        n = len(avances)
        # Aprobado = avance >= 100 (misma regla que export_aprobacion.py; hay casos de 101)
        aprobados = sum(1 for av in avances if av >= 100.0)
        por_curso.append({
            "nombre":         g["nombre"],
            "estudiantes":    n,
            "aprobados":      aprobados,
            "pct_aprobados":  round(100 * aprobados / n, 1) if n else 0.0,
            "promedio":       round(sum(avances) / n, 2) if n else 0.0,
            "min":            round(min(avances), 2) if avances else 0.0,
            "max":            round(max(avances), 2) if avances else 0.0,
        })
        log(f"    {g['nombre']}: {n} estudiantes, promedio {por_curso[-1]['promedio']}%, "
            f"aprobados {aprobados} ({por_curso[-1]['pct_aprobados']}%)")

    total_registros = sum(c["estudiantes"] for c in por_curso)
    promedio_general = (
        round(sum(c["promedio"] * c["estudiantes"] for c in por_curso) / total_registros, 2)
        if total_registros else 0.0
    )

    totales = {
        "total_cursos":           len(por_curso),
        "total_registros":        total_registros,
        "estudiantes_unicos_id":  len(ids_unicos),
        "promedio_general":       promedio_general,
        "total_aprobados":        sum(c["aprobados"] for c in por_curso),
    }

    anomalias = [
        {"categoria": "SIN PROGRESO",     "cantidad": sin_progreso},
        {"categoria": "AVANCE 0%",        "cantidad": avance_0},
        {"categoria": "AVANCE IRREGULAR", "cantidad": avance_irr},
    ]

    return por_curso, totales, anomalias


# ── Generación de data.json ────────────────────────────────────────────────────
def generar_json(por_curso: list, totales: dict, anomalias: list, segmento: str) -> dict:
    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        "segmento":  segmento,
        "por_curso": por_curso,
        "totales":   totales,
        "anomalias": anomalias,
    }


def guardar_json(datos: dict) -> None:
    os.makedirs(os.path.dirname(RUTA_DATA_JSON), exist_ok=True)
    with open(RUTA_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    log(f"  data.json generado en: {RUTA_DATA_JSON}")


# ── Git commit y push ──────────────────────────────────────────────────────────
def git_commit_y_push(timestamp: str) -> bool:
    """Retorna True si el push salió bien (o no había nada que publicar), False si falló."""
    ruta_relativa = os.path.join("docs", "avance", "data.json")

    try:
        resultado_status = subprocess.run(
            ["git", "status", "--porcelain", "--", ruta_relativa],
            cwd=PROYECTO_ROOT, capture_output=True, text=True, encoding="utf-8",
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        log("ERROR git (status --porcelain): timeout tras 180s")
        return False
    if resultado_status.returncode != 0:
        stderr = resultado_status.stderr.strip() or resultado_status.stdout.strip()
        log(f"ERROR git (status --porcelain): {stderr}")
        return False
    if not resultado_status.stdout.strip():
        log("  git: sin cambios, no hay nada que publicar.")
        return True

    pasos = [
        ["git", "add", ruta_relativa],
        ["git", "commit", "-m", f"chore: actualizar avance manual [{timestamp}]"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in pasos:
        try:
            resultado = subprocess.run(
                cmd, cwd=PROYECTO_ROOT, capture_output=True, text=True, encoding="utf-8",
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            log(f"ERROR git ({' '.join(cmd)}): timeout tras 180s")
            return False
        if resultado.returncode != 0:
            stderr = resultado.stderr.strip() or resultado.stdout.strip()
            log(f"ERROR git ({' '.join(cmd)}): {stderr}")
            return False
        log(f"  git {cmd[1]}: OK")
    return True


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta Avance manual a data.json")
    parser.add_argument("--segmento", default="Logica-Nivel 2-2026",
                        help="Nombre del segmento")
    parser.add_argument("--sin-push", action="store_true",
                        help="Genera el JSON sin git commit/push (pruebas)")
    args = parser.parse_args()

    try:
        hoja = conectar_hoja()

        log(f"Leyendo hoja '{NOMBRE_HOJA}'...")
        all_values = hoja.get_all_values()
        log(f"  {len(all_values)} filas leídas.")

        por_curso, totales, anomalias = procesar_avance(all_values)

        datos = generar_json(por_curso, totales, anomalias, args.segmento)
        guardar_json(datos)

        if args.sin_push:
            log("Modo --sin-push: no se toca git.")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
            log("Ejecutando git commit y push...")
            if not git_commit_y_push(timestamp):
                print(
                    f"EXPORT: cursos={len(por_curso)} promedio={totales['promedio_general']}% "
                    f"estado=error detalle=git_push_fallido",
                    flush=True,
                )
                sys.exit(1)

        log("=" * 60)
        log(f"  Segmento            : {args.segmento}")
        log(f"  Cursos procesados   : {len(por_curso)}")
        log(f"  Total registros     : {totales['total_registros']}")
        log(f"  Estudiantes únicos  : {totales['estudiantes_unicos_id']} (por ID)")
        log(f"  Promedio general    : {totales['promedio_general']}%")
        log(f"  Archivo generado    : {RUTA_DATA_JSON}")
        log("=" * 60)
        print(f"EXPORT: cursos={len(por_curso)} promedio={totales['promedio_general']}% estado=exito", flush=True)

    except FileNotFoundError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except gspread.exceptions.SpreadsheetNotFound:
        print(
            f"\nERROR: Sheet no encontrado. Comparte con el Service Account como Viewer:\n"
            f"  q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com\n"
            f"  URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}",
            file=sys.stderr,
        )
        sys.exit(1)
    except gspread.exceptions.WorksheetNotFound:
        print(
            f"\nERROR: No existe la pestaña '{NOMBRE_HOJA}'.",
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
