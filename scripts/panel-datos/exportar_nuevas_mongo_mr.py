# -*- coding: utf-8 -*-
"""
exportar_nuevas_mongo_mr.py — uso único: de las cédulas de mujeres-rofe-db.Users (2023/2024)
que NO están en postulantes_mr, exporta un Excel a Downloads con los datos de contacto.

No escribe en Supabase ni en Mongo. Lee scripts/panel-datos/../../tools/mongo_mr_historico_payload.json
(ya extraído) + consulta postulantes_mr de solo lectura para saber cuáles son nuevas.
"""

import io
import json
import os
import sys
import urllib.error
import urllib.request

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from openpyxl import Workbook

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_PAYLOAD      = os.path.join(PROYECTO_ROOT, "tools", "mongo_mr_historico_payload.json")
RUTA_SALIDA       = os.path.join(os.path.expanduser("~"), "Downloads", "mongo_mr_nuevas_2023_2024.xlsx")

USER_AGENT = "panel-datos-etl/1.0"


def cargar_env_local() -> None:
    with open(RUTA_ENV, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def get_todo(base, key, ruta, page=1000):
    filas, offset = [], 0
    sep = "&" if "?" in ruta else "?"
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT}
    while True:
        req = urllib.request.Request(f"{base}/rest/v1{ruta}{sep}limit={page}&offset={offset}", headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            lote = json.loads(resp.read())
        filas.extend(lote)
        if len(lote) < page:
            return filas
        offset += page


def main() -> int:
    cargar_env_local()
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    with open(RUTA_PAYLOAD, encoding="utf-8") as f:
        payload = json.load(f)
    por_anio = payload["por_anio"]

    existentes = {r["cedula"] for r in get_todo(url, key, "/postulantes_mr?select=cedula")}

    wb = Workbook()
    ws = wb.active
    ws.title = "Nuevas MR 2023-2024"
    ws.append(["cohorte", "cedula", "nombre", "email", "celular", "ciudad"])

    total = 0
    for anio in ("2023", "2024"):
        for ced, d in sorted(por_anio.get(anio, {}).items()):
            if ced in existentes:
                continue
            ws.append([anio, ced, d.get("nombre"), d.get("email"), d.get("celular"), d.get("ciudad")])
            total += 1

    wb.save(RUTA_SALIDA)
    print(f"RESUMEN: filas={total} archivo={RUTA_SALIDA} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
