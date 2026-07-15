# -*- coding: utf-8 -*-
"""
backfill_emoflow_participacion.py — Semanas 1-15 de Emoflow → emoflow_participacion_semanal.

⚠ UNA SOLA VEZ (histórico). El sync diario (`sync_emoflow_participacion.py`) solo captura la
semana EN CURSO desde el bloque agregado de `Estadísticas`, así que el gráfico de evolución del
panel arrancaba plano en la Semana 16. Este script rescata las semanas anteriores desde la
**pestaña `Emoflow` cruda** (gid 175161020) — el registro individual de check-ins semanales — para
que el historial se vea extenso.

Fuente y fidelidad: la pestaña cruda tiene un bloque por semana (`Semana 1..16`), cada uno con
`Email | Nombre | Ciudad | Registro Emoción | Fecha`. `Registro Emoción` es `Si`/`No` (si el
estudiante diligenció su check-in esa semana — NO es la emoción). `completado` = correos únicos con
`Si` por ciudad. Validado contra el bloque agregado de Estadísticas para la Semana 16: coincide en
7 de 9 ciudades, ±1 en las otras 2.

⚠ Por qué el histórico va como CONTEO (`completado`), no como %: el `Real` (denominador) de las
semanas pasadas no existe en ninguna fuente. Usar el `Real` actual daría **>100%** en ciudades cuya
cohorte encogió (CAL: 102 check-ins en Sem.2 vs 93 hoy). El conteo es fiel y no necesita supuesto.
Se guarda `real`/`avance_pct` best-effort (contra el Real actual) por completitud, pero el panel
grafica `completado`. La Semana 16 NO se toca (la maneja el sync diario en vivo).

Uso:
    python backfill_emoflow_participacion.py [--dry-run]

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
from collections import Counter, defaultdict
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

SHEET_ID    = "1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8"
PESTANA_ID  = 175161020          # pestaña 'Emoflow' cruda (registro individual por semana)
USER_AGENT  = "panel-datos-etl/1.0"

# Ciudad (nombre en la hoja) → grupo_ciudad canónico
CIUDAD_MAP = {
    "barranquilla": "BAQ", "bogotá d.c.": "BOG", "bogota d.c.": "BOG", "cali": "CAL",
    "cartagena de indias": "CTG", "medellín": "MED", "medellin": "MED", "guayaquil": "GYL",
    "quito": "QTO", "ciudad de panamá": "PAN", "ciudad de panama": "PAN", "uruguay": "UY",
}


def log(msg: str) -> None:
    print(f"[backfill-emoflow-part] {msg}", flush=True)


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


def req(metodo, url, key, ruta, cuerpo=None, prefer=""):
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json", "User-Agent": USER_AGENT}
    if prefer:
        headers["Prefer"] = prefer
    r = urllib.request.Request(url.rstrip("/") + "/rest/v1" + ruta, method=metodo, headers=headers,
                               data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            d = resp.read()
            return resp.status, json.loads(d) if d else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: "
                           f"{e.read().decode(errors='replace')[:400]}") from None


def parse_fecha(v):
    v = (v or "").strip()
    for f in ("%d/%m/%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(v, f).date()
        except ValueError:
            continue
    return None


def real_actual(url, key):
    """Real (denominador) por ciudad de la corrida en vivo más reciente."""
    filas = req("GET", url, key,
                "/emoflow_participacion_semanal?select=grupo_ciudad,real,fecha_corte"
                "&order=fecha_corte.desc")[1] or []
    if not filas:
        return {}
    ult = filas[0]["fecha_corte"]
    return {f["grupo_ciudad"]: f["real"] for f in filas
            if f["fecha_corte"] == ult and f.get("real")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill semanas 1-15 de participación Emoflow")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log("ERROR: falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY (.env.local)")
        return 1

    creds = Credentials.from_service_account_file(
        RUTA_CREDENCIALES, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    ws = gspread.authorize(creds).open_by_key(SHEET_ID).get_worksheet_by_id(PESTANA_ID)
    log(f"Leyendo pestaña cruda '{ws.title}'...")
    vals = ws.get_all_values()
    hdr, etiquetas = vals[1], vals[0]
    bloques = [i for i, h in enumerate(hdr) if h.strip().lower() == "email"]
    log(f"{len(bloques)} bloques de semana encontrados")

    real = real_actual(url, key)
    if not real:
        log("ADVERTENCIA: no hay Real en vivo — avance_pct quedará NULL")

    filas, fechas_usadas, sin_ciudad = [], {}, 0
    # Semana 16 (último bloque) NO se toca: la maneja el sync diario en vivo.
    for c in bloques[:-1]:
        lbl = etiquetas[c] if c < len(etiquetas) else ""
        m = re.search(r"\d+", lbl)
        semana = int(m.group()) if m else None

        por_ciudad = defaultdict(set)
        fechas = []
        for r in vals[2:]:
            if c < len(r) and r[c].strip() and c + 3 < len(r) and r[c + 3].strip().lower() == "si":
                ciu = r[c + 2].strip().lower() if c + 2 < len(r) else ""
                cod = CIUDAD_MAP.get(ciu)
                if cod:
                    por_ciudad[cod].add(r[c].strip().lower())
                else:
                    sin_ciudad += 1
                d = parse_fecha(r[c + 4]) if c + 4 < len(r) else None
                if d:
                    fechas.append(d)
        if not fechas or not por_ciudad:
            log(f"Semana {semana}: sin datos usables — omitida")
            continue

        fecha_corte = Counter(fechas).most_common(1)[0][0].isoformat()
        if fecha_corte in fechas_usadas:            # garantizar clave única (fecha_corte, ciudad)
            log(f"ERROR: fecha {fecha_corte} colisiona (Sem {semana} y {fechas_usadas[fecha_corte]})")
            return 1
        fechas_usadas[fecha_corte] = semana

        for cod, correos in sorted(por_ciudad.items()):
            completado = len(correos)
            rl = real.get(cod)
            filas.append({
                "fecha_corte": fecha_corte, "semana": semana, "grupo_ciudad": cod,
                "seleccionados": None, "real": rl, "completado": completado,
                "avance_pct": round(100 * completado / rl, 2) if rl else None,
                "fuente": "backfill-crudo",
            })

    log(f"{len(filas)} filas listas ({len(fechas_usadas)} semanas × ciudades) | "
        f"registros sin ciudad mapeable: {sin_ciudad}")
    for sem in sorted(set(f["semana"] for f in filas)):
        fs = [f for f in filas if f["semana"] == sem]
        tot = sum(f["completado"] for f in fs)
        log(f"  Sem {sem:2} ({fs[0]['fecha_corte']}): {tot} check-ins en {len(fs)} ciudades")

    if args.dry_run:
        log("DRY-RUN: no se escribió nada")
        return 0

    _, _ = req("POST", url, key, "/emoflow_participacion_semanal?on_conflict=fecha_corte,grupo_ciudad",
               filas, prefer="resolution=merge-duplicates,return=minimal")
    log(f"Upsert OK: {len(filas)} filas de backfill")
    print(f"RESUMEN: semanas={len(fechas_usadas)} filas={len(filas)} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
