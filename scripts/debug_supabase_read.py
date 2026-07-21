# -*- coding: utf-8 -*-
"""
Debug: Lee directamente de asistencia_promedio.
"""
import json
import os
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
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
anon_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not url or not anon_key or not service_key:
    raise RuntimeError("Faltan SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY / SUPABASE_SERVICE_ROLE_KEY (definir en .env.local o el entorno)")

print("\n" + "="*80)
print("DEBUG: Leer asistencia_promedio")
print("="*80 + "\n")

for key_type, key in [("ANON", anon_key), ("SERVICE", service_key)]:
    print(f"[{key_type} KEY]")
    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/asistencia_promedio?select=email,promedio_general&limit=3",
            method="GET",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
            print(f"  Status: {resp.status}")
            print(f"  Registros: {len(datos)}")
            if datos:
                print(f"  Primero: {datos[0]}\n")
            else:
                print(f"  (Tabla vacía)\n")
    except Exception as e:
        print(f"  Error: {e}\n")

# Intentar count
print("[COUNT]")
try:
    req = urllib.request.Request(
        f"{url}/rest/v1/asistencia_promedio?limit=0&count=exact",
        method="GET",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        range_header = resp.headers.get('Content-Range', 'No header')
        print(f"  Content-Range: {range_header}\n")
except Exception as e:
    print(f"  Error: {e}\n")
