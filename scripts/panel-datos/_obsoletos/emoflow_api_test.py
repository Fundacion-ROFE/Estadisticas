# OBSOLETO (P0 2026-07-24): script exploratorio; credenciales movidas a entorno.
# -*- coding: utf-8 -*-
"""
emoflow_api_test.py — Reconocimiento de API de Emoflow
Intenta: login → descarga CSV → inspecciona estructura
"""

import os
import requests
import sys
import io
from io import StringIO
import csv
import re

# Forzar UTF-8 en stdout
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_URL = "https://emoflow.sanumbe.com"
USER = os.environ.get("EMOFLOW_USER", "")
PASSWORD = os.environ.get("EMOFLOW_PASSWORD", "")
if not USER or not PASSWORD:
    raise RuntimeError("Definir EMOFLOW_USER/EMOFLOW_PASSWORD (.env.local). P0 2026-07-24")
session = requests.Session()

# Opción 1: Leer formulario de login para encontrar nombre de campos
print("[1] Leyendo formulario de login...")
try:
    resp = session.get(f"{BASE_URL}/login", timeout=10)
    # Buscar nombre de campos en el formulario
    inputs = re.findall(r'<input[^>]*name=["\']?([^"\'>\s]+)[^>]*(?:value=["\']?([^"\'>\s]*)["\']?)?', resp.text, re.I)
    campos_form = {}
    for name, value in inputs:
        if name not in campos_form:
            campos_form[name] = value or ""
    print(f"  ✓ Campos encontrados: {list(campos_form.keys())}")
except Exception as e:
    print(f"  Error: {e}")
    campos_form = {}

# Opción 2: Intentar login con POST form-data
print("\n[2] Intentando login con POST /login (form-data)...")
try:
    # Probar diferentes nombres de campo comunes
    credenciales_opciones = [
        {"usuario": USER, "password": PASSWORD},
        {"email": USER, "password": PASSWORD},
        {"usuario": USER, "contrasena": PASSWORD},
        {"username": USER, "password": PASSWORD},
    ]

    login_exitoso = False
    for creds in credenciales_opciones:
        resp = session.post(
            f"{BASE_URL}/login",
            data=creds,
            allow_redirects=True,
            timeout=10
        )
        # Si redirige a /admin o no devuelve login page es éxito
        if resp.status_code == 200 and ("admin" in resp.url or "registro_ingresos" in resp.text):
            print(f"  ✓ Login exitoso con credenciales: {creds}")
            login_exitoso = True
            break
        elif resp.status_code in (302, 303):
            print(f"  → Redirige a: {resp.headers.get('Location', '?')}")

    if not login_exitoso and "login" in resp.url.lower():
        print(f"  ⚠ Login probablemente falló (devuelve página de login)")
        print(f"  URL final: {resp.url}")

    print(f"  Cookies después de login: {session.cookies.get_dict()}")
except Exception as e:
    print(f"  Error en login: {e}")

# Opción 3: Descargar CSV del endpoint
print("\n[3] Intentando descargar CSV...")
try:
    resp = session.get(
        f"{BASE_URL}/admin/registro-ingresos-exportar",
        params={
            "scope": "all",
            "participacion_estado": "todos",
            "empresa_participacion": "Fundación ROFÉ"
        },
        timeout=30
    )
    print(f"  Status: {resp.status_code}")

    # Verificar si es CSV válido
    if "Usuario" in resp.text and "Nombre" in resp.text:
        print("  ✓ CSV válido descargado")
        # Contar filas
        reader = csv.DictReader(StringIO(resp.text))
        filas = list(reader)
        print(f"  Filas: {len(filas)}")
        if filas:
            print(f"  Primer registro: {filas[0]}")
            print(f"  Headers: {list(filas[0].keys())}")
    elif "login" in resp.text.lower() or "<!doctype" in resp.text.lower():
        print("  ✗ Aún redirige a login (la sesión no se mantuvo)")
    else:
        print(f"  Contenido: {resp.text[:300]}...")
except Exception as e:
    print(f"  Error descargando CSV: {e}")

print("\n[4] Resumen para automatización:")
print(f"  - Endpoint de login: POST /login")
print(f"  - Tipo de sesión: PHPSESSID (cookie)")
print(f"  - Endpoint de datos: GET /admin/registro-ingresos-exportar")
print(f"  - Respuesta: CSV")
print(f"  - Parámetros necesarios: scope, participacion_estado, empresa_participacion")
