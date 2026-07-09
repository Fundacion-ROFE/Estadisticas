# -*- coding: utf-8 -*-
"""
export_retirados.py — Lee la pestaña "Retirados" del Google Sheet y genera
docs/retirados/data.json con estadísticas agregadas (sin PII).

Fundación ROFÉ | Jóvenes creaTIvos
"""

import io
import json
import os
import subprocess
import sys
from collections import Counter
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
NOMBRE_HOJA       = "Retirados"
CREDENCIALES_JSON = "credenciales_service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_DATA_JSON    = os.path.join(PROYECTO_ROOT, "docs", "retirados", "data.json")
RUTA_EXCLUSIONES  = os.path.join(PROYECTO_ROOT, "tools", "exclusiones_prueba.json")


# ── Utilidades ────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[export-retirados] {msg}", flush=True)


def _cargar_exclusiones() -> set:
    """Cédulas de perfiles de prueba (tools/exclusiones_prueba.json, gitignoreado)."""
    ceds = set()
    if os.path.isfile(RUTA_EXCLUSIONES):
        try:
            with open(RUTA_EXCLUSIONES, encoding="utf-8") as f:
                for p in json.load(f).get("perfiles", []):
                    ced = "".join(ch for ch in str(p.get("cedula", "")) if ch.isdigit())
                    if ced:
                        ceds.add(ced)
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: exclusiones ilegibles ({e}) — no se excluye nada")
    return ceds


# ── Google Sheets ─────────────────────────────────────────────────────────────
def conectar_hoja() -> gspread.Worksheet:
    log("Conectando a Google Sheets...")
    ruta_creds = os.path.join(DIRECTORIO_SCRIPT, CREDENCIALES_JSON)
    if not os.path.isfile(ruta_creds):
        raise FileNotFoundError(
            f"No se encontró '{CREDENCIALES_JSON}'.\n"
            "Colócalo en el mismo directorio que export_retirados.py."
        )
    creds = Credentials.from_service_account_file(ruta_creds, scopes=SCOPES)
    gc = gspread.authorize(creds)
    hoja = gc.open_by_key(SHEET_ID).worksheet(NOMBRE_HOJA)
    log(f"  Conectado a '{NOMBRE_HOJA}' — Sheet ID: {SHEET_ID}")
    return hoja


# ── Procesamiento (solo agregados — NUNCA PII) ────────────────────────────────
def procesar_retirados(registros: list[dict]) -> dict:
    """Agrega los registros de retiro. El JSON público solo lleva conteos."""
    tipos     = Counter()
    causas    = Counter()
    programas = Counter()
    meses     = Counter()

    for r in registros:
        tipo = str(r.get("Tipo", "")).strip() or "Sin tipo"
        tipos[tipo] += 1
        causas[str(r.get("Causa", "")).strip() or "Sin causa"] += 1
        programas[str(r.get("Programa", "")).strip() or "Sin programa"] += 1
        fecha = str(r.get("FechaCancelacion", "")).strip()
        meses[fecha[:7] if len(fecha) >= 7 else "sin fecha"] += 1

    total = len(registros)
    log(f"  Total retirados: {total} | Tipos: {dict(tipos)}")

    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        "totales": {
            "total_retirados": total,
            "cancelados":      tipos.get("Cancelado", 0),
            "desertores":      tipos.get("Desertor", 0),
            "aplazados":       tipos.get("Aplazado", 0),
        },
        "por_tipo": [
            {"tipo": t, "cantidad": n} for t, n in tipos.most_common()
        ],
        "por_causa": [
            {"causa": c, "cantidad": n} for c, n in causas.most_common()
        ],
        "por_programa": [
            {"programa": p, "cantidad": n} for p, n in programas.most_common()
        ],
        "por_mes": [
            {"mes": m, "cantidad": n} for m, n in sorted(meses.items())
        ],
    }


def guardar_json(datos: dict) -> None:
    os.makedirs(os.path.dirname(RUTA_DATA_JSON), exist_ok=True)
    with open(RUTA_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    log(f"  data.json generado en: {RUTA_DATA_JSON}")


# ── Git commit y push ──────────────────────────────────────────────────────────
def git_commit_y_push(timestamp: str) -> None:
    pasos = [
        ["git", "add", os.path.join("docs", "retirados", "data.json")],
        ["git", "commit", "-m", f"chore: actualizar retirados [{timestamp}]"],
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


# ── Lectura tolerante ─────────────────────────────────────────────────────────
def leer_registros(ws) -> list:
    """get_all_records() tolerante: ignora columnas con encabezado vacío o duplicado,
    para que una fórmula suelta en la fila 1 no tumbe el pipeline."""
    vals = ws.get_all_values()
    if not vals:
        return []
    vistos, cols = set(), []
    for i, h in enumerate(vals[0]):
        h = str(h).strip()
        if h and h not in vistos:
            vistos.add(h)
            cols.append((i, h))
    return [{h: (fila[i] if i < len(fila) else "") for i, h in cols} for fila in vals[1:]]


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Exporta retirados a data.json")
    parser.add_argument("--sin-push", action="store_true",
                        help="Genera el JSON sin git commit/push (pruebas)")
    args = parser.parse_args()

    try:
        hoja = conectar_hoja()

        log(f"Leyendo hoja '{NOMBRE_HOJA}'...")
        registros = leer_registros(hoja)
        log(f"  {len(registros)} registros leídos.")
        if not registros:
            raise ValueError(f"La pestaña '{NOMBRE_HOJA}' está vacía.")

        excl = _cargar_exclusiones()
        if excl:
            antes = len(registros)
            registros = [
                r for r in registros
                if "".join(ch for ch in str(r.get("Identificacion", "")) if ch.isdigit())
                not in excl
            ]
            if antes - len(registros):
                log(f"  Exclusión de pruebas: {antes - len(registros)} registros quitados")

        datos = procesar_retirados(registros)
        guardar_json(datos)

        if args.sin_push:
            log("Modo --sin-push: no se toca git.")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
            log("Ejecutando git commit y push...")
            git_commit_y_push(timestamp)

        t = datos["totales"]
        log("=" * 60)
        log(f"  Total retirados : {t['total_retirados']}")
        log(f"  Cancelados      : {t['cancelados']}")
        log(f"  Desertores      : {t['desertores']}")
        log(f"  Aplazados       : {t['aplazados']}")
        log(f"  Archivo         : {RUTA_DATA_JSON}")
        log("=" * 60)
        print(
            f"EXPORT: retirados={t['total_retirados']} "
            f"cancelados={t['cancelados']} estado=exito",
            flush=True,
        )

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
            "Corre primero: python q10_to_sheets.py --grupo retirados",
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
