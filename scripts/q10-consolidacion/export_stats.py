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

DIRECTORIO_SCRIPT      = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT          = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_DATA_JSON         = os.path.join(PROYECTO_ROOT, "docs", "dashboard", "data.json")
RUTA_HISTORY_JSON      = os.path.join(PROYECTO_ROOT, "docs", "dashboard", "history.json")
RUTA_MAXIMOS_JSON      = os.path.join(PROYECTO_ROOT, "docs", "dashboard", "maximos_cursos.json")
CONFIG_CURSOS          = os.path.join(PROYECTO_ROOT, "tools", "course_config.json")
RUTA_EXCLUSIONES       = os.path.join(PROYECTO_ROOT, "tools", "exclusiones_prueba.json")
INTERVALO_HISTORY_DIAS = 4   # snapshot cada ~4 días (dos veces por semana)

# ── Cursos finalizados (marca de agua) ──────────────────────────────────────────
# Un curso ya no crece y sus estudiantes se van archivando en Q10 (Estado A → fuera
# del Consolidado), así que su matrícula "en vivo" encoge. Rastreamos el máximo
# histórico por curso para congelar inscritos/finalizados de los cursos terminados.
UMBRAL_AVANCE_FIN   = 100.0  # avance >= esto cuenta como "finalizó el curso" (cubre los 101)
UMBRAL_PROMEDIO_FIN = 90.0   # promedio del curso para considerarlo finalizado
MARGEN_DECLIVE      = 0.02   # matrícula cae >=2% del pico => cohorte ya archivándose


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


# ── Exclusión de usuarios de prueba ───────────────────────────────────────────
def _cargar_exclusiones() -> tuple[set, set]:
    """Cédulas y emails de perfiles de prueba (tools/exclusiones_prueba.json,
    gitignoreado). No deben contar en ningún KPI ni tabla."""
    ceds, emails = set(), set()
    if os.path.isfile(RUTA_EXCLUSIONES):
        try:
            with open(RUTA_EXCLUSIONES, encoding="utf-8") as f:
                for p in json.load(f).get("perfiles", []):
                    ced = "".join(ch for ch in str(p.get("cedula", "")) if ch.isdigit())
                    if ced:
                        ceds.add(ced)
                    if p.get("email"):
                        emails.add(str(p["email"]).strip().lower())
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: exclusiones ilegibles ({e}) — no se excluye nada")
    return ceds, emails


EXCL_CEDS, EXCL_EMAILS = _cargar_exclusiones()


def _es_prueba(id_val: str, email_val: str) -> bool:
    ced = "".join(ch for ch in id_val if ch.isdigit())
    return (ced in EXCL_CEDS) or (email_val in EXCL_EMAILS)


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


def _cargar_config_cursos() -> dict:
    if os.path.isfile(CONFIG_CURSOS):
        try:
            with open(CONFIG_CURSOS, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"jc": [], "mr": [], "stand": []}


def _clasificar_curso(nombre: str, config: dict) -> str:
    """Retorna 'jc', 'mr' o 'stand'. Config tiene precedencia sobre keywords."""
    n = ' '.join(nombre.replace('\xa0', ' ').split())
    if n in config.get("mr",    []): return "mr"
    if n in config.get("stand", []): return "stand"
    if n in config.get("jc",    []): return "jc"
    n_low = nombre.lower()
    return "mr" if any(p in n_low for p in _PALABRAS_MR) else "jc"


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
            if _es_prueba(id_val, email_val):
                continue
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
        finalizados = sum(1 for a in avances if a >= UMBRAL_AVANCE_FIN)
        por_curso.append({
            "curso":       g["nombre"],
            "estudiantes": n,             # activos hoy (en vivo)
            "finalizados": finalizados,   # con avance >= 100 (en vivo; se congela en máximos)
            "promedio":    round(sum(avances) / n, 2) if n else 0.0,
            "min":         round(min(avances), 2) if avances else 0.0,
            "max":         round(max(avances), 2) if avances else 0.0,
        })

    return por_curso, emails_unicos, emails_habilitados, avance_0, avance_irr


