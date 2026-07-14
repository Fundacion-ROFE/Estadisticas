# -*- coding: utf-8 -*-
"""
Sincronización: ZOOM-ASISTANCE (Google Sheets) → Supabase (tabla asistencia_zoom).

Extrae datos de asistencia desde Google Sheets y hace upsert en Supabase,
idempotente por (email, curso, fecha).

Uso:
  python scripts/panel-datos/sync_asistencia_supabase.py [--dry-run]

Requiere:
  - SUPABASE_URL y SUPABASE_ANON_KEY en entorno (o .env.local)
  - Service Account en scripts/q10-consolidacion/credenciales_service_account.json
"""
import io
import os
import sys
import json
from pathlib import Path
from collections import defaultdict

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import gspread
from google.oauth2.service_account import Credentials

BASE = Path(__file__).resolve().parents[2]
CRED = BASE / "scripts" / "q10-consolidacion" / "credenciales_service_account.json"

ZOOM_ASISTANCE_SHEET_ID = "1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0"
ZOOM_ASISTANCE_TAB = "ZOOM-ASISTANCE"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def cargar_env_local():
    """Carga .env.local si existe."""
    raiz = BASE
    ruta = raiz / ".env.local"
    if not ruta.exists():
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip())

def conectar_sheets():
    """Conecta a Google Sheets."""
    if not CRED.exists():
        raise FileNotFoundError(f"No encontrado: {CRED}")
    creds = Credentials.from_service_account_file(str(CRED), scopes=SCOPES)
    return gspread.authorize(creds)

def leer_asistencia_sheets():
    """Lee ZOOM-ASISTANCE y retorna lista de filas normalizadas."""
    print("Leyendo ZOOM-ASISTANCE...")
    gc = conectar_sheets()
    hoja = gc.open_by_key(ZOOM_ASISTANCE_SHEET_ID).worksheet(ZOOM_ASISTANCE_TAB)
    valores = hoja.get_all_values()

    if len(valores) < 2:
        raise ValueError("ZOOM-ASISTANCE está vacía")

    # Headers: Nombre | Apellido | Correo electrónico | Identificacion | Instancias | Curso | Fecha | % Asistencia
    headers = valores[0]
    idx_nombre = next((i for i, h in enumerate(headers) if h.lower().strip() == "nombre"), None)
    idx_apellido = next((i for i, h in enumerate(headers) if h.lower().strip() == "apellido"), None)
    idx_correo = next((i for i, h in enumerate(headers) if "correo" in h.lower()), None)
    idx_instancias = next((i for i, h in enumerate(headers) if "instancia" in h.lower()), None)
    idx_curso = next((i for i, h in enumerate(headers) if h.lower().strip() == "curso"), None)
    idx_fecha = next((i for i, h in enumerate(headers) if h.lower().strip() == "fecha"), None)
    idx_pct = next((i for i, h in enumerate(headers) if "%" in h.lower() and "asistencia" in h.lower()), None)

    if idx_correo is None:
        raise ValueError("No se encontró columna de correo")

    filas = []
    for fila in valores[1:]:
        if all(c.strip() == "" for c in fila):
            continue

        correo = (fila[idx_correo].strip().lower() if idx_correo < len(fila) else "")
        if not correo:
            continue

        nombre = fila[idx_nombre].strip() if idx_nombre is not None and idx_nombre < len(fila) else ""
        apellido = fila[idx_apellido].strip() if idx_apellido is not None and idx_apellido < len(fila) else ""
        curso = fila[idx_curso].strip() if idx_curso is not None and idx_curso < len(fila) else ""
        fecha = fila[idx_fecha].strip() if idx_fecha is not None and idx_fecha < len(fila) else ""
        instancias = fila[idx_instancias].strip() if idx_instancias is not None and idx_instancias < len(fila) else ""
        pct = fila[idx_pct].strip() if idx_pct is not None and idx_pct < len(fila) else ""

        filas.append({
            "email": correo,
            "nombre": nombre,
            "apellido": apellido,
            "curso": curso,
            "fecha": fecha,
            "instancias": instancias,
            "porcentaje_asistencia": pct,
        })

    print(f"  {len(filas)} filas leidas de ZOOM-ASISTANCE")
    return filas

def upsert_supabase(filas, dry_run=False):
    """Hace upsert en Supabase."""
    import urllib.request
    import urllib.error

    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not url or not key:
        raise ValueError("SUPABASE_URL y SUPABASE_ANON_KEY requeridas")

    print(f"Conectando a Supabase: {url}")

    if dry_run:
        print(f"[DRY-RUN] Se inserirían {len(filas)} filas")
        for i, f in enumerate(filas[:3]):
            print(f"  {i+1}. {f['email']} | {f['curso']} | {f['fecha']} | {f['porcentaje_asistencia']}")
        if len(filas) > 3:
            print(f"  ... y {len(filas) - 3} mas")
        return len(filas)

    # Agrupar por (email, curso, fecha) para no duplicar
    upserts = {}
    for f in filas:
        clave = (f["email"], f["curso"], f["fecha"])
        # Última ocurrencia gana (por si hay duplicados)
        upserts[clave] = {
            "email": f["email"],
            "nombre": f["nombre"],
            "apellido": f["apellido"],
            "curso": f["curso"],
            "fecha": f["fecha"],
            "instancias": f["instancias"],
            "porcentaje_asistencia": f["porcentaje_asistencia"],
        }

    datos_upsert = list(upserts.values())
    print(f"Upsert: {len(datos_upsert)} filas unicas")

    # POST /rest/v1/asistencia_zoom con upsert
    req = urllib.request.Request(
        f"{url}/rest/v1/asistencia_zoom",
        method="POST",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",  # Upsert on conflict
        },
        data=json.dumps(datos_upsert).encode("utf-8"),
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = resp.status
            if result in (200, 201):
                print(f"  Upsert exitoso (HTTP {result})")
                return len(datos_upsert)
            else:
                print(f"  FALLO HTTP {result}")
                return 0
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8") if e.fp else str(e)
        print(f"  ERROR HTTP {e.code}: {msg}")
        raise
    except Exception as e:
        print(f"  ERROR: {e}")
        raise

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sync ZOOM-ASISTANCE → Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar que se insertaría, sin hacer cambios")
    args = parser.parse_args()

    print("\n" + "="*80)
    print("SYNC: ZOOM-ASISTANCE (Sheets) → asistencia_zoom (Supabase)")
    print("="*80 + "\n")

    try:
        cargar_env_local()

        # 1. Leer desde Sheets
        filas = leer_asistencia_sheets()

        # 2. Upsert a Supabase
        n_insertadas = upsert_supabase(filas, dry_run=args.dry_run)

        print(f"\n[OK] Sincronizacion completa: {n_insertadas} filas")
        return 0

    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
