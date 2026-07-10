# -*- coding: utf-8 -*-
"""
normalize_q10_data.py — Fase 1a del panel de datos Supabase.

Lee la pestaña h2test (bloques por curso, doble encabezado) y la pestaña Retirados
del Sheet de Q10 → normaliza y valida → genera el payload listo para cargar a
Supabase (participants / courses / enrollments) + reporte de validación.

Reglas canónicas del proyecto (mismas que export_aprobacion/export_retirados):
  - Cédula normalizada a solo dígitos = q10_id (clave de cruce).
  - Aprobado/completado = avance > 80 (UMBRAL_APROBADO, operador >).
  - Desertores (Tipo=Desertor en pestaña Retirados) EXCLUIDOS de todo — perfiles de prueba.
  - Perfiles de prueba de tools/exclusiones_prueba.json EXCLUIDOS de todo.

⚠ PRIVACIDAD: el payload y el reporte contienen PII → se escriben SOLO en tools/
(gitignoreado). Nada de esto va a docs/ ni a GitHub.

Uso:
    python normalize_q10_data.py                # corrida completa
    python normalize_q10_data.py --max-filas 100  # prueba con muestra
Salidas:
    tools/supabase_payload.json          (participants, courses, enrollments)
    tools/normalize_report_YYYYMMDD.json (reporte de validación, PII)
Consola (parseable por n8n, patrón del proyecto):
    RESUMEN: participantes=N cursos=K matriculas=M errores=E advertencias=W estado=exito

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
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
PESTANA_H2TEST    = "h2test"
PESTANA_RETIRADOS = "Retirados"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_CREDENCIALES = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion",
                                 "credenciales_service_account.json")
RUTA_EXCLUSIONES  = os.path.join(PROYECTO_ROOT, "tools", "exclusiones_prueba.json")
RUTA_CONFIG_CURSOS = os.path.join(PROYECTO_ROOT, "tools", "course_config.json")
RUTA_PAYLOAD      = os.path.join(PROYECTO_ROOT, "tools", "supabase_payload.json")

# Clasificación de programa (misma lógica canónica de export_stats.py):
# course_config.json tiene precedencia; si el curso no está, keywords → MR; resto → JC
KEYWORDS_MR = ["emprendedoras", "idea a la acci"]
CONFIG_CURSOS = {"jc": [], "mr": [], "stand": []}  # se puebla en main()
DIR_REPORTES      = os.path.join(PROYECTO_ROOT, "tools")

UMBRAL_APROBADO = 80.0   # avance > 80 = completado (criterio canónico 2026-07-09)
COHORTE         = str(datetime.now().year)  # cohorte del participante (ej. "2026")
RE_EMAIL        = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")


# ── Utilidades (mismas convenciones que los exporters) ───────────────────────
def log(msg: str) -> None:
    print(f"[normalize-q10] {msg}", flush=True)


def norm_id(valor) -> str:
    """Cédula comparable entre reportes: solo dígitos."""
    return re.sub(r"\D", "", str(valor))


def norm_texto(valor) -> str:
    """Sin \\xa0 ni espacios repetidos, preservando el casing original."""
    return re.sub(r"\s+", " ", str(valor).replace("\xa0", " ")).strip()


def norm_email(valor) -> str:
    return norm_texto(valor).lower()


def cargar_config_cursos() -> dict:
    """{'jc': [...], 'mr': [...], 'stand': [...]} de tools/course_config.json."""
    if os.path.isfile(RUTA_CONFIG_CURSOS):
        try:
            with open(RUTA_CONFIG_CURSOS, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: course_config ilegible ({e}) — solo keywords")
    else:
        log("ADVERTENCIA: falta tools/course_config.json — clasificando solo por keywords")
    return {"jc": [], "mr": [], "stand": []}


def clasificar_curso(nombre: str, config: dict) -> str:
    """'jc' | 'mr' | 'stand' — config tiene precedencia sobre keywords."""
    n = norm_texto(nombre)
    for prog in ("jc", "mr", "stand"):
        if any(norm_texto(c) == n for c in config.get(prog, [])):
            return prog
    bajo = n.lower()
    if any(kw in bajo for kw in KEYWORDS_MR):
        return "mr"
    return "jc"


def cargar_exclusiones() -> tuple[set, set]:
    """Cédulas y emails de perfiles de prueba (tools/exclusiones_prueba.json)."""
    ceds, emails = set(), set()
    if os.path.isfile(RUTA_EXCLUSIONES):
        try:
            with open(RUTA_EXCLUSIONES, encoding="utf-8") as f:
                for p in json.load(f).get("perfiles", []):
                    ced = norm_id(p.get("cedula", ""))
                    if ced:
                        ceds.add(ced)
                    if p.get("email"):
                        emails.add(str(p["email"]).strip().lower())
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: exclusiones ilegibles ({e}) — no se excluye nada")
    else:
        log("ADVERTENCIA: falta tools/exclusiones_prueba.json — sin exclusión de pruebas")
    return ceds, emails


# ── Google Sheets ─────────────────────────────────────────────────────────────
def conectar() -> gspread.Spreadsheet:
    log("Conectando a Google Sheets...")
    if not os.path.isfile(RUTA_CREDENCIALES):
        raise FileNotFoundError(f"No se encontró {RUTA_CREDENCIALES}")
    creds = Credentials.from_service_account_file(RUTA_CREDENCIALES, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(SHEET_ID)


def detectar_grupos(row0: list, row1: list) -> list:
    """h2test: fila 1 = nombre del curso (celdas fusionadas), fila 2 = sub-headers.
    Mismo patrón que export_stats.detectar_grupos()."""
    posiciones = [(i, norm_texto(v)) for i, v in enumerate(row0) if v.strip()]
    grupos = []
    for j, (col_inicio, nombre) in enumerate(posiciones):
        col_fin = posiciones[j + 1][0] if j + 1 < len(posiciones) else len(row0)
        sub = [(i - col_inicio, row1[i].strip().lower())
               for i in range(col_inicio, min(col_fin, len(row1)))]
        grupos.append({
            "nombre":        nombre,
            "col_inicio":    col_inicio,
            "offset_id":     next((o for o, h in sub if "identificac" in h), None),
            "offset_nombre": next((o for o, h in sub if h == "nombre"), None),
            "offset_email":  next((o for o, h in sub if "email" in h or "correo" in h), None),
            "offset_avance": next((o for o, h in sub if "avance" in h), None),
        })
    return [g for g in grupos if g["offset_id"] is not None]


def _cel(row: list, col_inicio: int, offset) -> str:
    if offset is None:
        return ""
    i = col_inicio + offset
    return row[i].strip() if i < len(row) else ""


def leer_desertores(sh: gspread.Spreadsheet) -> set:
    """Cédulas con Tipo=Desertor en la pestaña Retirados (excluidos de todo)."""
    try:
        valores = sh.worksheet(PESTANA_RETIRADOS).get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        log("ADVERTENCIA: no existe pestaña Retirados — sin exclusión de desertores")
        return set()
    if not valores:
        return set()
    headers = [h.strip().lower() for h in valores[0]]
    try:
        i_id, i_tipo = headers.index("identificacion"), headers.index("tipo")
    except ValueError:
        log("ADVERTENCIA: pestaña Retirados sin headers esperados — sin exclusión")
        return set()
    desertores = {norm_id(r[i_id]) for r in valores[1:]
                  if len(r) > max(i_id, i_tipo)
                  and r[i_tipo].strip().lower() == "desertor" and norm_id(r[i_id])}
    log(f"Desertores en pestaña Retirados: {len(desertores)} (excluidos de todo)")
    return desertores


# ── Normalización y validación ────────────────────────────────────────────────
class Reporte:
    """Acumula errores/advertencias con detalle (PII → solo tools/)."""

    def __init__(self):
        self.errores = []
        self.advertencias = []
        self.contadores = Counter()

    def error(self, tipo: str, detalle: dict):
        self.errores.append({"tipo": tipo, **detalle})
        self.contadores[f"error_{tipo}"] += 1

    def warn(self, tipo: str, detalle: dict):
        self.advertencias.append({"tipo": tipo, **detalle})
        self.contadores[f"warn_{tipo}"] += 1


def normalizar_avance(crudo: str, curso: str, cedula: str, rep: Reporte):
    """'87,5' / '101' / '' → float 0-100 o None (descarta la matrícula)."""
    txt = norm_texto(crudo).replace("%", "").replace(",", ".")
    if txt == "":
        rep.warn("avance_vacio", {"cedula": cedula, "curso": curso})
        return 0.0
    try:
        v = float(txt)
    except ValueError:
        rep.error("avance_no_numerico", {"cedula": cedula, "curso": curso, "valor": crudo})
        return None
    if v < 0:
        rep.error("avance_negativo", {"cedula": cedula, "curso": curso, "valor": v})
        return None
    if v > 100:  # h2test trae 101 ocasionales (gotcha conocido del proyecto)
        rep.warn("avance_sobre_100", {"cedula": cedula, "curso": curso, "valor": v})
        v = 100.0
    return v


def estado_matricula(avance: float) -> str:
    if avance > UMBRAL_APROBADO:
        return "completado"
    if avance > 0:
        return "en_progreso"
    return "inscrito"


def procesar(all_values: list, desertores: set, excl_ceds: set, excl_emails: set,
             rep: Reporte, max_filas: int | None = None):
    """h2test → (participants{ced: dict}, courses[nombre], enrollments{(ced,curso): dict})."""
    grupos = detectar_grupos(all_values[0], all_values[1])
    log(f"Grupos de curso detectados en h2test: {len(grupos)}")
    filas = all_values[2:]
    if max_filas:
        filas = filas[:max_filas]
        log(f"MODO PRUEBA: solo primeras {max_filas} filas de datos")

    participants: dict[str, dict] = {}
    enrollments: dict[tuple, dict] = {}
    emails_vistos: dict[str, set] = defaultdict(set)  # email → set de cédulas

    for g in grupos:
        curso = g["nombre"]
        for n_fila, row in enumerate(filas, start=3):
            id_crudo = _cel(row, g["col_inicio"], g["offset_id"])
            if not id_crudo:
                continue
            cedula = norm_id(id_crudo)
            if not cedula:
                rep.error("cedula_invalida", {"fila": n_fila, "curso": curso, "valor": id_crudo})
                continue
            email = norm_email(_cel(row, g["col_inicio"], g["offset_email"]))
            if cedula in excl_ceds or email in excl_emails:
                rep.contadores["excluido_prueba"] += 1
                continue
            if cedula in desertores:
                rep.contadores["excluido_desertor"] += 1
                continue

            nombre = norm_texto(_cel(row, g["col_inicio"], g["offset_nombre"]))
            if not nombre:
                rep.warn("nombre_vacio", {"cedula": cedula, "curso": curso})
                nombre = "(sin nombre)"
            if email and not RE_EMAIL.match(email):
                rep.warn("email_invalido", {"cedula": cedula, "email": email})
                email = ""
            if email:
                emails_vistos[email].add(cedula)

            avance = normalizar_avance(_cel(row, g["col_inicio"], g["offset_avance"]),
                                       curso, cedula, rep)
            if avance is None:
                continue

            # participante: primera aparición gana; completar email/nombre si faltaban
            p = participants.setdefault(cedula, {
                "q10_id": cedula, "nombre": nombre, "email": email or None,
                # sociodemográficos: llegan después desde la BD de monitorias (nullable)
                "ciudad": None, "tipo_vivienda": None, "estrato": None, "edad": None,
                "estado_civil": None, "nivel_estudio": None,
            })
            if p["email"] is None and email:
                p["email"] = email
            if p["nombre"] == "(sin nombre)" and nombre != "(sin nombre)":
                p["nombre"] = nombre

            # matrícula: duplicado (misma cédula+curso, ej. periodos fusionados) → keepMax
            clave = (cedula, curso)
            if clave in enrollments:
                if avance > enrollments[clave]["porcentaje_avance"]:
                    enrollments[clave]["porcentaje_avance"] = int(round(avance))
                    enrollments[clave]["estado"] = estado_matricula(avance)
                rep.warn("matricula_duplicada", {"cedula": cedula, "curso": curso})
            else:
                enrollments[clave] = {
                    "q10_id": cedula, "curso": curso,
                    "porcentaje_avance": int(round(avance)),
                    "estado": estado_matricula(avance),
                }

    # email compartido entre cédulas distintas → advertencia (no bloquea)
    for email, ceds in emails_vistos.items():
        if len(ceds) > 1:
            rep.warn("email_compartido", {"email": email, "cedulas": sorted(ceds)})

    courses = sorted({e["curso"] for e in enrollments.values()})
    return participants, courses, enrollments


# ── Salidas ───────────────────────────────────────────────────────────────────
def guardar_payload(participants: dict, courses: list, enrollments: dict) -> dict:
    """Payload determinista (ordenado) → idempotente entre corridas del mismo input."""
    payload = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "cohorte": COHORTE,
        "umbral_aprobado": UMBRAL_APROBADO,
        "participants": [participants[c] for c in sorted(participants)],
        "courses": [{"nombre": c, "cohorte": COHORTE, "estado": "activo",
                     "programa": clasificar_curso(c, CONFIG_CURSOS)} for c in courses],
        "enrollments": [enrollments[k] for k in sorted(enrollments)],
    }
    os.makedirs(os.path.dirname(RUTA_PAYLOAD), exist_ok=True)
    with open(RUTA_PAYLOAD, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    log(f"Payload → {RUTA_PAYLOAD}")
    return payload


def guardar_reporte(rep: Reporte, payload: dict) -> str:
    ruta = os.path.join(DIR_REPORTES, f"normalize_report_{datetime.now():%Y%m%d}.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({
            "generado": payload["generado"],
            "totales": {
                "participantes": len(payload["participants"]),
                "cursos": len(payload["courses"]),
                "matriculas": len(payload["enrollments"]),
                "errores": len(rep.errores),
                "advertencias": len(rep.advertencias),
            },
            "contadores": dict(rep.contadores),
            "errores": rep.errores,
            "advertencias": rep.advertencias,
        }, f, ensure_ascii=False, indent=1)
    log(f"Reporte → {ruta}")
    return ruta


def main() -> int:
    ap = argparse.ArgumentParser(description="Normaliza h2test → payload Supabase (Fase 1a)")
    ap.add_argument("--max-filas", type=int, default=None,
                    help="Procesar solo las primeras N filas de datos (prueba)")
    args = ap.parse_args()

    global CONFIG_CURSOS
    CONFIG_CURSOS = cargar_config_cursos()
    rep = Reporte()
    excl_ceds, excl_emails = cargar_exclusiones()
    sh = conectar()
    desertores = leer_desertores(sh)
    log(f"Leyendo pestaña {PESTANA_H2TEST}...")
    all_values = sh.worksheet(PESTANA_H2TEST).get_all_values()
    if len(all_values) < 3:
        log("ERROR: h2test sin datos suficientes")
        return 1

    participants, courses, enrollments = procesar(
        all_values, desertores, excl_ceds, excl_emails, rep, args.max_filas)

    payload = guardar_payload(participants, courses, enrollments)
    guardar_reporte(rep, payload)

    log(f"Cursos: {', '.join(courses)}")
    top = rep.contadores.most_common(8)
    if top:
        log("Contadores: " + ", ".join(f"{k}={v}" for k, v in top))
    estado = "exito" if not rep.errores else "con_errores"
    print(f"RESUMEN: participantes={len(payload['participants'])} "
          f"cursos={len(payload['courses'])} matriculas={len(payload['enrollments'])} "
          f"errores={len(rep.errores)} advertencias={len(rep.advertencias)} estado={estado}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