def procesar_h2test(all_values: list) -> tuple:
    """
    Separa cursos JC, MR y Stand-by según course_config.json (keywords como fallback).
    Retorna (pc_jc, pc_mr, pc_stand, anom_jc, anom_mr, n_jc, hab_jc, n_mr, hab_mr,
             n_stand, hab_stand, total_db).
    """
    if len(all_values) < 2:
        raise ValueError("La hoja h2test está vacía o tiene menos de 2 filas.")

    config = _cargar_config_cursos()
    grupos = detectar_grupos(all_values[0], all_values[1])
    filas  = all_values[2:]

    cursos_normales = [g for g in grupos if "sin curso" not in g["nombre"].lower()]
    grupo_sin_curso = next((g for g in grupos if "sin curso" in g["nombre"].lower()), None)

    cursos_jc    = [g for g in cursos_normales if _clasificar_curso(g["nombre"], config) == "jc"]
    cursos_mr    = [g for g in cursos_normales if _clasificar_curso(g["nombre"], config) == "mr"]
    cursos_stand = [g for g in cursos_normales if _clasificar_curso(g["nombre"], config) == "stand"]

    pc_jc,    em_jc,    eh_jc,    av0_jc,    avi_jc    = _procesar_grupos(filas, cursos_jc)
    pc_mr,    em_mr,    eh_mr,    av0_mr,    avi_mr    = _procesar_grupos(filas, cursos_mr)
    pc_stand, em_stand, eh_stand, av0_stand, avi_stand = _procesar_grupos(filas, cursos_stand)

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

    total_db = len(em_jc | em_mr | em_stand | emails_sin_curso)

    anom_jc = [
        {"categoria": "SIN MATCH",        "cantidad": sin_match},
        {"categoria": "AVANCE 0%",         "cantidad": av0_jc},
        {"categoria": "AVANCE IRREGULAR",  "cantidad": avi_jc},
    ]
    anom_mr = [
        {"categoria": "AVANCE 0%",         "cantidad": av0_mr},
        {"categoria": "AVANCE IRREGULAR",  "cantidad": avi_mr},
    ]

    log(f"  JC:    {len(pc_jc)} cursos | {len(em_jc)} únicos | Hab: {len(eh_jc)} | SIN MATCH: {sin_match} | AVANCE 0%: {av0_jc} | IRR: {avi_jc}")
    log(f"  MR:    {len(pc_mr)} cursos | {len(em_mr)} únicos | Hab: {len(eh_mr)} | AVANCE 0%: {av0_mr} | IRR: {avi_mr}")
    log(f"  STAND: {len(pc_stand)} cursos | {len(em_stand)} únicos")
    log(f"  Total DB: {total_db}")
    return (pc_jc, pc_mr, pc_stand, anom_jc, anom_mr,
            len(em_jc), len(eh_jc),
            len(em_mr), len(eh_mr),
            len(em_stand), len(eh_stand),
            total_db)


# ── Generación de data.json ────────────────────────────────────────────────────
def generar_json(pc_jc: list, pc_mr: list, pc_stand: list,
                 anom_jc: list, anom_mr: list,
                 n_jc: int, hab_jc: int,
                 n_mr: int, hab_mr: int,
                 n_stand: int, hab_stand: int,
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
        # Cursos en observación (sin programa asignado aún)
        "stand": {
            "por_curso": pc_stand,
            "totales": {
                "total_cursos":             len(pc_stand),
                "total_estudiantes_unicos": n_stand,
                "total_habilitados":        hab_stand,
            },
        },
    }


