# -*- coding: utf-8 -*-
"""
Vacía completamente la tabla asistencia_zoom desde la API.
"""
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
RUTA_ENV = BASE / ".env.local"

def cargar_env_local() -> None:
    """Carga .env.local de la raíz (mismo parser que sync_asistencia_supabase.py)."""
    if not RUTA_ENV.is_file():
        return
    with open(RUTA_ENV, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

cargar_env_local()
url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not url or not service_key:
    raise RuntimeError("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (definir en .env.local o el entorno)")

print("\n" + "="*80)
print("TRUNCATE: asistencia_zoom")
print("="*80 + "\n")

# Primero, contar cuántos registros hay
print("[1] Consultando registros actuales...")
try:
    req = urllib.request.Request(
        f"{url}/rest/v1/asistencia_zoom?limit=0&count=exact",
        method="GET",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        # El count viene en Content-Range header
        content_range = resp.headers.get('Content-Range', '')
        print(f"    Content-Range: {content_range}\n")
except Exception as e:
    print(f"    Error: {e}\n")

# Intentar DELETE sin WHERE (para vaciar tabla)
print("[2] Borrando todos los registros...")
try:
    req = urllib.request.Request(
        f"{url}/rest/v1/asistencia_zoom",
        method="DELETE",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"    Status: {resp.status}")
        print(f"    Tabla vaciada exitosamente\n")
except urllib.error.HTTPError as e:
    print(f"    HTTP Error {e.code}")
    msg = e.read().decode('utf-8')
    print(f"    Respuesta: {msg}\n")

    if e.code == 405:
        print("SOLUCIÓN ALTERNATIVA:")
        print("La API no permite DELETE sin WHERE clause.")
        print("\nEjecuta esto en el SQL editor de Supabase:")
        print("  TRUNCATE TABLE asistencia_zoom CASCADE;")
        print("\nLuego ejecuta nuevamente este script.\n")

print("="*80)
