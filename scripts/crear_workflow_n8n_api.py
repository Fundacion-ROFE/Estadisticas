# -*- coding: utf-8 -*-
"""
Crea el workflow 'asistencia-zoom-diario' en n8n vía API REST.
"""
import io
import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parents[1]
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

# API de n8n
N8N_BASE = "http://localhost:5678"
N8N_API = f"{N8N_BASE}/api/v1"
N8N_API_KEY = os.getenv("N8N_API_KEY")
if not N8N_API_KEY:
    raise RuntimeError("Falta N8N_API_KEY (definir en .env.local o el entorno)")

print("\n" + "="*80)
print("CREAR WORKFLOW EN N8N VÍA API")
print("="*80 + "\n")

# Definición del workflow (estructura simplificada para API)
workflow_data = {
    "name": "asistencia-zoom-diario",
    "nodes": [
        {
            "parameters": {
                "triggerTimes": [
                    {
                        "mode": "everyDay",
                        "hour": 0,
                        "minute": 0
                    }
                ]
            },
            "id": "Cron",
            "name": "Cron",
            "type": "n8n-nodes-base.cron",
            "typeVersion": 1,
            "position": [250, 300],
            "disabled": False
        },
        {
            "parameters": {
                "command": "cd \"C:\\Users\\EstudiantesJC\\downloads\\admin-usable\" && python scripts\\panel-datos\\calcular_asistencia_promedio.py"
            },
            "id": "ExecuteCommand",
            "name": "Calcular Asistencia",
            "type": "n8n-nodes-base.executeCommand",
            "typeVersion": 1,
            "position": [550, 300],
        }
    ],
    "connections": {
        "Cron": {
            "main": [
                [
                    {
                        "node": "ExecuteCommand",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        }
    },
    "active": False,
    "settings": {}
}

print("[1] Verificando n8n...")
try:
    req = urllib.request.Request(
        f"{N8N_BASE}",
        method="GET"
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        if resp.status == 200:
            print(f"    OK - n8n disponible en {N8N_BASE}\n")
except Exception as e:
    print(f"    ERROR - n8n no está disponible: {e}")
    print(f"    Asegúrate que n8n esté corriendo en {N8N_BASE}\n")
    sys.exit(1)

print("[2] Creando workflow...")
try:
    req = urllib.request.Request(
        f"{N8N_API}/workflows",
        method="POST",
        headers={
            "X-N8N-API-KEY": N8N_API_KEY,
            "Content-Type": "application/json"
        },
        data=json.dumps(workflow_data).encode("utf-8")
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        workflow_id = result.get("id")
        print(f"    OK - Workflow creado")
        print(f"    ID: {workflow_id}")
        print(f"    Nombre: {result.get('name')}\n")
except urllib.error.HTTPError as e:
    msg = e.read().decode("utf-8")
    print(f"    ERROR {e.code}: {msg}\n")
    sys.exit(1)

print("[3] Activando workflow...")
try:
    activate_data = {
        "active": True
    }
    req = urllib.request.Request(
        f"{N8N_API}/workflows/{workflow_id}",
        method="PATCH",
        headers={
            "X-N8N-API-KEY": N8N_API_KEY,
            "Content-Type": "application/json"
        },
        data=json.dumps(activate_data).encode("utf-8")
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        status = "ACTIVO (verde)" if result.get("active") else "Inactivo"
        print(f"    OK - Workflow {status}\n")
except urllib.error.HTTPError as e:
    msg = e.read().decode("utf-8")
    print(f"    ERROR {e.code}: {msg}\n")
    sys.exit(1)

print("="*80)
print("WORKFLOW CREADO Y ACTIVADO EXITOSAMENTE")
print("="*80)
print(f"\nWorkflow ID: {workflow_id}")
print(f"Nombre: asistencia-zoom-diario")
print(f"Trigger: 00:00 (medianoche) cada día")
print(f"Acción: calcular_asistencia_promedio.py")
print(f"\nVe a: http://localhost:5678/workflow/{workflow_id}")
print(f"Status: ACTIVO (verde) - ejecutará cada noche\n")

return_code = 0

print("[4] TEST RECOMENDADO")
print("─" * 80)
print("\nEn n8n, en el nodo 'Calcular Asistencia', click el boton PLAY (triangulo)")
print("Verifica que el output contenga:")
print("  ✓ 704 registros leidos")
print("  ✓ 490 estudiantes unicos")
print("  ✓ Sincronización completada\n")

sys.exit(return_code)
