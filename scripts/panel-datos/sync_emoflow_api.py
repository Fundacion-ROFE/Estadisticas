# -*- coding: utf-8 -*-
"""
sync_emoflow_api.py — Emoflow API (registro-ingresos) → Supabase `emoflow_ingresos`.

Automatización sin Sheet intermedio:
  1. POST /login → PHPSESSID
  2. GET /admin/registro-ingresos-exportar → CSV con todos los ingresos
  3. Agregar por email (suma ingresos, obtiene último ingreso)
  4. Upsert a Supabase emoflow_ingresos (idéntico a sync_emoflow.py)

Credenciales:
  - EMOFLOW_URL (default: https://emoflow.sanumbe.com)
  - EMOFLOW_USER (nombre de usuario)
  - EMOFLOW_PASSWORD (contraseña)
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE_KEY

Uso:
    python sync_emoflow_api.py [--dry-run]

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from io import StringIO

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_REPORTE = os.path.join(
    PROYECTO_ROOT, "tools",
    f"emoflow_api_report_{datetime.now():%Y%m%d_%H%M%S}.json"
)

EMOFLOW_BASE_URL = "https://emoflow.sanumbe.com"
USER_AGENT = "panel-datos-etl/1.0"
LOTE = 500

# Area (como en Emoflow) → grupo_ciudad canónico
MAPA_GRUPO = {
    "barranquilla": "BAQ",
    "bogotá d.c.": "BOG",
    "bogotá d.c": "BOG",
    "cali": "CAL",
    "cartagena de indias": "CTG",
    "medellín": "MED",
    "guayaquil": "GYL",
    "quito": "QTO",
    "ciudad de panamá": "PAN",
    "uruguay": "UY",
}

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def log(msg: str) -> None:
    print(f"[sync-emoflow-api] {msg}", flush=True)


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
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        if prefer:
            headers["Prefer"] = prefer
        req = urllib.request.Request(
            self.base + ruta,
            method=metodo,
            headers=headers,
            data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                datos = resp.read()
                return resp.status, json.loads(datos) if datos else None
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"HTTP {e.code} en {metodo} {ruta}: "
                f"{e.read().decode(errors='replace')[:500]}"
            ) from None

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        """GET paginado."""
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
            self._req(
                "POST",
                f"/{tabla}?on_conflict={conflicto}",
                filas[i : i + LOTE],
                prefer="resolution=merge-duplicates,return=minimal",
            )
        return len(filas)


def norm_email(valor: str) -> str:
    return (valor or "").strip().lower()


def parse_fecha(valor: str):
    """Fecha Emoflow llega como 'd/m/Y H:M:S'."""
    v = (valor or "").strip()
    if not v:
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def descargar_emoflow_csv(usuario: str, contrasena: str) -> str:
    """Login a Emoflow y descarga CSV de ingresos."""
    log("Conectando a Emoflow...")
    session = requests.Session()

    # Login
    try:
        resp = session.post(
            f"{EMOFLOW_BASE_URL}/login",
            data={"usuario": usuario, "password": contrasena},
            timeout=30,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Login falló (status {resp.status_code})")
    except requests.RequestException as e:
        raise RuntimeError(f"Error conectando a Emoflow: {e}") from None

    log("Login exitoso")

    # Descargar CSV
    log("Descargando registro de ingresos...")
    try:
        resp = session.get(
            f"{EMOFLOW_BASE_URL}/admin/registro-ingresos-exportar",
            params={
                "scope": "all",
                "participacion_estado": "todos",
                "empresa_participacion": "Fundación ROFÉ",
            },
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Descarga falló (status {resp.status_code})")
        if "usuario" not in resp.text.lower():
            raise RuntimeError("Respuesta no contiene datos esperados")
    except requests.RequestException as e:
        raise RuntimeError(f"Error descargando CSV: {e}") from None

    log(f"CSV descargado ({len(resp.text)} bytes)")
    return resp.text


def procesar_csv_emoflow(csv_text: str) -> tuple[list[dict], dict]:
    """Parsea CSV y agrega ingresos por email."""
    reader = csv.DictReader(StringIO(csv_text))
    registros_crudos = list(reader)
    log(f"Registros brutos leídos: {len(registros_crudos)}")

    # Agregar por email
    por_email: dict[str, dict] = {}
    avisos = Counter()

    for crudo in registros_crudos:
        # Headers pueden tener BOM — normalizarlos
        crudo = {k.lstrip("﻿"): v for k, v in crudo.items()}

        email = norm_email(crudo.get("Usuario", ""))
        if not RE_EMAIL.match(email):
            avisos["email_invalido"] += 1
            continue

        # Nombre y área
        nombre = (crudo.get("Nombre", "") or "").strip() or None
        area = (crudo.get("Area", "") or "").strip() or None
        grupo = MAPA_GRUPO.get(area.lower()) if area else None
        if area and not grupo:
            avisos["area_desconocida"] += 1

        # Fecha de ingreso
        fecha_ingreso = crudo.get("Fecha emociones", "")

        # Agregar o actualizar
        if email in por_email:
            por_email[email]["ingresos"] += 1
            # Actualizar último ingreso si es más reciente
            if fecha_ingreso:
                try:
                    fecha_nueva = datetime.strptime(
                        fecha_ingreso, "%Y-%m-%d %H:%M:%S"
                    )
                    fecha_actual = (
                        datetime.fromisoformat(por_email[email]["ultimo_ingreso"])
                        if por_email[email]["ultimo_ingreso"]
                        else None
                    )
                    if not fecha_actual or fecha_nueva > fecha_actual:
                        por_email[email]["ultimo_ingreso"] = parse_fecha(fecha_ingreso)
                except (ValueError, TypeError):
                    pass
        else:
            por_email[email] = {
                "email": email,
                "nombre": nombre,
                "area": area,
                "grupo_ciudad": grupo,
                "ingresos": 1,
                "ultimo_ingreso": parse_fecha(fecha_ingreso),
                "fecha_corte": date.today().isoformat(),
            }

    filas = list(por_email.values())
    log(f"{len(filas)} usuarios únicos | avisos: {dict(avisos) or 'ninguno'}")
    return filas, dict(avisos)


def main() -> int:
    ap = argparse.ArgumentParser(description="Emoflow API → Supabase")
    ap.add_argument("--dry-run", action="store_true", help="no escribe en Supabase")
    args = ap.parse_args()

    cargar_env_local()

    # Credenciales Emoflow
    emoflow_user = os.environ.get("EMOFLOW_USER")
    emoflow_password = os.environ.get("EMOFLOW_PASSWORD")
    if not emoflow_user or not emoflow_password:
        log("ERROR: falta EMOFLOW_USER o EMOFLOW_PASSWORD (.env.local)")
        print("RESUMEN: filas=0 con_match=0 sin_match=0 estado=error")
        return 1

    # Credenciales Supabase
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log("ERROR: falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY (.env.local)")
        print("RESUMEN: filas=0 con_match=0 sin_match=0 estado=error")
        return 1

    # Descargar CSV
    try:
        csv_text = descargar_emoflow_csv(emoflow_user, emoflow_password)
    except RuntimeError as e:
        log(f"ERROR: {e}")
        print("RESUMEN: filas=0 con_match=0 sin_match=0 estado=error")
        return 1

    # Procesar
    filas, avisos = procesar_csv_emoflow(csv_text)
    if not filas:
        log("ERROR: no se generaron filas válidas")
        print("RESUMEN: filas=0 con_match=0 sin_match=0 estado=error")
        return 1

    # Conectar a Supabase
    supa = Supa(url, key)

    # Resolver participant_id por email
    log("Resolviendo participant_id por correo...")
    por_email_supa: dict[str, str] = {}
    for p in supa.get_todo("/participants?select=id,email"):
        e = norm_email(p.get("email"))
        if e:
            por_email_supa.setdefault(e, p["id"])

    sin_match = []
    for fila in filas:
        pid = por_email_supa.get(fila["email"])
        fila["participant_id"] = pid
        if not pid:
            sin_match.append(fila["email"])

    con_match = len(filas) - len(sin_match)
    pct = con_match / len(filas) * 100 if filas else 0
    log(
        f"cruce por correo: {con_match}/{len(filas)} ({pct:.1f}%) | sin match: {len(sin_match)}"
    )

    reporte = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "fuente": "emoflow_api",
        "filas": len(filas),
        "con_match": con_match,
        "sin_match": len(sin_match),
        "pct_match": round(pct, 1),
        "avisos": avisos,
        "emails_sin_match": sorted(sin_match),
    }
    os.makedirs(os.path.dirname(RUTA_REPORTE), exist_ok=True)
    with open(RUTA_REPORTE, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    log(f"Reporte → {os.path.relpath(RUTA_REPORTE, PROYECTO_ROOT)}")

    if args.dry_run:
        log("DRY-RUN: no se escribió nada en Supabase")
        print(
            f"RESUMEN: filas={len(filas)} con_match={con_match} "
            f"sin_match={len(sin_match)} estado=dry-run"
        )
        return 0

    log(f"Upsert de {len(filas)} filas en emoflow_ingresos (on_conflict=email)...")
    supa.upsert("emoflow_ingresos", filas, "email")

    # Historial agregado (igual que sync_emoflow.py)
    hoy = date.today().isoformat()
    resumen = supa.get_todo("/v_emoflow_resumen?select=*")
    if resumen:
        r = resumen[0]
        fila_h = {
            "fecha": hoy,
            "participantes": r["participantes"],
            "con_match_supabase": r["con_match_supabase"],
            "ingresos_promedio": r["ingresos_promedio"],
            "ingresos_mediana": r["ingresos_mediana"],
            "ingresos_max": r["ingresos_max"],
            "activos_7d": r["activos_7d"],
            "activos_14d": r["activos_14d"],
            "inactivos_30d": r["inactivos_30d"],
            "fuente": "emoflow-api",
        }
        supa.upsert("historial_emoflow", [fila_h], "fecha")
        log(
            f"Historial Emoflow: snapshot {hoy} (participantes={r['participantes']})"
        )

    filas_hc = [
        {
            "fecha": hoy,
            "grupo_ciudad": c["grupo_ciudad"],
            "participantes": c["participantes"],
            "ingresos_promedio": c["ingresos_promedio"],
            "ingresos_mediana": c["ingresos_mediana"],
            "activos_7d": c["activos_7d"],
            "inactivos_30d": c["inactivos_30d"],
            "fuente": "emoflow-api",
        }
        for c in supa.get_todo("/v_emoflow_por_ciudad?select=*")
    ]
    if filas_hc:
        supa.upsert("historial_emoflow_ciudad", filas_hc, "fecha,grupo_ciudad")
        log(f"Historial Emoflow ciudad: snapshot {hoy} con {len(filas_hc)} ciudades")

    log("OK")
    print(
        f"RESUMEN: filas={len(filas)} con_match={con_match} "
        f"sin_match={len(sin_match)} estado=exito"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
