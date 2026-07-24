# -*- coding: utf-8 -*-
"""
Sync simple: inserta records ignorando conflictos.
"""
import io
import os
import sys
import json
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import gspread
from google.oauth2.service_account import Credentials

BASE = Path(__file__).resolve().parents[2]
CRED = BASE / "scripts" / "q10-consolidacion" / "credenciales_service_account.json"
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

def main():
    print("\n" + "="*80)
    print("SYNC SIMPLE: ZOOM-ASISTANCE -> asistencia_zoom")
    print("="*80 + "\n")

    cargar_env_local()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (definir en .env.local o el entorno)")

    # Leer Sheets
    print("Leyendo Sheets...")
    creds = Credentials.from_service_account_file(str(CRED), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    hoja = gc.open_by_key("1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0").worksheet("ZOOM-ASISTANCE")
    valores = hoja.get_all_values()

    headers = valores[0]
    idx_correo = next((i for i, h in enumerate(headers) if "correo" in h.lower()), None)
    idx_curso = next((i for i, h in enumerate(headers) if h.lower() == "curso"), None)
    idx_fecha = next((i for i, h in enumerate(headers) if h.lower() == "fecha"), None)
    idx_asistencia = next((i for i, h in enumerate(headers) if "asistencia" in h.lower() or "%" in h.lower()), None)

    # Deduplicar
    registros = {}
    for fila in valores[1:]:
        if len(fila) > max(idx_correo or 0, idx_curso or 0, idx_fecha or 0):
            email = fila[idx_correo].strip().lower() if idx_correo is not None else ""
            if email:
                clave = (email, fila[idx_curso].strip() if idx_curso else "", fila[idx_fecha].strip() if idx_fecha else "")
                if clave not in registros:
                    asistencia_str = fila[idx_asistencia].strip() if idx_asistencia and idx_asistencia < len(fila) else "0%"
                    registros[clave] = asistencia_str

    datos = []
    for (email, curso, fecha), asistencia_str in registros.items():
        datos.append({
            "email": email,
            "curso": curso,
            "fecha": fecha,
            "porcentaje_asistencia": asistencia_str
        })

    print(f"  {len(datos)} registros unicos para insertar\n")

    # Insertar uno por uno
    import urllib.request
    import urllib.error

    insertados = 0
    conflictos = 0

    for i, reg in enumerate(datos, 1):
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/asistencia_zoom",
                method="POST",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps([reg]).encode("utf-8"),
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                insertados += 1
                if i % 100 == 0 or i == len(datos):
                    print(f"  [{i}/{len(datos)}] {insertados} insertados, {conflictos} conflictos saltados")

        except urllib.error.HTTPError as e:
            if e.code == 409:
                conflictos += 1
            else:
                print(f"  ERROR en registro {i}: {reg}")
                raise

    print(f"\n[OK] Sync completado: {insertados} filas en Supabase ({conflictos} conflictos ignorados)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
