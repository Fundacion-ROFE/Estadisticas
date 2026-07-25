#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Revisa la estructura de la tabla participants en Supabase.
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

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV = os.path.join(PROYECTO_ROOT, ".env.local")
USER_AGENT = "panel-datos-etl/1.0"

def cargar_env_local():
    if not os.path.isfile(RUTA_ENV):
        return
    with open(RUTA_ENV, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

cargar_env_local()
url = os.environ.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not url or not key:
    print("ERROR: faltan credenciales")
    sys.exit(1)

base = url.rstrip("/") + "/rest/v1"
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "User-Agent": USER_AGENT,
}

# Obtener un registro para ver qué campos tiene
print("[*] Leyendo 1 registro de participants...")
req = urllib.request.Request(
    f"{base}/participants?limit=1",
    headers=headers,
)
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        registros = json.loads(resp.read())
except urllib.error.HTTPError as e:
    print(f"ERROR HTTP {e.code}")
    sys.exit(1)

if registros:
    registro = registros[0]
    print("\nCampos disponibles en participants:")
    print("=" * 100)
    for key_val in sorted(registro.keys()):
        val = registro[key_val]
        tipo = type(val).__name__
        print(f"  {key_val:30} ({tipo:15}) = {str(val)[:60]}")
else:
    print("No hay registros")
