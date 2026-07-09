# -*- coding: utf-8 -*-
"""
export_retirados.py — Lee la pestaña "Retirados" del Google Sheet y genera
docs/retirados/data.json con estadísticas agregadas (sin PII).

Fundación ROFÉ | Jóvenes creaTIvos
"""

import io
import json
import os
import re
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
RUTA_COHORTE      = os.path.join(PROYECTO_ROOT, "tools", "cohorte_2026.json")
RUTA_LEDGER       = os.path.join(PROYECTO_ROOT, "tools", "aprobacion_ledger.json")

# Ruta de aprendizaje 2026 de Jóvenes creaTIvos, en orden cronológico. La etapa de
# retiro = último curso de esta ruta con avance >= 100 en el ledger. Nombres deben
# coincidir con las claves del ledger (norm_curso de export_aprobacion.py).
RUTA_2026 = [
    "Bienvenidos a Jóvenes creaTIvos",
    "Hackea tu cerebro: Aprende en menos tiempo y sin sufrir",
    "Habilidades esenciales para ser un emprendedor exitoso",
    "Emprendimiento: Idea de Negocio JC",
    "Introducción a la IA Generativa - 2026",
    "Fundamentos Lógica de Programación - 2026",
    "Desarrollo Web Front-End - HTML - 2026",
]
UMBRAL_APROBADO = 100.0  # avance >= 100 aprueba (mismo criterio que export_aprobacion.py)


# ── Utilidades ────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[export-retirados] {msg}", flush=True)


def norm_id(valor) -> str:
    """Cédula comparable entre reportes: solo dígitos (igual que export_aprobacion.py)."""
    return re.sub(r"\D", "", str(valor))


def norm_curso(nombre) -> str:
    """Nombre de asignatura sin \\xa0 ni espacios repetidos (clave del ledger)."""
    return re.sub(r"\s+", " ", str(nombre).replace("\xa0", " ")).strip()


def cargar_cohorte_2026() -> dict | None:
    """Cohorte y retirados únicos 2026 por programa (cédulas), generado por
    export_aprobacion.py. Sin este archivo no se puede filtrar a 2026 → el panel
    degrada al histórico completo con una advertencia."""
    if not os.path.isfile(RUTA_COHORTE):
        log("ADVERTENCIA: falta tools/cohorte_2026.json — corre export_aprobacion.py "
            "primero. Se genera el histórico completo (sin filtro 2026).")
        return None
    try:
        with open(RUTA_COHORTE, encoding="utf-8") as f:
            data = json.load(f)
        por_prog = data.get("por_programa", {})
        n_ret = sum(len(v.get("retirados", [])) for v in por_prog.values())
        log(f"Cohorte 2026: {len(por_prog)} programas, {n_ret} retirados únicos "
            f"(generada {data.get('actualizado', '?')})")
        return data
    except (json.JSONDecodeError, OSError) as e:
        log(f"ADVERTENCIA: cohorte_2026.json ilegible ({e}) — histórico completo")
        return None


def cargar_ledger() -> dict:
    """{cedula: {curso_norm: max_avance}} — máximo avance visto por estudiante×curso.
    Necesario para la heurística de etapa de retiro. Vive en tools/ (PII)."""
    if os.path.isfile(RUTA_LEDGER):
        try:
            with open(RUTA_LEDGER, encoding="utf-8") as f:
                return json.load(f).get("estudiantes", {})
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: ledger ilegible ({e}) — sin heurística de etapa")
    else:
        log("ADVERTENCIA: falta tools/aprobacion_ledger.json — sin etapa de retiro")
    return {}


def etapa_de_retiro(cedula: str, ledger: dict) -> tuple[int, str]:
    """Último curso de la ruta 2026 con avance >= 100 para este retirado.
    Devuelve (orden, etiqueta): orden 0 = no completó ninguno; 1..N = índice en la ruta."""
    avances = ledger.get(cedula, {})
    ultimo = 0
    for i, curso in enumerate(RUTA_2026, start=1):
        if avances.get(norm_curso(curso), 0.0) >= UMBRAL_APROBADO:
            ultimo = i
    etiqueta = "No completó ningún curso" if ultimo == 0 else RUTA_2026[ultimo - 1]
    return ultimo, etiqueta


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
def procesar_historico(registros: list[dict]) -> dict:
    """Agregación histórica completa (fallback cuando no hay cohorte 2026)."""
    tipos, causas, programas, meses = Counter(), Counter(), Counter(), Counter()
    for r in registros:
        tipos[str(r.get("Tipo", "")).strip() or "Sin tipo"] += 1
        causas[str(r.get("Causa", "")).strip() or "Sin causa"] += 1
        programas[str(r.get("Programa", "")).strip() or "Sin programa"] += 1
        fecha = str(r.get("FechaCancelacion", "")).strip()
        meses[fecha[:7] if len(fecha) >= 7 else "sin fecha"] += 1
    total = len(registros)
    log(f"  Histórico completo: {total} retirados | Tipos: {dict(tipos)}")
    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        "anio": None,
        "totales": {
            "total_retirados": total,
            "cancelados":      tipos.get("Cancelado", 0),
            "desertores":      tipos.get("Desertor", 0),
            "aplazados":       tipos.get("Aplazado", 0),
        },
        "por_tipo":     [{"tipo": t, "cantidad": n} for t, n in tipos.most_common()],
        "por_causa":    [{"causa": c, "cantidad": n} for c, n in causas.most_common()],
        "por_programa": [{"programa": p, "cantidad": n} for p, n in programas.most_common()],
        "por_mes":      [{"mes": m, "cantidad": n} for m, n in sorted(meses.items())],
        "por_etapa":    [],
    }


