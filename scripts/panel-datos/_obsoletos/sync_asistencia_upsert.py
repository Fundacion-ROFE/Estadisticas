# -*- coding: utf-8 -*-
"""
Sincroniza ZOOM-ASISTANCE a Supabase usando UPSERT (sobrescribe si existe).
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
    print("SYNC UPSERT: ZOOM-ASISTANCE -> asistencia_zoom (sobrescribe si existe)")
    print("="*80 + "\n")

    cargar_env_local()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # SERVICE KEY para permitir TRUNCATE
    if not url or not key:
        raise RuntimeError("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (definir en .env.local o el entorno)")

    # Leer Sheets
    print("Leyendo ZOOM-ASISTANCE...")
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

    # OPCION 1: TRUNCATE + INSERT (recomendado si tienes control)
    print("[PASO 1] TRUNCATE tabla asistencia_zoom...")
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/asistencia_zoom",
            method="DELETE",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            data=json.dumps({"1": "1"}).encode("utf-8"),  # Dummy WHERE clause
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"  Respuesta: {resp.status}")
    except urllib.error.HTTPError as e:
        if e.code == 405:
            print(f"  ADVERTENCIA: No se puede hacer DELETE sin WHERE")
            print(f"  Necesitas hacer TRUNCATE manualmente en Supabase dashboard\n")
        else:
            print(f"  Error: {e}\n")

    # OPCION 2: Insertar en lote con UPSERT (Prefer header)
    print("[PASO 2] Insertar con UPSERT (Prefer: resolution=merge-duplicates)...")

    insertados = 0
    conflictos = 0

    # Insertar en lotes de 100
    for lote_num in range(0, len(datos), 100):
        lote = datos[lote_num:lote_num+100]

        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/asistencia_zoom",
                method="POST",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",  # UPSERT en duplicados
                },
                data=json.dumps(lote).encode("utf-8"),
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                insertados += len(lote)
                print(f"  [{lote_num+len(lote)}/{len(datos)}] {insertados} insertados")

        except urllib.error.HTTPError as e:
            if e.code == 409:
                print(f"  [{lote_num+len(lote)}/{len(datos)}] Conflictos en lote")
                conflictos += len(lote)
            else:
                print(f"  ERROR {e.code}: {e}")
                print(f"  Detalle: {e.read().decode('utf-8')}")

    print(f"\n[OK] Sync completado: {insertados} registros procesados")
    if conflictos > 0:
        print(f"     {conflictos} conflictos (se intenta sobrescribir)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