def guardar_json(datos: dict) -> None:
    os.makedirs(os.path.dirname(RUTA_DATA_JSON), exist_ok=True)
    with open(RUTA_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    log(f"  data.json generado en: {RUTA_DATA_JSON}")


# ── Marca de agua de cursos (inscritos / finalizados congelados) ────────────────
def _norm_nombre(nombre: str) -> str:
    return ' '.join(nombre.replace('\xa0', ' ').split())


def _seed_maximos_desde_history() -> dict:
    """Siembra máximos iniciales desde history.json: para cada curso, el pico de
    matrícula ('estudiantes') jamás registrado. finalizados arranca en 0 y se llena
    en la próxima corrida real (history.json no guarda el conteo al 100%)."""
    seed: dict = {}
    if not os.path.isfile(RUTA_HISTORY_JSON):
        return seed
    try:
        with open(RUTA_HISTORY_JSON, encoding="utf-8") as f:
            historia = json.load(f)
    except Exception:
        return seed
    for snap in historia:
        fecha = snap.get("fecha", "")
        for prog in ("jc", "mr"):
            for c in snap.get(prog, {}).get("por_curso", []):
                nombre = _norm_nombre(c.get("curso", ""))
                if not nombre:
                    continue
                est  = c.get("estudiantes", 0) or 0
                prev = seed.get(nombre)
                if prev is None or est > prev["inscritos"]:
                    seed[nombre] = {
                        "inscritos":         est,
                        "inscritos_fecha":   fecha,
                        "promedio_en_pico":  c.get("promedio", 0.0),
                        "finalizados":       0,
                        "finalizados_fecha": "",
                    }
    if seed:
        log(f"  Máximos: sembrados desde history.json ({len(seed)} cursos)")
    return seed


def _cargar_maximos() -> dict:
    if os.path.isfile(RUTA_MAXIMOS_JSON):
        try:
            with open(RUTA_MAXIMOS_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return _seed_maximos_desde_history()


def _enriquecer_curso(c: dict, maximos: dict, hoy: str) -> None:
    """Actualiza la marca de agua del curso y le añade inscritos/finalizados/finalizado.

    - inscritos:   máx histórico de 'estudiantes' (matrícula pico 2026, nunca decae).
    - finalizados: máx histórico de avance >= 100 (nunca decae).
    - finalizado:  True si el promedio es alto Y la matrícula ya bajó del pico
                   (señal de que Q10 empezó a archivar la cohorte al terminar).
    """
    nombre    = _norm_nombre(c["curso"])
    live_est  = c.get("estudiantes", 0)
    live_fin  = c.get("finalizados", 0)
    live_prom = c.get("promedio", 0.0)

    m = maximos.get(nombre, {
        "inscritos": 0, "inscritos_fecha": "", "promedio_en_pico": 0.0,
        "finalizados": 0, "finalizados_fecha": "",
    })
    if live_est > m.get("inscritos", 0):
        m["inscritos"]        = live_est
        m["inscritos_fecha"]  = hoy
        m["promedio_en_pico"] = live_prom
    if live_fin > m.get("finalizados", 0):
        m["finalizados"]       = live_fin
        m["finalizados_fecha"] = hoy
    maximos[nombre] = m

    inscritos     = m["inscritos"]   or live_est
    finalizados   = m["finalizados"] or live_fin
    promedio_pico = m["promedio_en_pico"] or live_prom
    finalizado    = (live_prom >= UMBRAL_PROMEDIO_FIN
                     and inscritos > 0
                     and live_est <= inscritos * (1 - MARGEN_DECLIVE))

    c["inscritos"]     = inscritos
    c["finalizados"]   = finalizados
    c["promedio_pico"] = round(promedio_pico, 2)
    c["finalizado"]    = finalizado


def enriquecer_con_maximos(*listas_por_curso: list) -> dict:
    """Aplica la marca de agua a todas las listas por_curso in-place. Retorna
    el dict de máximos actualizado (para persistir)."""
    maximos = _cargar_maximos()
    hoy = datetime.now().date().isoformat()
    for lista in listas_por_curso:
        for c in lista:
            _enriquecer_curso(c, maximos, hoy)
    return maximos


def guardar_maximos(maximos: dict) -> None:
    os.makedirs(os.path.dirname(RUTA_MAXIMOS_JSON), exist_ok=True)
    with open(RUTA_MAXIMOS_JSON, "w", encoding="utf-8") as f:
        json.dump(maximos, f, ensure_ascii=False, indent=2)
    log(f"  maximos_cursos.json actualizado ({len(maximos)} cursos).")


# ── Historial de snapshots ────────────────────────────────────────────────────
def _snapshot_from_data(datos: dict, fecha: str) -> dict:
    """Extrae un resumen liviano de un data.json completo para el historial."""
    def resumir(por_curso: list, total_unicos: int) -> dict:
        cursos = [
            {"curso": c["curso"], "promedio": c["promedio"], "estudiantes": c["estudiantes"]}
            for c in por_curso
        ]
        total_est = sum(c["estudiantes"] for c in cursos)
        prom_global = (
            round(sum(c["promedio"] * c["estudiantes"] for c in cursos) / total_est, 2)
            if total_est else 0.0
        )
        return {"total_estudiantes_unicos": total_unicos, "promedio_global": prom_global, "por_curso": cursos}

    jc = resumir(datos.get("por_curso", []),
                 datos.get("totales", {}).get("total_estudiantes_unicos", 0))
    mr = resumir(datos.get("mr", {}).get("por_curso", []),
                 datos.get("mr", {}).get("totales", {}).get("total_estudiantes_unicos", 0))
    return {"fecha": fecha, "jc": jc, "mr": mr}


def actualizar_history(datos: dict) -> bool:
    """
    Añade un snapshot a history.json si han pasado >= INTERVALO_HISTORY_DIAS
    desde el último registro. Retorna True si se añadió un nuevo snapshot.
    """
    historia: list = []
    if os.path.isfile(RUTA_HISTORY_JSON):
        try:
            with open(RUTA_HISTORY_JSON, encoding="utf-8") as f:
                historia = json.load(f)
        except Exception:
            historia = []

    hoy = datetime.now().date()

    if historia:
        ultima_fecha = datetime.fromisoformat(historia[-1]["fecha"]).date()
        delta = (hoy - ultima_fecha).days
        if delta < INTERVALO_HISTORY_DIAS:
            log(f"  History: último snapshot hace {delta} día(s) (umbral {INTERVALO_HISTORY_DIAS}). Sin cambios.")
            return False

    entrada = _snapshot_from_data(datos, hoy.isoformat())
    historia.append(entrada)

    os.makedirs(os.path.dirname(RUTA_HISTORY_JSON), exist_ok=True)
    with open(RUTA_HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(historia, f, ensure_ascii=False, indent=2)

    log(f"  History: snapshot {hoy.isoformat()} añadido — total: {len(historia)} entradas.")
    return True


# ── Git commit y push ──────────────────────────────────────────────────────────
def git_commit_y_push(timestamp: str, incluir_history: bool = False) -> bool:
    """Retorna True si el push salió bien (o no había nada que publicar), False si falló."""
    archivos = [
        os.path.join("docs", "dashboard", "data.json"),
        os.path.join("docs", "dashboard", "maximos_cursos.json"),
    ]
    if incluir_history:
        archivos.append(os.path.join("docs", "dashboard", "history.json"))

    try:
        resultado_status = subprocess.run(
            ["git", "status", "--porcelain", "--"] + archivos,
            cwd=PROYECTO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
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

    sufijo = " +history" if incluir_history else ""
    pasos = [
        ["git", "add"] + archivos,
        ["git", "commit", "-m", f"chore: actualizar estadisticas [{timestamp}]{sufijo}"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in pasos:
        try:
            resultado = subprocess.run(
                cmd,
                cwd=PROYECTO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
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


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Exporta stats h2test a data.json")
    parser.add_argument("--sin-push", action="store_true",
                        help="Genera el JSON sin git commit/push (pruebas)")
    args = parser.parse_args()

    try:
        hoja = conectar_hoja()

        log(f"Leyendo hoja '{NOMBRE_HOJA}'...")
        all_values = hoja.get_all_values()
        log(f"  {len(all_values)} filas leídas.")

        (pc_jc, pc_mr, pc_stand,
         anom_jc, anom_mr,
         n_jc, hab_jc,
         n_mr, hab_mr,
         n_stand, hab_stand,
         total_db) = procesar_h2test(all_values)

        log("Actualizando máximos históricos por curso...")
        maximos = enriquecer_con_maximos(pc_jc, pc_mr, pc_stand)
        guardar_maximos(maximos)
        n_fin = sum(1 for c in pc_jc if c.get("finalizado"))
        log(f"  Cursos JC marcados como finalizados: {n_fin}")

        datos = generar_json(pc_jc, pc_mr, pc_stand,
                             anom_jc, anom_mr,
                             n_jc, hab_jc,
                             n_mr, hab_mr,
                             n_stand, hab_stand,
                             total_db)
        guardar_json(datos)

        log("Actualizando historial...")
        nuevo_snapshot = actualizar_history(datos)

        if args.sin_push:
            log("Modo --sin-push: no se toca git.")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
            log("Ejecutando git commit y push...")
            if not git_commit_y_push(timestamp, incluir_history=nuevo_snapshot):
                print(
                    f"EXPORT: cursos_jc={len(pc_jc)} cursos_mr={len(pc_mr)} "
                    f"cursos_stand={len(pc_stand)} estado=error detalle=git_push_fallido",
                    flush=True,
                )
                sys.exit(1)

        log("=" * 60)
        log(f"  Cursos JC           : {len(pc_jc)}")
        log(f"  Cursos MR           : {len(pc_mr)}")
        log(f"  Cursos Stand-by     : {len(pc_stand)}")
        log(f"  Archivo generado    : {RUTA_DATA_JSON}")
        log("=" * 60)
        print(f"EXPORT: cursos_jc={len(pc_jc)} cursos_mr={len(pc_mr)} cursos_stand={len(pc_stand)} estado=exito", flush=True)

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
