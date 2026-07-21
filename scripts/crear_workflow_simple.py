# -*- coding: utf-8 -*-
"""
Crea workflow 'asistencia-zoom-diario' en n8n vía API (versión simplificada).
"""
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

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

N8N_API = "http://localhost:5678/api/v1"
N8N_API_KEY = os.getenv("N8N_API_KEY")
if not N8N_API_KEY:
    raise RuntimeError("Falta N8N_API_KEY (definir en .env.local o el entorno)")

print("\n" + "="*80)
print("CREAR WORKFLOW: asistencia-zoom-diario")
print("="*80 + "\n")

# Datos minimalistas del workflow
workflow = {
    "name": "asistencia-zoom-diario",
    "nodes": [
        {
            "parameters": {
                "triggerTimes": [{"mode": "everyDay", "hour": 0, "minute": 0}]
            },
            "id": "Cron",
            "name": "Cron",
            "type": "n8n-nodes-base.cron",
            "typeVersion": 1,
            "position": [250, 300]
        },
        {
            "parameters": {
                "command": "cd \"C:\\Users\\EstudiantesJC\\downloads\\admin-usable\" && python scripts\\panel-datos\\calcular_asistencia_promedio.py"
            },
            "id": "ExecuteCommand",
            "name": "Calcular Asistencia",
            "type": "n8n-nodes-base.executeCommand",
            "typeVersion": 1,
            "position": [550, 300]
        }
    ],
    "connections": {
        "Cron": {
            "main": [[{"node": "ExecuteCommand", "type": "main", "index": 0}]]
        }
    },
    "settings": {}
}

print("[1] Creando workflow...")
try:
    req = urllib.request.Request(
        f"{N8N_API}/workflows",
        method="POST",
        headers={
            "X-N8N-API-KEY": N8N_API_KEY,
            "Content-Type": "application/json"
        },
        data=json.dumps(workflow).encode("utf-8")
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        workflow_id = result.get("id")
        print(f"    OK - Creado")
        print(f"    ID: {workflow_id}\n")
except urllib.error.HTTPError as e:
    print(f"    ERROR {e.code}: {e.read().decode('utf-8')}\n")
    exit(1)

print("[2] Activando workflow...")
try:
    update_data = dict(workflow)
    update_data["active"] = True
    req = urllib.request.Request(
        f"{N8N_API}/workflows/{workflow_id}",
        method="PUT",
        headers={
            "X-N8N-API-KEY": N8N_API_KEY,
            "Content-Type": "application/json"
        },
        data=json.dumps(update_data).encode("utf-8")
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(f"    OK - Activo\n")
except urllib.error.HTTPError as e:
    print(f"    ERROR {e.code}: {e.read().decode('utf-8')}\n")
    exit(1)

print("="*80)
print("EXITO - Workflow listo")
print("="*80)
print(f"\nWorkflow ID: {workflow_id}")
print(f"Status: ACTIVO (verde)")
print(f"Trigger: 00:00 cada noche")
print(f"Acción: calcular_asistencia_promedio.py")
print(f"\nURL: http://localhost:5678/workflow/{workflow_id}\n")
