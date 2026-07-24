# -*- coding: utf-8 -*-
"""
Sincroniza directamente a Supabase, ignorando 409 pero mostrando errores reales.
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
    print("SYNC DIRECTO: ZOOM-ASISTANCE -> asistencia_zoom")
    print("="*80 + "\n")

    cargar_env_local()
    url = os.getenv("SUPABASE_URL")
    # Usar SERVICE ROLE KEY para ignorar RLS policies
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        raise RuntimeError("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (definir en .env.local o el entorno)")
    api_key = service_key

    # Leer Sheets
    print("[1] Leyendo ZOOM-ASISTANCE...")
    creds = Credentials.from_service_account_file(str(CRED), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    hoja = gc.open_by_key("1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0").worksheet("ZOOM-ASISTANCE")
    valores = hoja.get_all_values()

    headers = valores[0]
    print(f"    Headers: {headers}\n")

    idx_correo = next((i for i, h in enumerate(headers) if "correo" in h.lower()), None)
    idx_curso = next((i for i, h in enumerate(headers) if h.lower() == "curso"), None)
    idx_fecha = next((i for i, h in enumerate(headers) if h.lower() == "fecha"), None)
    idx_asistencia = next((i for i, h in enumerate(headers) if "asistencia" in h.lower() or "%" in h.lower()), None)
    idx_nombre = next((i for i, h in enumerate(headers) if "nombre" in h.lower() and "apellido" not in h.lower()), None)
    idx_apellido = next((i for i, h in enumerate(headers) if "apellido" in h.lower()), None)
    idx_instancias = next((i for i, h in enumerate(headers) if "instancia" in h.lower()), None)

    print(f"    Índices: correo={idx_correo}, curso={idx_curso}, fecha={idx_fecha}, asistencia={idx_asistencia}")
    print(f"             nombre={idx_nombre}, apellido={idx_apellido}, instancias={idx_instancias}\n")

    # Deduplicar
    registros = {}
    for fila in valores[1:]:
        if len(fila) > max(idx_correo or 0, idx_curso or 0, idx_fecha or 0):
            email = fila[idx_correo].strip().lower() if idx_correo is not None else ""
            if email:
                clave = (email, fila[idx_curso].strip() if idx_curso else "", fila[idx_fecha].strip() if idx_fecha else "")
                if clave not in registros:
                    asistencia_str = fila[idx_asistencia].strip() if idx_asistencia and idx_asistencia < len(fila) else "0%"
                    nombre = fila[idx_nombre].strip() if idx_nombre and idx_nombre < len(fila) else ""
                    apellido = fila[idx_apellido].strip() if idx_apellido and idx_apellido < len(fila) else ""
                    instancias = fila[idx_instancias].strip() if idx_instancias and idx_instancias < len(fila) else "0/3"

                    registros[clave] = {
                        "asistencia": asistencia_str,
                        "nombre": nombre,
                        "apellido": apellido,
                        "instancias": instancias,
                    }

    datos = []
    for (email, curso, fecha), info in registros.items():
        datos.append({
            "email": email,
            "curso": curso,
            "fecha": fecha,
            "nombre": info["nombre"],
            "apellido": info["apellido"],
            "porcentaje_asistencia": info["asistencia"],
            "instancias": info["instancias"],
        })

    print(f"[2] Preparados {len(datos)} registros únicos\n")

    # Insertar en lotes con manejo de 409
    import urllib.request
    import urllib.error

    insertados = 0
    conflictos = 0
    otros_errores = 0

    print("[3] Insertando en lotes de 50...\n")

    for lote_num in range(0, len(datos), 50):
        lote = datos[lote_num:lote_num+50]

        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/asistencia_zoom",
                method="POST",
                headers={
                    "apikey": api_key,
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(lote).encode("utf-8"),
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                insertados += len(lote)
                print(f"    [{lote_num+len(lote):3d}/{len(datos)}] OK - {insertados} insertados")

        except urllib.error.HTTPError as e:
            if e.code == 409:
                conflictos += len(lote)
                print(f"    [{lote_num+len(lote):3d}/{len(datos)}] 409 Conflict - {conflictos} conflictos totales")
            else:
                otros_errores += 1
                msg = e.read().decode("utf-8") if e.fp else str(e)
                print(f"    [{lote_num+len(lote):3d}/{len(datos)}] ERROR {e.code}: {msg[:100]}")

    print(f"\n" + "="*80)
    print(f"[OK] Sync completado")
    print(f"     {insertados} registros insertados exitosamente")
    print(f"     {conflictos} conflictos (registros duplicados)")
    print(f"     {otros_errores} otros errores")
    print("="*80 + "\n")

    if insertados > 0:
        print("SIGUIENTE PASO:")
        print("1. Abre el panel: python tools/panel_riesgo_gui.py")
        print("2. Tab 'Jóvenes creaTIvos' → Vista 'En Q10'")
        print("3. Deberías ver porcentajes reales en la columna 'Asistencia %'\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
