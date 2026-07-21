# -*- coding: utf-8 -*-
"""
Crea el workflow 'asistencia-zoom-diario' en n8n vía API.
"""
import json
import urllib.request
import urllib.error

# Configuración de n8n
N8N_URL = "http://localhost:5678/api/v1"
# La clave se obtiene de http://localhost:5678/settings/personal

print("\n" + "="*80)
print("CREAR WORKFLOW EN N8N: asistencia-zoom-diario")
print("="*80 + "\n")

# Definición del workflow
workflow = {
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

print("Workflow a crear:")
print(json.dumps(workflow, indent=2)[:500] + "...\n")

print("[INSTRUCCIONES MANUALES]\n")
print("Dado que n8n no expone API de creación sin autenticación,")
print("aquí hay dos opciones:\n")

print("OPCIÓN 1: Importar JSON en n8n (RECOMENDADO)")
print("─" * 60)
print("1. Abre n8n: http://localhost:5678")
print("2. Click en el menú '≡' (esquina superior izquierda)")
print("3. Click 'Import'")
print("4. Selecciona: n8n-workflows/asistencia-zoom-diario.json")
print("5. Click 'Import'")
print("6. En el workflow, click 'Save'")
print("7. Click el toggle 'Active' → debe estar en verde\n")

print("OPCIÓN 2: Crear manualmente (sin importar)")
print("─" * 60)
print("1. Abre n8n: http://localhost:5678")
print("2. Click '+ New' → 'New Workflow'")
print("3. Nombre: 'asistencia-zoom-diario'")
print("4. Click '+ Add trigger' → Busca 'Cron' → Selecciona")
print("5. En Cron, configura:")
print("   - Trigger time: 00:00 (medianoche)")
print("6. Click el '+' que sale del Cron")
print("7. Busca 'Execute Command' → Selecciona")
print("8. En Execute Command, pegá en 'Command':")
print("   cd \"C:\\Users\\EstudiantesJC\\downloads\\admin-usable\" && python scripts\\panel-datos\\calcular_asistencia_promedio.py")
print("9. Click 'Save'")
print("10. Click el toggle 'Active' → debe estar en verde\n")

print("OPCIÓN 3: Verificar si está corriendo")
print("─" * 60)
try:
    req = urllib.request.Request(
        f"{N8N_URL}/workflows",
        method="GET",
        headers={
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        workflows = json.loads(resp.read().decode("utf-8"))
        print(f"✓ n8n está corriendo")
        print(f"✓ Workflows actuales: {len(workflows)}\n")
except Exception as e:
    print(f"✗ No se pudo conectar a n8n: {e}")
    print(f"   Asegúrate que n8n está corriendo en http://localhost:5678\n")

print("="*80)
print("ARCHIVO JSON LISTO:")
print("  → n8n-workflows/asistencia-zoom-diario.json")
print("="*80 + "\n")
