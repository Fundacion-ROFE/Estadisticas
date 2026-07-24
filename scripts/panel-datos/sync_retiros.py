# -*- coding: utf-8 -*-
"""
sync_retiros.py — Retiro INDIVIDUAL (JC + MR) → Supabase tabla `retiros`.

Cierra el gap #1 de la auditoría 2026-07-23: el retiro solo existía como agregado
(cohorte_ingresos.retirados) — esto carga la fila individual (variable de resultado
más valiosa para el análisis uso-Emoflow ↔ retención).

Fuentes (dos Sheets distintos, mismo Service Account):
  JC: pestaña "Retirados" del Sheet h2test (1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs)
      — columnas: Identificacion, Nombre, TipoDocumento, Telefono, Programa, Sede,
      FechaCancelacion, Causa, Descripcion, Tipo. Verificado en vivo 2026-07-24: 370
      filas, 100% Programa="Jóvenes creaTIvos", 0 cédulas duplicadas, todas con fecha.
  MR: pestaña "Inactivas" del Sheet BD-Mujeres ROFÉ (1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8)
      — sin headers de "Retiros" por nombre estable; índices 0-based verificados en vivo
      2026-07-24: cedula=4 ("Numero de identificacion"), Motivos=25, Estado=26,
      Año-retiro=27. ~33 filas usables (2 descartadas: cédula vacía/ilegible).

Mapeo a `retiros` (esquema 007, upsert on_conflict=cedula,cohorte,programa):
  cedula         : Identificacion / Numero de identificacion, solo dígitos
  participant_id : lookup participants.q10_id (misma convención que sync_postulantes_mr.py
                   y cargar_supabase.py — la cédula ES el q10_id); NULL si no matchea
  programa       : 'jc' / 'mr' (valores REALES del enum programa_type — verificado con
                   GET /cohorte_ingresos en vivo; el plan usa 'JC'/'MR' en prosa pero el
                   enum vive en minúscula)
  cohorte        : JC → '2026' si la cédula está en el set autoritativo
                    tools/cohorte_2026.json:por_programa["Jóvenes creaTIvos"].retirados
                    (mismo criterio que export_retirados.py); si no, año de
                    FechaCancelacion (best-effort, histórico). MR → Año-retiro tal cual
                    (el propio 007 advierte: puede ser año de registro de la baja, no
                    cohorte real — se documenta en el motivo).
  fecha_retiro   : JC → FechaCancelacion (solo fecha, sin hora). MR → NULL (la fuente
                   solo trae año).
  anio_retiro    : JC → año de FechaCancelacion. MR → Año-retiro crudo.
  motivo         : JC → "Causa — Descripcion" (300 car). MR → "Estado — Motivos" +
                   nota de la ambigüedad de Año-retiro (300 car).
  etapa          : JC → etapa_de_retiro() (adaptada de export_retirados.py) contra
                   tools/aprobacion_ledger.json. MR → NULL (sin ruta de cursos equivalente).
  fuente         : 'sheet_retirados_q10' / 'inactivas_mr'

Uso:
    python sync_retiros.py [--dry-run]
Consola (parseable por n8n):
    RESUMEN: jc=N mr=M total=T cargados=C con_match_participant=K estado=exito|dry_run

Fundación ROFÉ | Jóvenes creaTIvos · Mujeres ROFÉ
"""

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime

try:
    import truststore
    truststore.inject_into_ssl()  # SSL corporativo (convención del proyecto)
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import gspread
from google.oauth2.service_account import Credentials
import urllib.error
import urllib.request

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_CREDENCIALES = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion",
                                  "credenciales_service_account.json")
RUTA_EXCLUSIONES  = os.path.join(PROYECTO_ROOT, "tools", "exclusiones_prueba.json")
RUTA_COHORTE      = os.path.join(PROYECTO_ROOT, "tools", "cohorte_2026.json")
RUTA_LEDGER       = os.path.join(PROYECTO_ROOT, "tools", "aprobacion_ledger.json")

SHEET_JC_ID  = "1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs"  # h2test
HOJA_JC      = "Retirados"
SHEET_MR_ID  = "1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8"  # BD-Mujeres ROFÉ
HOJA_MR      = "Inactivas"

# Índices 0-based de "Inactivas" verificados en vivo 2026-07-24 (mismo Sheet que
# sync_postulantes_mr.py:IDX_INACTIVAS, que ya usa cedula=4; Motivos/Estado/Año-retiro
# no estaban capturados ahí porque ese script no los necesita).
IDX_MR_CEDULA  = 4
IDX_MR_MOTIVOS = 25
IDX_MR_ESTADO  = 26
IDX_MR_ANIO    = 27

USER_AGENT = "panel-datos-etl/1.0"  # NO Mozilla — Supabase bloquea secrets "de navegador"
LOTE       = 500

