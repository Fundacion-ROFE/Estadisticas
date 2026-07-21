# -*- coding: utf-8 -*-
"""
Verifica el estado de la tabla asistencia_zoom en Supabase.
"""
import json
import os
import urllib.request
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
anon_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not url or not service_key:
    raise RuntimeError("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (definir en .env.local o el entorno)")

print("\n" + "="*80)
print("Estado de asistencia_zoom en Supabase")
print("="*80 + "\n")

# Intenta con SERVICE KEY
print("[1] Consultando con SERVICE KEY...")
try:
    req = urllib.request.Request(
        f"{url}/rest/v1/asistencia_zoom?select=count(*)",
        method="GET",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        if result:
            count = result[0]["count"]
            print(f"   ✓ Registros en asistencia_zoom: {count}\n")
        else:
            print(f"   ✓ Tabla vacía\n")
except Exception as e:
    print(f"   ✗ Error: {e}\n")

# Obtener primeras 3 filas
print("[2] Primeros 3 registros:")
try:
    req = urllib.request.Request(
        f"{url}/rest/v1/asistencia_zoom?select=*&limit=3",
        method="GET",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        for i, row in enumerate(data, 1):
            print(f"\n   [{i}]")
            for k, v in row.items():
                if k not in ['id', 'created_at']:
                    print(f"      {k}: {v}")
except Exception as e:
    print(f"   ✗ Error: {e}\n")

print("\n" + "="*80)
print("ANÁLISIS")
print("="*80 + "\n")

print("Si hay registros:")
print("  → Necesitas TRUNCATE la tabla antes de sincronizar nuevamente")
print("  → Ejecuta en Supabase dashboard: DROP TABLE asistencia_zoom")
print("  → Luego ejecuta de nuevo el sync\n")

print("Si la tabla está vacía:")
print("  → El error 409 se debe a un problema en los datos/formato")
print("  → Revisa que los correos estén en minúsculas")
print("  → Verifica que la estructura de datos coincida con la tabla\n")
