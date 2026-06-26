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
    posiciones = [(i, ' '.join(v.replace('\xa0', ' ').split()))
                  for i, v in enumerate(row0) if v.strip()]
    grupos = []
    for j, (col_inicio, nombre) in enumerate(posiciones):
        col_fin = posiciones[j + 1][0] if j + 1 < len(posiciones) else len(row0)
        sub = [
            (i - col_inicio, row1[i].strip().lower())
            for i in range(col_inicio, min(col_fin, len(row1)))
        ]
        offset_id     = next((o for o, h in sub if "identificac" in h), None)
        offset_avance = next((o for o, h in sub if "avance" in h), None)
        offset_estado = next((o for o, h in sub if "estado" in h), None)
        offset_email  = next((o for o, h in sub if "email" in h), None)
        grupos.append({
            "nombre":        nombre,
            "col_inicio":    col_inicio,
            "col_fin":       col_fin,
            "offset_id":     offset_id,
            "offset_avance": offset_avance,
            "offset_estado": offset_estado,
            "offset_email":  offset_email,
        })
    return grupos


def _cel_grupo(row: list, col_inicio: int, offset) -> str:
    if offset is None:
        return ""
    idx = col_inicio + offset
    return row[idx].strip() if idx < len(row) else ""


_PALABRAS_MR = ["emprendedoras", "idea a la acci"]

def _es_curso_mr(nombre: str) -> bool:
    n = nombre.lower()
    return any(p in n for p in _PALABRAS_MR)


def _procesar_grupos(filas: list, grupos: list) -> tuple:
    """Procesa un subconjunto de grupos de cursos.
    Retorna (por_curso, emails_unicos, emails_habilitados, avance_0, avance_irr).
    """
    por_curso          = []
    emails_unicos      = set()
    emails_habilitados = set()
    avance_0           = 0
    avance_irr         = 0

    for g in grupos:
        avances = []
        for row in filas:
            id_val = _cel_grupo(row, g["col_inicio"], g["offset_id"])
            if not id_val:
                continue
            email_val = _cel_grupo(row, g["col_inicio"], g.get("offset_email")).lower().strip()
            est_val   = _cel_grupo(row, g["col_inicio"], g.get("offset_estado")).upper()
            if email_val:
                emails_unicos.add(email_val)
                if est_val in ("A", ""):
                    emails_habilitados.add(email_val)
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

    return por_curso, emails_unicos, emails_habilitados, avance_0, avance_irr


def procesar_h2test(all_values: list) -> tuple:
    """
    Separa cursos JC y MR, procesa cada programa independientemente.
    Retorna (pc_jc, pc_mr, anom_jc, anom_mr, n_jc, hab_jc, n_mr, hab_mr, total_db).
    """
    if len(all_values) < 2:
        raise ValueError("La hoja h2test está vacía o tiene menos de 2 filas.")

    grupos = detectar_grupos(all_values[0], all_values[1])
    filas  = all_values[2:]

    cursos_normales = [g for g in grupos if "sin curso" not in g["nombre"].lower()]
    grupo_sin_curso = next((g for g in grupos if "sin curso" in g["nombre"].lower()), None)

    cursos_jc = [g for g in cursos_normales if not _es_curso_mr(g["nombre"])]
    cursos_mr = [g for g in cursos_normales if     _es_curso_mr(g["nombre"])]

    pc_jc, em_jc, eh_jc, av0_jc, avi_jc = _procesar_grupos(filas, cursos_jc)
    pc_mr, em_mr, eh_mr, av0_mr, avi_mr = _procesar_grupos(filas, cursos_mr)

    sin_match        = 0
    emails_sin_curso = set()
    if grupo_sin_curso and grupo_sin_curso["offset_id"] is not None:
        offset_em_sc = grupo_sin_curso.get("offset_email")
        for row in filas:
            if _cel_grupo(row, grupo_sin_curso["col_inicio"], grupo_sin_curso["offset_id"]):
                sin_match += 1
                em = _cel_grupo(row, grupo_sin_curso["col_inicio"], offset_em_sc).lower().strip()
                if em:
                    emails_sin_curso.add(em)

    total_db = len(em_jc | em_mr | emails_sin_curso)

    anom_jc = [
        {"categoria": "SIN MATCH",        "cantidad": sin_match},
        {"categoria": "AVANCE 0%",         "cantidad": av0_jc},
        {"categoria": "AVANCE IRREGULAR",  "cantidad": avi_jc},
    ]
    anom_mr = [
        {"categoria": "AVANCE 0%",         "cantidad": av0_mr},
        {"categoria": "AVANCE IRREGULAR",  "cantidad": avi_mr},
    ]

    log(f"  JC: {len(pc_jc)} cursos | {len(em_jc)} únicos | Hab: {len(eh_jc)} | SIN MATCH: {sin_match} | AVANCE 0%: {av0_jc} | IRR: {avi_jc}")
    log(f"  MR: {len(pc_mr)} cursos | {len(em_mr)} únicos | Hab: {len(eh_mr)} | AVANCE 0%: {av0_mr} | IRR: {avi_mr}")
    log(f"  Total DB: {total_db}")
    return (pc_jc, pc_mr, anom_jc, anom_mr,
            len(em_jc), len(eh_jc),
            len(em_mr), len(eh_mr),
            total_db)


# ── Generación de data.json ────────────────────────────────────────────────────
def generar_json(pc_jc: list, pc_mr: list,
                 anom_jc: list, anom_mr: list,
                 n_jc: int, hab_jc: int,
                 n_mr: int, hab_mr: int,
                 total_db: int) -> dict:
    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        # Top-level = solo Jóvenes creaTIvos (dashboard principal)
        "por_curso": pc_jc,
        "anomalias": anom_jc,
        "totales": {
            "total_cursos":             len(pc_jc),
            "total_estudiantes_unicos": n_jc,
            "total_habilitados":        hab_jc,
            "total_db":                 total_db,
        },
        # Subsección exclusiva para el panel Mujeres ROFÉ
        "mr": {
            "por_curso": pc_mr,
            "anomalias": anom_mr,
            "totales": {
                "total_cursos":             len(pc_mr),
                "total_estudiantes_unicos": n_mr,
                "total_habilitados":        hab_mr,
            },
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

        pc_jc, pc_mr, anom_jc, anom_mr, n_jc, hab_jc, n_mr, hab_mr, total_db = procesar_h2test(all_values)

        datos = generar_json(pc_jc, pc_mr, anom_jc, anom_mr, n_jc, hab_jc, n_mr, hab_mr, total_db)
        guardar_json(datos)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
        log("Ejecutando git commit y push...")
        git_commit_y_push(timestamp)

        log("=" * 60)
        log(f"  Cursos JC           : {len(pc_jc)}")
        log(f"  Cursos MR           : {len(pc_mr)}")
        log(f"  Archivo generado    : {RUTA_DATA_JSON}")
        log("=" * 60)
        print(f"EXPORT: cursos_jc={len(pc_jc)} cursos_mr={len(pc_mr)} estado=exito", flush=True)

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
