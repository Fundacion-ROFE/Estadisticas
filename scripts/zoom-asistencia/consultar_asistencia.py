# -*- coding: utf-8 -*-
"""
Consulta datos de asistencia Zoom desde ZOOM-ASISTANCE (Google Sheets).
Calcula promedio de asistencia por estudiante y muestra a al menos 3 usuarios.
Requiere: Service Account en scripts/q10-consolidacion/credenciales_service_account.json
"""
import os
import sys
from pathlib import Path
from collections import defaultdict

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

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

def conectar():
    """Conecta a Google Sheets con credenciales de Service Account."""
    if not CRED.exists():
        raise FileNotFoundError(f"No encontrado: {CRED}")
    creds = Credentials.from_service_account_file(str(CRED), scopes=SCOPES)
    return gspread.authorize(creds)

def limpiar_pct(valor):
    """Convierte '72%' → 72.0"""
    limpio = valor.strip().replace("%", "").replace(",", ".").strip()
    if not limpio:
        return 0.0
    try:
        return float(limpio)
    except ValueError:
        return 0.0

def limpiar_instancias(valor):
    """Convierte '2/3' → 2, '3/3' → 3"""
    try:
        partes = valor.strip().split("/")
        return int(partes[0]) if partes else 0
    except (ValueError, IndexError):
        return 0

def consultar_asistencia():
    """Lee ZOOM-ASISTANCE y calcula promedio de asistencia por estudiante."""
    print("Conectando a Google Sheets...")
    gc = conectar()

    print(f"Leyendo '{ZOOM_ASISTANCE_TAB}'...")
    hoja = gc.open_by_key(ZOOM_ASISTANCE_SHEET_ID).worksheet(ZOOM_ASISTANCE_TAB)
    valores = hoja.get_all_values()

    if len(valores) < 2:
        print("ERROR: pestaña ZOOM-ASISTANCE está vacía o sin datos.")
        return

    # Headers esperados: Nombre | Apellido | Correo electrónico | Identificacion | Instancias | Curso | Fecha | % Asistencia
    headers = valores[0]
    print(f"\nHeaders encontrados: {headers}\n")

    # Encontrar índices de columnas
    idx_nombre = None
    idx_apellido = None
    idx_correo = None
    idx_identificacion = None
    idx_instancias = None
    idx_curso = None
    idx_fecha = None
    idx_pct = None

    for i, h in enumerate(headers):
        h_lower = h.lower().strip()
        if "nombre" == h_lower:
            idx_nombre = i
        elif "apellido" == h_lower:
            idx_apellido = i
        elif "correo" in h_lower or "email" in h_lower:
            idx_correo = i
        elif "identificac" in h_lower:
            idx_identificacion = i
        elif "instancia" in h_lower:
            idx_instancias = i
        elif "curso" == h_lower:
            idx_curso = i
        elif "fecha" == h_lower:
            idx_fecha = i
        elif "%" in h_lower and "asistencia" in h_lower:
            idx_pct = i

    if idx_correo is None:
        print("ERROR: No se encontró columna de correo electrónico.")
        return

    # Agrupar por estudiante (correo)
    por_email = defaultdict(lambda: {
        "nombre": "",
        "apellido": "",
        "identificacion": "",
        "registros": [],  # lista de {curso, fecha, instancias, porcentaje}
    })

    for fila in valores[1:]:
        if all(c.strip() == "" for c in fila):
            continue

        correo = (fila[idx_correo].strip() if idx_correo < len(fila) else "").lower()
        if not correo:
            continue

        nombre = fila[idx_nombre].strip() if idx_nombre is not None and idx_nombre < len(fila) else ""
        apellido = fila[idx_apellido].strip() if idx_apellido is not None and idx_apellido < len(fila) else ""
        identificacion = fila[idx_identificacion].strip() if idx_identificacion is not None and idx_identificacion < len(fila) else ""
        curso = fila[idx_curso].strip() if idx_curso is not None and idx_curso < len(fila) else ""
        fecha = fila[idx_fecha].strip() if idx_fecha is not None and idx_fecha < len(fila) else ""
        instancias = fila[idx_instancias].strip() if idx_instancias is not None and idx_instancias < len(fila) else ""
        pct = fila[idx_pct].strip() if idx_pct is not None and idx_pct < len(fila) else ""

        por_email[correo]["nombre"] = nombre
        por_email[correo]["apellido"] = apellido
        por_email[correo]["identificacion"] = identificacion

        por_email[correo]["registros"].append({
            "curso": curso,
            "fecha": fecha,
            "instancias": limpiar_instancias(instancias),
            "porcentaje": limpiar_pct(pct),
        })

    # Calcular promedio por estudiante
    estudiantes_con_promedio = []
    for correo, datos in por_email.items():
        n_registros = len(datos["registros"])
        if n_registros == 0:
            continue

        prom_pct = sum(r["porcentaje"] for r in datos["registros"]) / n_registros
        prom_instancias = sum(r["instancias"] for r in datos["registros"]) / n_registros

        # Contar faltas (instancias < 3/3 o asistencia < 70%)
        faltas = [
            r for r in datos["registros"]
            if r["instancias"] < 3 or r["porcentaje"] < 70
        ]

        estudiantes_con_promedio.append({
            "correo": correo,
            "nombre": datos["nombre"],
            "apellido": datos["apellido"],
            "identificacion": datos["identificacion"],
            "registros_totales": n_registros,
            "promedio_porcentaje": round(prom_pct, 1),
            "promedio_instancias": round(prom_instancias, 2),
            "faltas": faltas,
        })

    # Ordenar por promedio descendente
    estudiantes_con_promedio.sort(key=lambda x: x["promedio_porcentaje"], reverse=True)

    # Mostrar al menos 3 estudiantes
    print(f"\n{'='*100}")
    print(f"ASISTENCIA ZOOM — Consulta de {len(estudiantes_con_promedio)} estudiantes únicos")
    print(f"{'='*100}\n")

    for idx, est in enumerate(estudiantes_con_promedio[:min(3, len(estudiantes_con_promedio))], 1):
        print(f"\n[{idx}] {est['nombre']} {est['apellido']}")
        print(f"    Correo: {est['correo']}")
        print(f"    ID: {est['identificacion']}")
        print(f"    Registros: {est['registros_totales']} clases")
        print(f"    Promedio asistencia: {est['promedio_porcentaje']}%")
        print(f"    Promedio momentos (0-3): {est['promedio_instancias']}/3")

        if est['faltas']:
            print(f"    Faltas/bajos ({len(est['faltas'])} de {est['registros_totales']}):")
            for falta in est['faltas']:
                print(f"      - {falta['curso']} ({falta['fecha']}): {falta['porcentaje']}%, {falta['instancias']}/3 momentos")
        else:
            print(f"    [OK] Sin faltas registradas")

    # Estadísticas generales
    print(f"\n{'='*100}")
    print(f"ESTADÍSTICAS GENERALES")
    print(f"{'='*100}")
    print(f"Total estudiantes: {len(estudiantes_con_promedio)}")
    print(f"Total registros de asistencia: {sum(e['registros_totales'] for e in estudiantes_con_promedio)}")
    promedio_general = sum(e['promedio_porcentaje'] for e in estudiantes_con_promedio) / len(estudiantes_con_promedio) if estudiantes_con_promedio else 0
    print(f"Promedio general de asistencia: {round(promedio_general, 1)}%")
    print(f"Estudiantes con <70% promedio: {sum(1 for e in estudiantes_con_promedio if e['promedio_porcentaje'] < 70)}")

if __name__ == "__main__":
    try:
        consultar_asistencia()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
