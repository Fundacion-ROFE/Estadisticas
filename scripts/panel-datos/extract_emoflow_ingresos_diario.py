# -*- coding: utf-8 -*-
"""
extract_emoflow_ingresos_diario.py — Serie DIARIA REAL de ingresos a Emoflow por ciudad.

Emoflow expone en /admin/registro-ingresos-exportar un CSV con UN evento por fila
(cada ingreso/check-in de "emociones") con su timestamp exacto y la ciudad (Area).
De ahí derivamos, sin inventar nada:
  - ingresos por (día, ciudad)  → serie de tiempo real
  - usuarios únicos activos por (día, ciudad)
  - fila NACIONAL por día (agregado de todas las ciudades)

Cubre TODO el histórico presente en el CSV (≈120 días), así que una sola corrida
hace el backfill real y reemplaza el backfill plano de historial_emoflow.

Columnas del CSV: Usuario | Nombre | Empresa | Area | Fecha emociones |
                  Fechas bienestar | Dimensiones bienestar completadas
(bienestar viene vacío para esta organización — solo se miden ingresos.)

Uso:
    python extract_emoflow_ingresos_diario.py [--dry-run]

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import csv
import io
import json
import os
import sys
import urllib.request
from collections import defaultdict
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

import requests

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV = os.path.join(PROYECTO_ROOT, ".env.local")

EMOFLOW_BASE_URL = "https://emoflow.sanumbe.com"
USER_AGENT = "panel-datos-etl/1.0"

# Area (texto de Emoflow) → grupo_ciudad canónico (mismos códigos del panel).
MAPA_GRUPO = {
    "barranquilla": "BAQ",
    "bogotá d.c.": "BOG",
    "bogota d.c.": "BOG",
    "cali": "CAL",
    "cartagena de indias": "CTG",
    "medellín": "MED",
    "medellin": "MED",
    "guayaquil": "GYL",
    "quito": "QTO",
    "ciudad de panamá": "PAN",
    "ciudad de panama": "PAN",
    "uruguay": "UY",
}


def log(msg: str) -> None:
    print(f"[emoflow-diario] {msg}", flush=True)


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


def descargar_csv(usuario: str, contrasena: str) -> str:
    log("Login en Emoflow...")
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    r = s.post(
        f"{EMOFLOW_BASE_URL}/login",
        data={"usuario": usuario, "password": contrasena},
        timeout=30,
        allow_redirects=True,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Login falló (status {r.status_code})")
    log("Descargando registro de ingresos (CSV)...")
    r = s.get(
        f"{EMOFLOW_BASE_URL}/admin/registro-ingresos-exportar"
        "?scope=all&participacion_estado=todos&empresa_participacion="
        "&participacion_desde=&participacion_hasta=",
        timeout=90,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Descarga falló (status {r.status_code})")
    log(f"CSV recibido ({len(r.text):,} bytes)")
    return r.text


def agregar(csv_text: str) -> list:
    """CSV de eventos → filas diarias por ciudad + NACIONAL."""
    reader = csv.DictReader(io.StringIO(csv_text))
    # ingresos[(fecha, grupo)] = int ; usuarios[(fecha, grupo)] = set(email)
    ingresos = defaultdict(int)
    usuarios = defaultdict(set)

    total = 0
    for row in reader:
        # la primera columna trae BOM: '﻿Usuario'
        email = (row.get("Usuario") or row.get("﻿Usuario") or "").strip().lower()
        area = (row.get("Area") or "").strip()
        femo = (row.get("Fecha emociones") or "").strip()
        if not femo:
            continue
        fecha = femo[:10]  # 'YYYY-MM-DD'
        if len(fecha) != 10:
            continue
        total += 1
        grupo = MAPA_GRUPO.get(area.lower())

        # NACIONAL siempre
        ingresos[(fecha, "NACIONAL")] += 1
        if email:
            usuarios[(fecha, "NACIONAL")].add(email)
        # por ciudad (si mapea)
        if grupo:
            ingresos[(fecha, grupo)] += 1
            if email:
                usuarios[(fecha, grupo)].add(email)

    filas = []
    for (fecha, grupo), n in ingresos.items():
        filas.append({
            "fecha": fecha,
            "grupo_ciudad": grupo,
            "ingresos": n,
            "usuarios_activos": len(usuarios[(fecha, grupo)]),
            "fuente": "emoflow-csv",
        })
    log(f"Eventos procesados: {total:,} → filas (día×ciudad): {len(filas):,}")
    return filas


def upsert_supabase(url: str, key: str, filas: list) -> None:
    base = url.rstrip("/") + "/rest/v1/emoflow_ingresos_diario?on_conflict=fecha,grupo_ciudad"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    for i in range(0, len(filas), 500):
        lote = filas[i:i + 500]
        req = urllib.request.Request(base, method="POST", headers=headers,
                                     data=json.dumps(lote).encode())
        with urllib.request.urlopen(req, timeout=120):
            pass
    log(f"Upsert OK: {len(filas):,} filas")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cargar_env_local()

    user = os.environ.get("EMOFLOW_USER")
    pwd = os.environ.get("EMOFLOW_PASSWORD")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (user and pwd):
        log("ERROR: falta EMOFLOW_USER/EMOFLOW_PASSWORD")
        print("RESUMEN: estado=error"); return 1
    if not (url and key):
        log("ERROR: falta SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY")
        print("RESUMEN: estado=error"); return 1

    try:
        csv_text = descargar_csv(user, pwd)
    except RuntimeError as e:
        log(f"ERROR: {e}"); print("RESUMEN: estado=error"); return 1

    filas = agregar(csv_text)
    if not filas:
        log("ERROR: no se generaron filas"); print("RESUMEN: estado=error"); return 1

    # resumen rápido para el log
    dias = sorted({f["fecha"] for f in filas})
    nac = [f for f in filas if f["grupo_ciudad"] == "NACIONAL"]
    log(f"Rango: {dias[0]} → {dias[-1]} ({len(dias)} días) · filas NACIONAL: {len(nac)}")

    if args.dry_run:
        log("DRY-RUN: no se escribe")
        print(f"RESUMEN: filas={len(filas)} dias={len(dias)} estado=dry-run"); return 0

    upsert_supabase(url, key, filas)
    print(f"RESUMEN: filas={len(filas)} dias={len(dias)} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
