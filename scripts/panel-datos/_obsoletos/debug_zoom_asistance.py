# OBSOLETO (P0 2026-07-24): diagnóstico de un solo uso; credenciales movidas a entorno.
# -*- coding: utf-8 -*-
"""
Debug: Inspecciona la estructura de ZOOM-ASISTANCE y verifica qué se envía a Supabase.
"""
import os
import io
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
import urllib.request

BASE = Path(__file__).resolve().parents[2]
CRED = BASE / "scripts" / "q10-consolidacion" / "credenciales_service_account.json"

def main():
    print("\n" + "="*100)
    print("DEBUG: Estructura ZOOM-ASISTANCE y sincronización a Supabase")
    print("="*100 + "\n")

    # ─── Leer ZOOM-ASISTANCE ─────────────────────────────────────────────
    print("[1] Leyendo ZOOM-ASISTANCE...")
    creds = Credentials.from_service_account_file(str(CRED), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)

    try:
        sheet = gc.open_by_key("1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0")
        ws = sheet.worksheet("ZOOM-ASISTANCE")
        valores = ws.get_all_values()
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return 1

    print(f"   ✓ Total filas: {len(valores)}\n")

    # ─── Analizar estructura ──────────────────────────────────────────────
    print("[2] Estructura de headers:")
    headers = valores[0]
    for i, h in enumerate(headers):
        print(f"   [{i:2d}] {h}")

    # Encontrar índices importantes
    idx_correo = next((i for i, h in enumerate(headers) if "correo" in h.lower()), None)
    idx_curso = next((i for i, h in enumerate(headers) if h.lower() == "curso"), None)
    idx_fecha = next((i for i, h in enumerate(headers) if h.lower() == "fecha"), None)
    idx_lectura = next((i for i, h in enumerate(headers) if "lectura" in h.lower()), None)

    print(f"\n   Índices encontrados:")
    print(f"   • correo: {idx_correo}")
    print(f"   • curso: {idx_curso}")
    print(f"   • fecha: {idx_fecha}")
    print(f"   • lectura: {idx_lectura}\n")

    # ─── Mostrar primeras filas ───────────────────────────────────────────
    print("[3] Primeras 5 filas de datos:\n")
    for row_num, fila in enumerate(valores[1:6], 2):
        if len(fila) > max(idx_correo or 0, idx_curso or 0):
            correo = fila[idx_correo].strip().lower() if idx_correo and idx_correo < len(fila) else "—"
            curso = fila[idx_curso].strip() if idx_curso and idx_curso < len(fila) else "—"
            fecha = fila[idx_fecha].strip() if idx_fecha and idx_fecha < len(fila) else "—"
            lectura = fila[idx_lectura].strip() if idx_lectura and idx_lectura < len(fila) else "—"
            print(f"   Fila {row_num}:")
            print(f"      Correo: {correo}")
            print(f"      Curso: {curso}")
            print(f"      Fecha: {fecha}")
            print(f"      Lectura: {lectura}")
            print()

    # ─── Contar unicos ───────────────────────────────────────────────────
    print("[4] Estadísticas:")
    correos_unicos = set()
    con_lectura_disponible = 0

    for fila in valores[1:]:
        if len(fila) > (idx_correo or 0):
            correo = fila[idx_correo].strip().lower() if idx_correo < len(fila) else ""
            if correo:
                correos_unicos.add(correo)

            if idx_lectura and idx_lectura < len(fila):
                lectura = fila[idx_lectura].strip().lower()
                if lectura == "disponible":
                    con_lectura_disponible += 1

    print(f"   • Emails únicos: {len(correos_unicos)}")
    print(f"   • Registros con lectura='disponible': {con_lectura_disponible}")
    print(f"   • Total registros: {len(valores) - 1}\n")

    # ─── Verificar en Supabase ───────────────────────────────────────────
    print("[5] Verificar Supabase:")
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")

    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/asistencia_zoom?select=count()&limit=1",
            method="GET",
            headers={"apikey": key, "Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            count = result[0]["count"] if result else 0
            print(f"   • Registros en asistencia_zoom: {count}\n")
    except Exception as e:
        print(f"   ✗ Error consultando Supabase: {e}\n")

    # ─── Preparar datos para sincronizar ──────────────────────────────────
    print("[6] Datos que se DEBERÍAN sincronizar:")
    registros = {}
    for fila in valores[1:]:
        if len(fila) > max(idx_correo or 0, idx_curso or 0):
            correo = fila[idx_correo].strip().lower() if idx_correo < len(fila) else ""
            curso = fila[idx_curso].strip() if idx_curso < len(fila) else ""
            fecha = fila[idx_fecha].strip() if idx_fecha < len(fila) else ""

            if correo and curso and fecha:
                clave = (correo, curso, fecha)
                if clave not in registros:
                    registros[clave] = True

    print(f"   • Registros únicos a sincronizar: {len(registros)}\n")

    # Mostrar 3 ejemplos
    print("   Ejemplos (primeros 3):")
    for i, (correo, curso, fecha) in enumerate(list(registros.keys())[:3], 1):
        print(f"      [{i}] {correo} | {curso} | {fecha}")
    print()

    print("="*100)
    print("ANÁLISIS COMPLETADO")
    print("="*100 + "\n")

    print("RECOMENDACIONES:")
    if len(registros) == 0:
        print("⚠️  No hay registros para sincronizar. Verifica que ZOOM-ASISTANCE tenga datos.")
    else:
        print(f"✓ Hay {len(registros)} registros listos para sincronizar")
        if count == 0:
            print("⚠️  Supabase está vacía. Ejecuta: python scripts/panel-datos/sync_asistencia_simple.py")
        else:
            print(f"✓ Supabase ya tiene {count} registros")

    return 0

if __name__ == "__main__":
    sys.exit(main())
