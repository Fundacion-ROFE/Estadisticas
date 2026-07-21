# -*- coding: utf-8 -*-
"""
Calcula % promedio de asistencia por estudiante y por curso.
Lee de ZOOM-ASISTANCE (Sheet) → Supabase (asistencia_promedio).
Ejecutar: diariamente vía n8n después de que se actualiza ZOOM-ASISTANCE.
"""
import io
import os
import sys
import json
from pathlib import Path
from datetime import datetime
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
import urllib.request
import urllib.error

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

cargar_env_local()

def leer_zoom_asistance():
    """Lee ZOOM-ASISTANCE del Sheet."""
    creds = Credentials.from_service_account_file(str(CRED), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    hoja = gc.open_by_key("1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0").worksheet("ZOOM-ASISTANCE")
    valores = hoja.get_all_values()

    headers = valores[0]
    idx_correo = next((i for i, h in enumerate(headers) if "correo" in h.lower()), None)
    idx_curso = next((i for i, h in enumerate(headers) if h.lower() == "curso"), None)
    idx_asistencia = next((i for i, h in enumerate(headers) if "asistencia" in h.lower() or "%" in h.lower()), None)

    if idx_correo is None or idx_curso is None or idx_asistencia is None:
        raise ValueError(f"Headers no encontrados. Disponibles: {headers}")

    registros = []
    for fila in valores[1:]:
        if len(fila) > max(idx_correo, idx_curso, idx_asistencia):
            email = fila[idx_correo].strip().lower() if fila[idx_correo] else ""
            curso = fila[idx_curso].strip() if fila[idx_curso] else ""
            asistencia_str = fila[idx_asistencia].strip() if fila[idx_asistencia] else "0%"

            if email and curso and asistencia_str:
                try:
                    asistencia_pct = float(asistencia_str.replace("%", "").strip())
                    registros.append({
                        "email": email,
                        "curso": curso,
                        "asistencia": asistencia_pct
                    })
                except ValueError:
                    continue

    return registros

def calcular_promedios(registros):
    """Calcula promedios por email y por curso."""
    por_email = defaultdict(list)
    por_email_curso = defaultdict(lambda: defaultdict(list))

    for reg in registros:
        email = reg["email"]
        curso = reg["curso"]
        asistencia = reg["asistencia"]

        por_email[email].append(asistencia)
        por_email_curso[email][curso].append(asistencia)

    # Calcular promedios
    estudiantes = []
    for email, valores in por_email.items():
        promedio_general = sum(valores) / len(valores)

        cursos_dict = {}
        for curso, valores_curso in por_email_curso[email].items():
            promedio_curso = sum(valores_curso) / len(valores_curso)
            cursos_dict[curso] = round(promedio_curso, 1)

        estudiantes.append({
            "email": email,
            "promedio_general": round(promedio_general, 1),
            "n_registros": len(valores),
            "cursos": cursos_dict
        })

    return estudiantes

def sincronizar_supabase(estudiantes):
    """Inserta/actualiza en Supabase."""
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        raise RuntimeError("Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (definir en .env.local o el entorno)")

    insertados = 0
    actualizados = 0
    errores = 0

    for est in estudiantes:
        data = {
            "email": est["email"],
            "promedio_general": est["promedio_general"],
            "n_registros": est["n_registros"],
            "cursos": est["cursos"],
            "actualizado_en": datetime.utcnow().isoformat()
        }

        try:
            # Intenta UPSERT: si existe, actualiza; si no, inserta
            req = urllib.request.Request(
                f"{url}/rest/v1/asistencia_promedio",
                method="POST",
                headers={
                    "apikey": service_key,
                    "Authorization": f"Bearer {service_key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"  # UPSERT
                },
                data=json.dumps([data]).encode("utf-8")
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 201:
                    insertados += 1
                else:
                    actualizados += 1

        except urllib.error.HTTPError as e:
            if e.code == 409:
                actualizados += 1
            else:
                errores += 1
                print(f"  ERROR {e.code} para {est['email']}")

    return insertados, actualizados, errores

def main():
    print("\n" + "="*80)
    print("CALCULAR ASISTENCIA: ZOOM-ASISTANCE → asistencia_promedio")
    print("="*80 + "\n")

    # Paso 1: Leer Sheet
    print("[1] Leyendo ZOOM-ASISTANCE...")
    try:
        registros = leer_zoom_asistance()
        print(f"    ✓ {len(registros)} registros leídos\n")
    except Exception as e:
        print(f"    ✗ Error: {e}\n")
        return 1

    # Paso 2: Calcular promedios
    print("[2] Calculando promedios...")
    try:
        estudiantes = calcular_promedios(registros)
        print(f"    ✓ {len(estudiantes)} estudiantes únicos\n")
    except Exception as e:
        print(f"    ✗ Error: {e}\n")
        return 1

    # Mostrar ejemplos
    print("[3] Ejemplos (primeros 3):\n")
    for est in estudiantes[:3]:
        print(f"    {est['email']}")
        print(f"      Promedio: {est['promedio_general']}%")
        print(f"      Clases: {est['n_registros']}")
        if est['cursos']:
            print(f"      Por curso: {est['cursos']}")
        print()

    # Paso 3: Sincronizar a Supabase
    print("[4] Sincronizando a Supabase...")
    try:
        insertados, actualizados, errores = sincronizar_supabase(estudiantes)
        print(f"    ✓ {insertados} nuevos registros")
        print(f"    ✓ {actualizados} registros actualizados")
        if errores > 0:
            print(f"    ⚠️  {errores} errores\n")
        else:
            print()
    except Exception as e:
        print(f"    ✗ Error: {e}\n")
        return 1

    print("="*80)
    print("[OK] Sincronización completada")
    print("="*80 + "\n")

    print("PRÓXIMO PASO:")
    print("El panel ahora mostrará automáticamente la asistencia desde Supabase.\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())

