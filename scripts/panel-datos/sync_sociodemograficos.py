# -*- coding: utf-8 -*-
"""
sync_sociodemograficos.py — BD Seguimiento de Monitorias (Sheet vivo) → Supabase participants.

Extrae de la pestaña `Seguimiento` (hub, headers fila 1): ID(c7), Grupo(c2),
Fecha Nacimiento(c11), Edad(c12), Ciudad(c13), Género(c16); y de `Diagnostico`
(headers fila 1): Número de documento(c3) + situación de emprendimiento(c32,
4 categorías). Cruza por cédula normalizada y actualiza SOLO participantes que
ya existen en Supabase (los de la BD que no están en Q10 se reportan, no se crean).

tiene_emprendimiento = (situacion == en_marcha). Al final recomputa agregados.

**2026-07-23: también calcula `en_seguimiento_jc`** (alerta operativa, NO retiro confirmado —
ver COMMENT de la columna / docs/procesos/supabase-estructura.md): el equipo borra primero de
esta pestaña cuando alguien se retira y solo meses después lo refleja en Q10, así que la
ausencia aquí es una señal más fresca que Q10 de "posible retiro sin confirmar". Se calcula
para TODOS los participantes programa=jc en Supabase (no solo los que trae el Sheet, a
diferencia del resto de campos de este script) — por eso corre en un segundo paso separado.
Alcance SOLO JC (decisión explícita: MR no tiene la misma disciplina de borrado, sería ruido).

⚠ PRIVACIDAD: PII en memoria y en tools/ solamente.

**2026-07-21: se dejó de leer el xlsx exportado a mano de Downloads — ahora lee el
Google Sheet en vivo** (mismo Sheet ID que `sync_emoflow_participacion.py`, id
`1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8`, pestañas `Seguimiento` + `Diagnostico`).
Esto permite encadenarlo a un schedule n8n sin depender de que alguien descargue el
xlsx primero. Ver docs/procesos/bd-seguimiento-monitorias.md.

Uso:
    python sync_sociodemograficos.py [--dry-run]
Consola (parseable por n8n):
    RESUMEN: actualizados=N sin_match_supabase=X sin_datos=Y estado=exito

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
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

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_CREDENCIALES = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion",
                                 "credenciales_service_account.json")
SHEET_ID          = "1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8"  # BD Seguimiento de Monitorias
RUTA_REPORTE      = os.path.join(PROYECTO_ROOT, "tools",
                                 f"sociodemograficos_report_{datetime.now():%Y%m%d}.json")

USER_AGENT = "panel-datos-etl/1.0"  # Supabase rechaza secrets con UA de navegador
LOTE       = 500

# Diagnostico c32 → enum emprendimiento_situacion (match por prefijo)
MAPA_EMPRENDIMIENTO = [
    ("sí, tengo un emprendimiento en marcha", "en_marcha"),
    ("tengo una idea de negocio",             "idea"),
    ("me llama la atención emprender",        "interesado"),
    ("no me interesa emprender",              "no_interesado"),
]


def log(msg: str) -> None:
    print(f"[sync-sociodem] {msg}", flush=True)


def norm_id(valor) -> str:
    """Cédula a solo dígitos. Gotcha openpyxl: las celdas numéricas llegan como
    float (1041774123.0) — str() directo mete '.0' y el strip de no-dígitos lo
    convertía en un CERO EXTRA al final (10417741230 ≠ 1041774123)."""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\D", "", str(valor))


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


class Supa:
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.key = key

    def _req(self, metodo: str, ruta: str, cuerpo=None, prefer: str = ""):
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}",
                   "Content-Type": "application/json", "User-Agent": USER_AGENT}
        if prefer:
            headers["Prefer"] = prefer
        req = urllib.request.Request(self.base + ruta, method=metodo, headers=headers,
                                     data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                datos = resp.read()
                return resp.status, json.loads(datos) if datos else None
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: "
                               f"{e.read().decode(errors='replace')[:500]}") from None

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            _, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page


def _parse_fecha(valor: str) -> str | None:
    """'DD/MM/YYYY' (formato del Sheet, locale es) → 'YYYY-MM-DD'. None si no parsea."""
    v = str(valor).strip()
    if not v:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _conectar_sheet():
    creds = Credentials.from_service_account_file(
        RUTA_CREDENCIALES, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    return gspread.authorize(creds).open_by_key(SHEET_ID)


def extraer_bd() -> tuple[dict, set]:
    """({cedula: {genero, fecha_nacimiento, edad, ciudad, grupo_ciudad,
                  situacion_emprendimiento, tiene_emprendimiento}}, {cedulas presentes en Seguimiento})

    El segundo valor (presencia cruda) es independiente del filtro len(r)<16 de abajo —
    para "está o no en Seguimiento" solo importa que la fila tenga cédula en c7, no que
    tenga las 16 columnas completas de datos sociodemográficos."""
    log(f"Leyendo Sheet vivo (id {SHEET_ID})...")
    sh = _conectar_sheet()

    filas = sh.worksheet("Seguimiento").get_all_values()
    cedulas_seguimiento = {norm_id(r[6]) for r in filas[1:] if len(r) > 6 and norm_id(r[6])}

    datos: dict[str, dict] = {}
    for r in filas[1:]:
        if len(r) < 16:
            continue
        ced = norm_id(r[6])          # c7 ID
        if not ced:
            continue
        edad = r[11].strip()         # c12 Edad
        datos[ced] = {
            "grupo_ciudad": r[1].strip() or None,          # c2 Grupo
            "fecha_nacimiento": _parse_fecha(r[10]),        # c11 Fecha Nacimiento
            # rango plausible: la BD trae "0" para desconocido (3 casos reales, 2026-07-23)
            "edad": int(edad) if edad.isdigit() and 10 <= int(edad) <= 90 else None,
            "ciudad": r[12].strip() or None,                # c13 Ciudad
            "genero": r[15].strip() or None,                # c16 Género
        }
    log(f"Seguimiento: {len(datos)} cédulas con datos ({len(cedulas_seguimiento)} cédulas presentes en total)")

    filas2 = sh.worksheet("Diagnostico").get_all_values()
    n_emp = 0
    for r in filas2[1:]:
        if len(r) < 32:
            continue
        ced = norm_id(r[2])          # c3 Número de documento
        if not ced or not r[31].strip():   # c32 situación emprendimiento
            continue
        texto = r[31].strip().lower()
        situacion = next((v for pref, v in MAPA_EMPRENDIMIENTO if texto.startswith(pref)), None)
        if situacion is None:
            continue
        fila = datos.setdefault(ced, {})
        fila["situacion_emprendimiento"] = situacion
        fila["tiene_emprendimiento"] = situacion == "en_marcha"
        n_emp += 1
    log(f"Diagnostico: {n_emp} respuestas de emprendimiento mapeadas")
    return datos, cedulas_seguimiento


def main() -> int:
    ap = argparse.ArgumentParser(description="BD monitorias → Supabase participants")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cargar_env_local()
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        return 1

    datos, cedulas_seguimiento = extraer_bd()
    supa = Supa(url, key)
    # q10_id → nombre actual: el eco del nombre satisface el NOT NULL del INSERT
    # propuesto en el upsert (Postgres valida constraints ANTES de resolver el conflicto)
    existentes = {r["q10_id"]: r["nombre"]
                  for r in supa.get_todo("/participants?select=q10_id,nombre")}
    log(f"Participantes en Supabase: {len(existentes)}")

    # en_seguimiento_jc: se calcula para los participantes programa=jc de la COHORTE ACTUAL
    # (no todo el histórico — el Sheet "Seguimiento" solo trackea el año en curso; aplicar
    # esto a cohortes 2023-2025 marcaría como "alerta de retiro" a miles de egresados
    # normales, que nunca estuvieron ni deberían estar en ese Sheet). Alcance SOLO JC.
    ANIO_COHORTE_ACTUAL = str(datetime.now().year)
    jc_participantes = supa.get_todo(
        "/participants?select=q10_id,nombre,enrollments!inner(courses!inner(programa,cohorte))"
        f"&enrollments.courses.programa=eq.jc&enrollments.courses.cohorte=eq.{ANIO_COHORTE_ACTUAL}")
    jc_q10_ids = {r["q10_id"] for r in jc_participantes if r.get("q10_id")}
    log(f"Participantes JC cohorte {ANIO_COHORTE_ACTUAL} (para en_seguimiento_jc): {len(jc_q10_ids)}")

    hoy = datetime.now().date().isoformat()
    filas_seguimiento = [
        {"q10_id": ced, "nombre": existentes[ced],
         "en_seguimiento_jc": ced in cedulas_seguimiento,
         "fecha_verificacion_seguimiento": hoy,
         "updated_at": datetime.now().isoformat(timespec="seconds")}
        for ced in sorted(jc_q10_ids) if ced in existentes
    ]
    alertas_retiro_pendiente = sum(1 for f in filas_seguimiento if not f["en_seguimiento_jc"])
    log(f"en_seguimiento_jc: {len(filas_seguimiento) - alertas_retiro_pendiente} activos en Sheet · "
        f"{alertas_retiro_pendiente} SIN aparecer en Seguimiento (alerta de retiro pendiente de confirmar)")

    filas, sin_match, sin_datos, stats = [], [], 0, Counter()
    for ced, d in sorted(datos.items()):
        limpio = {k: v for k, v in d.items() if v is not None}
        if not limpio:
            sin_datos += 1
            continue
        if ced not in existentes:
            sin_match.append(ced)   # en BD monitorias pero no en Q10 (retirados, típicamente)
            continue
        filas.append({"q10_id": ced, "nombre": existentes[ced], **limpio,
                      "updated_at": datetime.now().isoformat(timespec="seconds")})
        for k in limpio:
            stats[k] += 1

    log(f"A actualizar: {len(filas)} · sin match en Supabase: {len(sin_match)} · sin datos: {sin_datos}")
    log("Campos: " + ", ".join(f"{k}={v}" for k, v in stats.most_common()))

    if args.dry_run:
        print(f"RESUMEN: actualizados=0 sin_match_supabase={len(sin_match)} "
              f"sin_datos={sin_datos} alertas_retiro_pendiente={alertas_retiro_pendiente} "
              f"estado=dry_run")
        return 0

    # upsert por q10_id: en filas existentes PostgREST solo toca las columnas provistas.
    # Gotcha PGRST102: el bulk exige claves idénticas en todas las filas del batch →
    # agrupar por conjunto de claves (así "vacío nunca sobreescribe" se mantiene:
    # jamás mandamos null explícito por un dato que la BD no trae).
    grupos: dict[frozenset, list] = {}
    for fila in filas:
        grupos.setdefault(frozenset(fila), []).append(fila)
    for claves, grupo in grupos.items():
        for i in range(0, len(grupo), LOTE):
            supa._req("POST", "/participants?on_conflict=q10_id", grupo[i:i + LOTE],
                      prefer="resolution=merge-duplicates,return=minimal")
    log(f"Actualizados: {len(filas)} (en {len(grupos)} grupos de columnas)")

    # en_seguimiento_jc: mismo booleano+fecha para todos → cabe en un solo grupo de columnas
    for i in range(0, len(filas_seguimiento), LOTE):
        supa._req("POST", "/participants?on_conflict=q10_id", filas_seguimiento[i:i + LOTE],
                  prefer="resolution=merge-duplicates,return=minimal")
    log(f"en_seguimiento_jc actualizado: {len(filas_seguimiento)} participantes JC")

    _, agg = supa._req("POST", "/rpc/recompute_aggregates", {})
    log(f"Agregados recomputados: {agg}")

    with open(RUTA_REPORTE, "w", encoding="utf-8") as f:
        json.dump({"generado": datetime.now().isoformat(timespec="seconds"),
                   "actualizados": len(filas), "campos": dict(stats),
                   "sin_match_supabase": sorted(sin_match), "sin_datos": sin_datos,
                   "alertas_retiro_pendiente": alertas_retiro_pendiente,
                   "cedulas_alerta_retiro_pendiente": sorted(
                       f["q10_id"] for f in filas_seguimiento if not f["en_seguimiento_jc"])},
                  f, ensure_ascii=False, indent=1)
    log(f"Reporte → {RUTA_REPORTE}")

    print(f"RESUMEN: actualizados={len(filas)} sin_match_supabase={len(sin_match)} "
          f"sin_datos={sin_datos} alertas_retiro_pendiente={alertas_retiro_pendiente} "
          f"estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
