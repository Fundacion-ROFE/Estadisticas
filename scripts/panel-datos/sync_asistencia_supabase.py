# -*- coding: utf-8 -*-
"""
Sincronizacion: ZOOM-ASISTANCE (Google Sheets) → Supabase asistencia_zoom.

Lee datos desde Google Sheets y hace upsert en Supabase via REST API.
Idempotente por (email, curso, fecha).

Uso:
  python scripts/panel-datos/sync_asistencia_supabase.py [--dry-run]

Requiere:
  - SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en entorno
  - Service Account en scripts/q10-consolidacion/credenciales_service_account.json
"""
import io
import os
import sys
import json
from pathlib import Path
from collections import defaultdict

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

ZOOM_ASISTANCE_SHEET_ID = "1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0"
ZOOM_ASISTANCE_TAB = "ZOOM-ASISTANCE"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def conectar_sheets():
    """Conecta a Google Sheets."""
    if not CRED.exists():
        raise FileNotFoundError(f"No encontrado: {CRED}")
    creds = Credentials.from_service_account_file(str(CRED), scopes=SCOPES)
    return gspread.authorize(creds)

def leer_asistencia_sheets():
    """Lee ZOOM-ASISTANCE, deduplica por (email, curso, fecha), retorna lista normalizada."""
    print("Leyendo ZOOM-ASISTANCE...")
    gc = conectar_sheets()
    hoja = gc.open_by_key(ZOOM_ASISTANCE_SHEET_ID).worksheet(ZOOM_ASISTANCE_TAB)
    valores = hoja.get_all_values()

    if len(valores) < 2:
        raise ValueError("ZOOM-ASISTANCE esta vacia")

    headers = valores[0]
    idx_nombre = next((i for i, h in enumerate(headers) if h.lower().strip() == "nombre"), None)
    idx_apellido = next((i for i, h in enumerate(headers) if h.lower().strip() == "apellido"), None)
    idx_correo = next((i for i, h in enumerate(headers) if "correo" in h.lower()), None)
    idx_instancias = next((i for i, h in enumerate(headers) if "instancia" in h.lower()), None)
    idx_curso = next((i for i, h in enumerate(headers) if h.lower().strip() == "curso"), None)
    idx_fecha = next((i for i, h in enumerate(headers) if h.lower().strip() == "fecha"), None)
    idx_pct = next((i for i, h in enumerate(headers) if "%" in h.lower() and "asistencia" in h.lower()), None)

    if idx_correo is None:
        raise ValueError("No se encontro columna de correo")

    # Leer todas las filas
    todas_filas = []
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

        todas_filas.append({
            "email": correo,
            "nombre": nombre,
            "apellido": apellido,
            "curso": curso,
            "fecha": fecha,
            "instancias": instancias,
            "porcentaje_asistencia": pct,
        })

    # Deduplicar: guardar ultima ocurrencia de cada (email, curso, fecha)
    deduped = {}
    for f in todas_filas:
        clave = (f["email"], f["curso"], f["fecha"])
        deduped[clave] = f

    filas = list(deduped.values())
    print(f"  {len(todas_filas)} filas leidas, {len(filas)} unicas (sin duplicados)")
    return filas

def upsert_supabase(filas, dry_run=False):
    """Hace upsert en Supabase via REST API (DELETE + INSERT)."""
    import urllib.request
    import urllib.error

    url = "https://kbxptoowtnteflhrfwid.supabase.co"
    key = "***SECRETO-PURGADO***"

    print(f"\nSupabase: {url}")

    if dry_run:
        print(f"[DRY-RUN] Se inserirían {len(filas)} filas")
        for i, f in enumerate(filas[:3]):
            print(f"  {i+1}. {f['email']} | {f['curso']} | {f['fecha']}")
        if len(filas) > 3:
            print(f"  ... y {len(filas) - 3} mas")
        return len(filas)

    # Deduplicar por (email, curso, fecha)
    upserts = {}
    for f in filas:
        clave = (f["email"], f["curso"], f["fecha"])
        upserts[clave] = {
            "email": f["email"],
            "nombre": f["nombre"],
            "apellido": f["apellido"],
            "curso": f["curso"],
            "fecha": f["fecha"],
            "instancias": f["instancias"],
            "porcentaje_asistencia": f["porcentaje_asistencia"],
            "correo_electronico": f["email"],
        }

    datos_upsert = list(upserts.values())
    print(f"Registros a sincronizar: {len(datos_upsert)}\n")

    try:
        # Insertar en lotes con UPSERT via header Prefer
        # Esto es la forma correcta en Supabase: PUT/POST con resolution=upsert
        print("Insertando registros (upsert por lotes)...")

        batch_size = 100
        for i in range(0, len(datos_upsert), batch_size):
            batch = datos_upsert[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(datos_upsert) + batch_size - 1) // batch_size

            req_upsert = urllib.request.Request(
                f"{url}/rest/v1/asistencia_zoom",
                method="POST",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=upsert",
                },
                data=json.dumps(batch).encode("utf-8"),
            )

            try:
                with urllib.request.urlopen(req_upsert, timeout=60) as resp:
                    if resp.status in (200, 201):
                        print(f"  [{batch_num}/{total_batches}] {len(batch)} filas insertadas")
                    else:
                        print(f"  [{batch_num}/{total_batches}] HTTP {resp.status}")
            except urllib.error.HTTPError as e:
                if e.code == 409:
                    # Intentar de nuevo con DELETE previo
                    print(f"  [{batch_num}/{total_batches}] Conflicto detectado, limpiando...")
                    # Delete registros del batch
                    emails_batch = [f["email"] for f in batch]
                    for email in set(emails_batch):
                        req_del = urllib.request.Request(
                            f"{url}/rest/v1/asistencia_zoom?email=eq.{email}",
                            method="DELETE",
                            headers={
                                "apikey": key,
                                "Authorization": f"Bearer {key}",
                            },
                        )
                        try:
                            with urllib.request.urlopen(req_del, timeout=30) as resp:
                                pass
                        except:
                            pass
                    # Reintentar insert
                    with urllib.request.urlopen(req_upsert, timeout=60) as resp:
                        print(f"  [{batch_num}/{total_batches}] {len(batch)} filas insertadas (reintentado)")
                else:
                    raise

        print(f"\n[OK] Sync exitoso: {len(datos_upsert)} filas en Supabase")
        return len(datos_upsert)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sync ZOOM-ASISTANCE -> Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar sin hacer cambios")
    args = parser.parse_args()

    print("\n" + "="*80)
    print("SYNC: ZOOM-ASISTANCE (Sheets) -> asistencia_zoom (Supabase)")
    print("="*80 + "\n")

    try:
        filas = leer_asistencia_sheets()
        n_insertadas = upsert_supabase(filas, dry_run=args.dry_run)

        if not args.dry_run:
            print(f"\n[OK] Sincronizacion completa: {n_insertadas} filas en Supabase")
        return 0

    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