def procesar_2026(registros: list[dict], cohorte: dict, ledger: dict) -> dict:
    """Agrega SOLO los retirados de la cohorte 2026.

    El conjunto autoritativo de retirados 2026 son las cédulas inhabilitadas de la
    cohorte (union de por_programa[*].retirados de cohorte_2026.json) — NO se filtra
    por FechaCancelacion. Los datos de tipo/causa/mes salen del cruce de esas cédulas
    con la pestaña Retirados; los que no tengan registro en la pestaña se cuentan
    aparte ('sin_registro_hoja') para que los totales cuadren con el panel de aprobación.
    La etapa de retiro sale del ledger (último curso de la ruta con avance >= 100)."""
    por_prog = cohorte.get("por_programa", {})

    # cédula → programa, y conjunto autoritativo de retirados 2026
    prog_de_ced: dict[str, str] = {}
    retirados_set: set[str] = set()
    for prog, v in por_prog.items():
        for ced in v.get("retirados", []):
            c = norm_id(ced)
            if c:
                retirados_set.add(c)
                prog_de_ced.setdefault(c, prog)

    # Cruce con la pestaña Retirados (tipo/causa/mes) — solo cédulas de la cohorte 2026
    tipos, causas, meses = Counter(), Counter(), Counter()
    con_registro: set[str] = set()
    for r in registros:
        ced = norm_id(r.get("Identificacion", ""))
        if ced not in retirados_set or ced in con_registro:
            continue
        con_registro.add(ced)
        tipos[str(r.get("Tipo", "")).strip() or "Sin tipo"] += 1
        causas[str(r.get("Causa", "")).strip() or "Sin causa"] += 1
        fecha = str(r.get("FechaCancelacion", "")).strip()
        meses[fecha[:7] if len(fecha) >= 7 else "sin fecha"] += 1

    sin_registro = retirados_set - con_registro
    if sin_registro:
        # Inhabilitados de la cohorte que no aparecen en la pestaña Retirados
        # (Q10 los archivó sin registro de cancelación formal).
        tipos["Sin registro de retiro"] += len(sin_registro)
        causas["Sin registro de retiro"] += len(sin_registro)

    # por_programa desde la cohorte (suma exacta al total de retirados 2026)
    programas = Counter()
    for ced in retirados_set:
        programas[prog_de_ced.get(ced, "Sin programa")] += 1

    # Etapa de retiro (heurística con ledger) sobre TODOS los retirados 2026
    etapas = Counter()  # orden → cantidad
    for ced in retirados_set:
        orden, _ = etapa_de_retiro(ced, ledger)
        etapas[orden] += 1
    por_etapa = []
    for orden in range(0, len(RUTA_2026) + 1):
        etiqueta = "No completó ningún curso" if orden == 0 else RUTA_2026[orden - 1]
        por_etapa.append({"orden": orden, "etapa": etiqueta,
                          "cantidad": etapas.get(orden, 0)})

    total = len(retirados_set)
    log(f"  Retirados 2026: {total} ({len(con_registro)} con registro en hoja, "
        f"{len(sin_registro)} sin registro) | Tipos: {dict(tipos)}")
    log(f"  Etapa de retiro: " + ", ".join(
        f"{e['etapa'][:24]}={e['cantidad']}" for e in por_etapa if e['cantidad']))

    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        "anio": cohorte.get("anio", "2026"),
        "totales": {
            "total_retirados": total,
            "cancelados":      tipos.get("Cancelado", 0),
            "desertores":      tipos.get("Desertor", 0),
            "aplazados":       tipos.get("Aplazado", 0),
            "sin_registro_hoja": len(sin_registro),
        },
        "por_tipo":     [{"tipo": t, "cantidad": n} for t, n in tipos.most_common()],
        "por_causa":    [{"causa": c, "cantidad": n} for c, n in causas.most_common()],
        "por_programa": [{"programa": p, "cantidad": n} for p, n in programas.most_common()],
        "por_mes":      [{"mes": m, "cantidad": n} for m, n in sorted(meses.items())],
        "por_etapa":    por_etapa,
        "ruta":         RUTA_2026,
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
                if norm_id(r.get("Identificacion", "")) not in excl
            ]
            if antes - len(registros):
                log(f"  Exclusión de pruebas: {antes - len(registros)} registros quitados")

        # Filtrar a la cohorte 2026 si existe tools/cohorte_2026.json; si no, histórico
        cohorte = cargar_cohorte_2026()
        if cohorte:
            ledger = cargar_ledger()
            datos = procesar_2026(registros, cohorte, ledger)
        else:
            datos = procesar_historico(registros)
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