# Ruta de aprendizaje 2026 de JC, idéntica a export_retirados.py:RUTA_2026 — necesaria
# para adaptar etapa_de_retiro() sin depender de un import cruzado entre
# scripts/q10-consolidacion y scripts/panel-datos (convención de la casa: duplicar,
# no compartir módulo — ver Track A del plan 2026-07-24).
RUTA_2026 = [
    "Bienvenidos a Jóvenes creaTIvos",
    "Hackea tu cerebro: Aprende en menos tiempo y sin sufrir",
    "Habilidades esenciales para ser un emprendedor exitoso",
    "Emprendimiento: Idea de Negocio JC",
    "Introducción a la IA Generativa - 2026",
    "Fundamentos Lógica de Programación - 2026",
    "Desarrollo Web Front-End - HTML - 2026",
]
UMBRAL_APROBADO = 80.0  # mismo criterio que export_retirados.py / export_aprobacion.py


def log(msg: str) -> None:
    print(f"[sync-retiros] {msg}", flush=True)


def norm_id(valor) -> str:
    """Cédula comparable entre fuentes: solo dígitos."""
    return re.sub(r"\D", "", str(valor))


def norm_curso(nombre) -> str:
    """Nombre de asignatura sin \\xa0 ni espacios repetidos (clave del ledger)."""
    return re.sub(r"\s+", " ", str(nombre).replace("\xa0", " ")).strip()


def cargar_env_local() -> None:
    if not os.path.isfile(RUTA_ENV):
        return
    with open(RUTA_ENV, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def cargar_exclusiones() -> set:
    """Cédulas de perfiles de prueba (tools/exclusiones_prueba.json, gitignoreado)."""
    ceds = set()
    if os.path.isfile(RUTA_EXCLUSIONES):
        try:
            with open(RUTA_EXCLUSIONES, encoding="utf-8") as f:
                for p in json.load(f).get("perfiles", []):
                    ced = norm_id(p.get("cedula", ""))
                    if ced:
                        ceds.add(ced)
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: exclusiones ilegibles ({e}) — no se excluye nada")
    return ceds


def cargar_cohorte_2026_jc() -> tuple:
    """(retirados, roster_completo) de la cohorte 2026 JC — cédulas, mismo criterio
    que export_retirados.py:cargar_cohorte_2026 (generado por export_aprobacion.py).
    Vacíos si falta el archivo (degrada: toda fila JC usa el año de FechaCancelacion).

    roster_completo (cohorte ∪ retirados) sirve para blindar el fallback de año: Q10
    a veces reescribe FechaCancelacion al reprocesar registros viejos (fecha "hoy" en
    vez de la fecha real de retiro — gotcha ya documentado en mapa-codigo.md), así que
    un año=2026 en la hoja NO basta para asumir cohorte 2026 si la cédula ni siquiera
    pertenece al roster 2026 (verificado en vivo 2026-07-24: 25 filas así)."""
    if not os.path.isfile(RUTA_COHORTE):
        log("ADVERTENCIA: falta tools/cohorte_2026.json — corre export_aprobacion.py "
            "primero. Cohorte JC se infiere solo del año de FechaCancelacion.")
        return set(), set()
    try:
        with open(RUTA_COHORTE, encoding="utf-8") as f:
            data = json.load(f)
        jc = data.get("por_programa", {}).get("Jóvenes creaTIvos", {})
        retirados = {norm_id(c) for c in jc.get("retirados", [])}
        roster = retirados | {norm_id(c) for c in jc.get("cohorte", [])}
        log(f"Cohorte 2026 JC: {len(retirados)} retirados únicos, {len(roster)} en "
            f"roster completo (generada {data.get('actualizado', '?')})")
        return retirados, roster
    except (json.JSONDecodeError, OSError) as e:
        log(f"ADVERTENCIA: cohorte_2026.json ilegible ({e}) — sin filtro 2026")
        return set(), set()


def cargar_ledger() -> dict:
    """{cedula: {curso_norm: max_avance}} — necesario para la heurística de etapa.
    Adaptado de export_retirados.py:cargar_ledger()."""
    if os.path.isfile(RUTA_LEDGER):
        try:
            with open(RUTA_LEDGER, encoding="utf-8") as f:
                return json.load(f).get("estudiantes", {})
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: ledger ilegible ({e}) — sin etapa de retiro")
    else:
        log("ADVERTENCIA: falta tools/aprobacion_ledger.json — sin etapa de retiro")
    return {}


def etapa_de_retiro(cedula: str, ledger: dict) -> str:
    """Último curso de la ruta 2026 con avance >= 100 para este retirado JC.
    Adaptado de export_retirados.py:etapa_de_retiro() — aquí solo se necesita la
    etiqueta (no el orden numérico, que export_retirados.py usa para agrupar)."""
    avances = ledger.get(cedula, {})
    ultimo = 0
    for i, curso in enumerate(RUTA_2026, start=1):
        if avances.get(norm_curso(curso), 0.0) > UMBRAL_APROBADO:
            ultimo = i
    return "No completó ningún curso" if ultimo == 0 else RUTA_2026[ultimo - 1]


class Supa:
    """Cliente REST mínimo (stdlib) con service key — mismo patrón que
    cargar_supabase.py / sync_postulantes_mr.py (no reescribir el paginador)."""

    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.key = key

    def _req(self, metodo: str, ruta: str, cuerpo=None, prefer: str = ""):
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}",
                   "Content-Type": "application/json", "User-Agent": USER_AGENT}
        if prefer:
            headers["Prefer"] = prefer
        req = urllib.request.Request(
            self.base + ruta, method=metodo, headers=headers,
            data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                datos = resp.read()
                return resp.status, json.loads(datos) if datos else None
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="replace")[:500]
            raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: {detalle}") from None

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        """GET paginado (PostgREST corta en ~1000 filas por defecto)."""
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            _, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page


