#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Agrega nodos export_supabase_json y sync_supabase_to_sheets al workflow q10-sync-supabase."""

import json
import os

RUTA_WORKFLOW = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "..",
    "n8n-workflows",
    "q10-sync-supabase.json"
))

with open(RUTA_WORKFLOW, "r", encoding="utf-8") as f:
    workflow = json.load(f)

# Nuevos nodos a agregar
nodos_nuevos = [
    {
        "parameters": {
            "command": "cd C:/Users/EstudiantesJC/downloads/admin-usable/scripts/panel-datos && python export_supabase_json.py"
        },
        "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1,
        "position": [2464, -192],
        "id": "q10sb-0001-0001-0001-000000000018",
        "name": "Ejecutar export_supabase_json"
    },
    {
        "parameters": {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "strict",
                    "version": 2
                },
                "conditions": [
                    {
                        "leftValue": "={{ $json.stdout }}",
                        "rightValue": "estado=exito",
                        "operator": {
                            "type": "string",
                            "operation": "contains"
                        }
                    }
                ],
                "combinator": "and"
            },
            "options": {}
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [2688, -192],
        "id": "q10sb-0001-0001-0001-000000000019",
        "name": "¿Export JSON OK?"
    },
    {
        "parameters": {
            "command": "cd C:/Users/EstudiantesJC/downloads/admin-usable/scripts/panel-datos && python sync_supabase_to_sheets.py"
        },
        "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1,
        "position": [2912, -192],
        "id": "q10sb-0001-0001-0001-000000000020",
        "name": "Ejecutar sync_supabase_to_sheets"
    },
    {
        "parameters": {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "strict",
                    "version": 2
                },
                "conditions": [
                    {
                        "leftValue": "={{ $json.stdout }}",
                        "rightValue": "estado=exito",
                        "operator": {
                            "type": "string",
                            "operation": "contains"
                        }
                    }
                ],
                "combinator": "and"
            },
            "options": {}
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [3136, -192],
        "id": "q10sb-0001-0001-0001-000000000021",
        "name": "¿Sheets OK?"
    },
    {
        "parameters": {
            "errorMessage": "=Export JSON a GitHub fallo. Salida: {{ $json.stdout }} {{ $json.stderr }}"
        },
        "type": "n8n-nodes-base.stopAndError",
        "typeVersion": 1,
        "position": [2912, -96],
        "id": "q10sb-0001-0001-0001-000000000022",
        "name": "Error Export JSON"
    },
    {
        "parameters": {
            "errorMessage": "=Sync Supabase to Sheets fallo. Salida: {{ $json.stdout }} {{ $json.stderr }}"
        },
        "type": "n8n-nodes-base.stopAndError",
        "typeVersion": 1,
        "position": [3360, -96],
        "id": "q10sb-0001-0001-0001-000000000023",
        "name": "Error Sheets"
    }
]

# Mover nodo OK a nueva posición
for node in workflow["nodes"]:
    if node["name"] == "OK":
        node["position"] = [3360, -288]

# Agregar nodos nuevos
workflow["nodes"].extend(nodos_nuevos)

# Actualizar conexiones
if "connections" not in workflow:
    workflow["connections"] = {}

# Nuevas conexiones
conexiones_nuevas = {
    "¿Participación OK?": [
        {"node": "Ejecutar export_supabase_json", "type": "main", "index": 0}
    ],
    "Ejecutar export_supabase_json": [
        {"node": "¿Export JSON OK?", "type": "main", "index": 0}
    ],
    "¿Export JSON OK?": [
        {"node": "Ejecutar sync_supabase_to_sheets", "type": "main", "index": 0},
        {"node": "Error Export JSON", "type": "main", "index": 1}
    ],
    "Ejecutar sync_supabase_to_sheets": [
        {"node": "¿Sheets OK?", "type": "main", "index": 0}
    ],
    "¿Sheets OK?": [
        {"node": "OK", "type": "main", "index": 0},
        {"node": "Error Sheets", "type": "main", "index": 1}
    ]
}

for node_name, conexiones in conexiones_nuevas.items():
    workflow["connections"][node_name] = conexiones

# Guardar
with open(RUTA_WORKFLOW, "w", encoding="utf-8") as f:
    json.dump(workflow, f, ensure_ascii=False, indent=2)

print("Workflow actualizado exitosamente")
print(f"Total nodos: {len(workflow['nodes'])}")
print(f"Nodos agregados: {len(nodos_nuevos)}")
