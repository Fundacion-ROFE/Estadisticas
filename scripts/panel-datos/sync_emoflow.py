# -*- coding: utf-8 -*-
"""
sync_emoflow.py — Pestaña `+Ingresos-EmoFlow` (Sheet manual) → Supabase `emoflow_ingresos`.

Emoflow es la herramienta de estado de ánimo de los estudiantes. Hoy la usamos como
proxy de "calidad de estudiante" a través de los INGRESOS AL SISTEMA (contador
acumulado por estudiante).

⚠ LLAVE DE CRUCE: el correo. Emoflow NO expone la cédula, así que el email
normalizado (lower + trim) es la única unión posible con `participants`. Los correos
sin match se cargan igual con `participant_id = NULL` (quedan en la tabla, no se
pierden, y no se crean participants desde aquí — Q10 es la fuente de verdad de quién
existe).

El `Area` de Emoflow se mapea a los códigos canónicos de `grupo_ciudad`
(BAQ/BOG/CAL/CTG/MED/GYL/QTO/PAN/UY) para que el filtro por ciudad del panel funcione
igual sobre estos datos.

⚠ PRIVACIDAD: la tabla lleva email/nombre (PII) → RLS sin lectura anónima. El panel
público consume solo las vistas agregadas `v_emoflow_resumen`, `v_emoflow_por_ciudad`
y `v_emoflow_bandas`.

Uso:
    python sync_emoflow.py [--dry-run]
Consola (parseable por n8n):
    RESUMEN: filas=N con_match=M sin_match=X estado=exito

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
from datetime import date, datetime

try:
    import truststore
    truststore.inject_into_ssl()          # SSL corporativo (convención del proyecto)
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
RUTA_REPORTE      = os.path.join(PROYECTO_ROOT, "tools",
                                 f"emoflow_report_{datetime.now():%Y%m%d}.json")

SHEET_ID    = "1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8"   # Sheet manual (mismo de Avance)
PESTANA_ID  = 1288133311                                        # +Ingresos-EmoFlow
USER_AGENT  = "panel-datos-etl/1.0"   # Supabase rechaza secrets con UA de navegador
LOTE        = 500

# Area (como la escribe Emoflow) → grupo_ciudad canónico del panel
MAPA_GRUPO = {
    "barranquilla":          "BAQ",
    "bogotá d.c.":           "BOG",
    "cali":                  "CAL",
    "cartagena de indias":   "CTG",
    "medellín":              "MED",
    "guayaquil":             "GYL",
    "quito":                 "QTO",
    "ciudad de panamá":      "PAN",
    "uruguay":               "UY",
}

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def log(msg: str) -> None:
    print(f"[sync-emoflow] {msg}", flush=True)


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
        """GET paginado (PostgREST corta en ~1000 filas)."""
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            _, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page

    def upsert(self, tabla: str, filas: list, conflicto: str) -> int:
        for i in range(0, len(filas), LOTE):
            self._req("POST", f"/{tabla}?on_conflict={conflicto}", filas[i:i + LOTE],
                      prefer="resolution=merge-duplicates,return=minimal")
        return len(filas)


def norm_email(valor: str) -> str:
    return (valor or "").strip().lower()


def parse_fecha(valor: str):
    """`Ultimo ingreso` llega como d/m/Y y a veces con hora (d/m/Y H:M)."""
    v = (valor or "").strip()
    if not v:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def leer_pestana() -> tuple[list[dict], dict]:
    """+Ingresos-EmoFlow → filas normalizadas. Headers fila 1:
    Usuario | Nombre | Area | Ingresos al sistema | Ultimo ingreso"""
    creds = Credentials.from_service_account_file(
        RUTA_CREDENCIALES,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    ws = gspread.authorize(creds).open_by_key(SHEET_ID).get_worksheet_by_id(PESTANA_ID)
    log(f"Leyendo pestaña '{ws.title}'...")

    crudas = ws.get_all_values()[1:]
    filas, avisos = [], Counter()
    vistos: dict[str, dict] = {}

    for cruda in crudas:
        if not cruda or not cruda[0].strip():
            continue
        email = norm_email(cruda[0])
        if not RE_EMAIL.match(email):
            avisos["email_invalido"] += 1
            continue

        area = (cruda[2].strip() if len(cruda) > 2 else "") or None
        grupo = MAPA_GRUPO.get(area.lower()) if area else None
        if area and not grupo:
            avisos["area_desconocida"] += 1

        crudo_ing = (cruda[3].strip() if len(cruda) > 3 else "")
        if not crudo_ing.isdigit():
            avisos["ingresos_no_numerico"] += 1
            continue

        fila = {
            "email":          email,
            "nombre":         (cruda[1].strip() if len(cruda) > 1 else "") or None,
            "area":           area,
            "grupo_ciudad":   grupo,
            "ingresos":       int(crudo_ing),
            "ultimo_ingreso": parse_fecha(cruda[4] if len(cruda) > 4 else ""),
            "fecha_corte":    date.today().isoformat(),
        }

        # Duplicado de correo en la hoja → gana el de más ingresos (keepMax, patrón del proyecto)
        previo = vistos.get(email)
        if previo:
            avisos["email_duplicado"] += 1
            if fila["ingresos"] <= previo["ingresos"]:
                continue
            filas[filas.index(previo)] = fila
            vistos[email] = fila
            continue

        vistos[email] = fila
        filas.append(fila)

    log(f"{len(filas)} filas válidas | avisos: {dict(avisos) or 'ninguno'}")
    return filas, dict(avisos)


def main() -> int:
    ap = argparse.ArgumentParser(description="Emoflow (+Ingresos) → Supabase")
    ap.add_argument("--dry-run", action="store_true", help="no escribe en Supabase")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log("ERROR: falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY (.env.local)")
        print("RESUMEN: filas=0 con_match=0 sin_match=0 estado=error")
        return 1

    filas, avisos = leer_pestana()
    if not filas:
        log("ERROR: la pestaña no devolvió filas válidas")
        print("RESUMEN: filas=0 con_match=0 sin_match=0 estado=error")
        return 1

    supa = Supa(url, key)

    # participants.email → id  (la única llave común con Emoflow)
    log("Resolviendo participant_id por correo...")
    por_email: dict[str, str] = {}
    for p in supa.get_todo("/participants?select=id,email"):
        e = norm_email(p.get("email"))
        if e:
            por_email.setdefault(e, p["id"])   # 1er match gana (emails únicos en participants)

    sin_match = []
    for fila in filas:
        pid = por_email.get(fila["email"])
        fila["participant_id"] = pid
        if not pid:
            sin_match.append(fila["email"])

    con_match = len(filas) - len(sin_match)
    pct = con_match / len(filas) * 100
    log(f"cruce por correo: {con_match}/{len(filas)} ({pct:.1f}%) | sin match: {len(sin_match)}")

    reporte = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "filas": len(filas), "con_match": con_match, "sin_match": len(sin_match),
        "pct_match": round(pct, 1), "avisos": avisos,
        "emails_sin_match": sorted(sin_match),   # PII → tools/ (gitignoreado)
    }
    os.makedirs(os.path.dirname(RUTA_REPORTE), exist_ok=True)
    with open(RUTA_REPORTE, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    log(f"Reporte → {os.path.relpath(RUTA_REPORTE, PROYECTO_ROOT)}")

    if args.dry_run:
        log("DRY-RUN: no se escribió nada en Supabase")
        print(f"RESUMEN: filas={len(filas)} con_match={con_match} "
              f"sin_match={len(sin_match)} estado=dry-run")
        return 0

    log(f"Upsert de {len(filas)} filas en emoflow_ingresos (on_conflict=email)...")
    supa.upsert("emoflow_ingresos", filas, "email")

    log("OK")
    print(f"RESUMEN: filas={len(filas)} con_match={con_match} "
          f"sin_match={len(sin_match)} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