def _conectar_sheet(sheet_id: str):
    creds = Credentials.from_service_account_file(
        RUTA_CREDENCIALES, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    return gspread.authorize(creds).open_by_key(sheet_id)


def leer_registros_tolerante(ws) -> list:
    """get_all_records() tolerante: ignora columnas con encabezado vacío o duplicado
    (patrón de export_retirados.py:leer_registros — una fórmula suelta en la fila 1
    no debe tumbar el pipeline)."""
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


# ── Extracción JC ───────────────────────────────────────────────────────────────
def extraer_jc(exclusiones: set) -> list:
    log(f"Leyendo hoja '{HOJA_JC}' del Sheet JC (id {SHEET_JC_ID})...")
    sh = _conectar_sheet(SHEET_JC_ID)
    ws = sh.worksheet(HOJA_JC)
    registros = leer_registros_tolerante(ws)
    log(f"  {len(registros)} filas leídas.")

    retirados_2026, roster_2026 = cargar_cohorte_2026_jc()
    ledger = cargar_ledger()

    filas, vistos = [], set()
    excluidos = 0
    for r in registros:
        ced = norm_id(r.get("Identificacion", ""))
        if not ced:
            continue
        if ced in exclusiones:
            excluidos += 1
            continue

        fecha_raw = str(r.get("FechaCancelacion", "")).strip()
        fecha_retiro = fecha_raw[:10] if len(fecha_raw) >= 10 else None
        anio = fecha_raw[:4] if len(fecha_raw) >= 4 and fecha_raw[:4].isdigit() else None
        # cohorte VARCHAR(10) — placeholders cortos a propósito.
        nota_cohorte = None
        if ced in retirados_2026:
            cohorte = "2026"
        elif anio == "2026" and ced not in roster_2026:
            # FechaCancelacion cae en 2026 pero la cédula no pertenece al roster 2026
            # (ni activo ni retirado) — fecha de Q10 no confiable para esta fila, no se
            # confirma cohorte (evita inflar el cuadre contra cohorte_ingresos).
            cohorte = "no_cohorte"
            nota_cohorte = "[cohorte no confirmada: FechaCancelacion=2026 pero cédula fuera del roster 2026]"
        else:
            cohorte = anio or "sin_fecha"

        causa = str(r.get("Causa", "")).strip()
        descripcion = str(r.get("Descripcion", "")).strip()
        motivo = " — ".join(p for p in (causa, descripcion) if p)
        if nota_cohorte:
            motivo = f"{motivo} {nota_cohorte}" if motivo else nota_cohorte
        motivo = motivo[:300] or None

        etapa = etapa_de_retiro(ced, ledger)

        clave = (ced, cohorte)
        if clave in vistos:
            continue  # defensivo: la hoja no traía duplicados al 2026-07-24, pero puede cambiar
        vistos.add(clave)

        filas.append({
            "cedula": ced,
            "programa": "jc",
            "cohorte": cohorte,
            "fecha_retiro": fecha_retiro,
            "anio_retiro": anio,
            "motivo": motivo,
            "etapa": etapa,
            "fuente": "sheet_retirados_q10",
        })

    if excluidos:
        log(f"  Exclusión de pruebas: {excluidos} filas quitadas")
    log(f"  JC: {len(filas)} filas de retiro (tras dedupe cedula+cohorte)")
    return filas


# ── Extracción MR ───────────────────────────────────────────────────────────────
def extraer_mr(exclusiones: set) -> list:
    log(f"Leyendo hoja '{HOJA_MR}' del Sheet MR (id {SHEET_MR_ID})...")
    sh = _conectar_sheet(SHEET_MR_ID)
    ws = sh.worksheet(HOJA_MR)
    vals = ws.get_all_values()
    log(f"  {max(len(vals) - 1, 0)} filas leídas (incluye posibles filas vacías de cola).")

    filas, vistos = [], set()
    excluidos = 0
    for r in vals[1:]:
        if len(r) <= IDX_MR_CEDULA:
            continue
        ced = norm_id(r[IDX_MR_CEDULA])
        if not ced:
            continue
        if ced in exclusiones:
            excluidos += 1
            continue

        anio_raw = str(r[IDX_MR_ANIO]).strip() if len(r) > IDX_MR_ANIO else ""
        anio = anio_raw if anio_raw.isdigit() else None
        cohorte = anio or "sin_anio"

        estado = str(r[IDX_MR_ESTADO]).strip() if len(r) > IDX_MR_ESTADO else ""
        motivos = str(r[IDX_MR_MOTIVOS]).strip() if len(r) > IDX_MR_MOTIVOS else ""
        base = " — ".join(p for p in (estado, motivos) if p)
        nota = "[Año-retiro: año de registro de la baja, no cohorte confirmada — ver 007]"
        motivo = (f"{base} {nota}" if base else nota)[:300]

        clave = (ced, cohorte)
        if clave in vistos:
            continue
        vistos.add(clave)

        filas.append({
            "cedula": ced,
            "programa": "mr",
            "cohorte": cohorte,
            "fecha_retiro": None,
            "anio_retiro": anio,
            "motivo": motivo,
            "etapa": None,
            "fuente": "inactivas_mr",
        })

    if excluidos:
        log(f"  Exclusión de pruebas: {excluidos} filas quitadas")
    log(f"  MR: {len(filas)} filas de retiro (tras dedupe cedula+cohorte)")
    return filas


def enmascarar(ced: str) -> str:
    if len(ced) <= 4:
        return "*" * len(ced)
    return ced[:2] + "*" * (len(ced) - 4) + ced[-2:]


def main() -> int:
    ap = argparse.ArgumentParser(description="Retiro individual JC+MR → Supabase retiros")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (.env.local o entorno)")
        print("RESUMEN: jc=0 mr=0 total=0 cargados=0 con_match_participant=0 estado=error")
        return 1

    exclusiones = cargar_exclusiones()

    filas_jc = extraer_jc(exclusiones)
    filas_mr = extraer_mr(exclusiones)
    filas = filas_jc + filas_mr
    log(f"Total combinado: {len(filas)} filas ({len(filas_jc)} JC + {len(filas_mr)} MR)")

    log("Consultando participants en Supabase (lookup por q10_id == cédula)...")
    supa = Supa(url, key)
    participantes = supa.get_todo("/participants?select=id,q10_id")
    q10_a_participant = {p["q10_id"]: p["id"] for p in participantes if p.get("q10_id")}
    log(f"Participantes en Supabase (para enlazar): {len(q10_a_participant)}")

    con_match = 0
    ahora = datetime.now().isoformat(timespec="seconds")
    for fila in filas:
        pid = q10_a_participant.get(fila["cedula"])
        if pid:
            fila["participant_id"] = pid
            con_match += 1
        fila["updated_at"] = ahora
        # Limpia claves None: PostgREST las trataría como NULL explícito, lo cual está
        # bien para columnas nulleables, pero agrupamos por firma de columnas (abajo)
        # así que es más simple omitir las ausentes, igual que sync_postulantes_mr.py.
        for k in list(fila.keys()):
            if fila[k] is None:
                del fila[k]

    log(f"Con match en participants: {con_match} de {len(filas)}")

    if args.dry_run:
        log("Muestra de 5 filas (cédula enmascarada, sin nombres — la tabla retiros no "
            "guarda nombre):")
        for fila in filas[:5]:
            copia = dict(fila)
            copia["cedula"] = enmascarar(copia["cedula"])
            log(f"    {copia}")
        print(f"RESUMEN: jc={len(filas_jc)} mr={len(filas_mr)} total={len(filas)} "
              f"cargados=0 con_match_participant={con_match} estado=dry_run")
        return 0

    grupos: dict = {}
    for fila in filas:
        grupos.setdefault(frozenset(fila), []).append(fila)
    for grupo in grupos.values():
        for i in range(0, len(grupo), LOTE):
            supa._req("POST", "/retiros?on_conflict=cedula,cohorte,programa", grupo[i:i + LOTE],
                      prefer="resolution=merge-duplicates,return=minimal")
    log(f"Cargados: {len(filas)} (en {len(grupos)} grupos de columnas)")

    print(f"RESUMEN: jc={len(filas_jc)} mr={len(filas_mr)} total={len(filas)} "
          f"cargados={len(filas)} con_match_participant={con_match} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
