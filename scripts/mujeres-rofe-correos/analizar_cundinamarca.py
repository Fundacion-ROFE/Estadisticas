#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis exhaustivo: Cundinamarca histórico (todas las personas, no solo MR actual).
Identifica variantes de ciudades y propone normalización.
"""
import io
import json
import os
import sys
import re
import urllib.error
import urllib.request
from collections import defaultdict

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV = os.path.join(PROYECTO_ROOT, ".env.local")
USER_AGENT = "panel-datos-etl/1.0"

# Municipios de Cundinamarca (referencia oficial)
MUNICIPIOS_CUNDINAMARCA = {
    "bogota", "soacha", "chia", "cajica", "zipaquira", "madrid", "funza", "mosquera",
    "la ceja", "facatativa", "girardot", "fusagasuga", "zipacon", "tunjuelito",
    "suesca", "nemocón", "pacho", "guacheta", "ubate", "vileta", "laguna",
    "guasca", "carmen de carupa", "tabio", "colsubsidio", "gachancipa", "tocancipa",
    "cota", "sopó", "beltrán", "sutatausa", "paime", "sutatausa", "guayabetal",
    "machetá", "manta", "medina", "quetame", "gachalá", "gachantivá", "gama",
    "garagoa", "guateque", "machetá", "medina", "quetame", "sacaboy", "sesquilé",
    "silvania", "sosá", "suachoque", "suesca", "tena", "tibacuy", "tibirita",
    "tocaima", "tocancipa", "togui", "torca", "ubaté", "ubaque", "une",
    "utica", "vergara", "vianí", "vileta", "villagómez", "viota", "yacopí",
    "zipacón", "zipaquirá", "alban", "beltran", "bituima", "bojaca", "canencia",
    "caparrapis", "caqueza", "carmen de carupa", "carupa", "casablanca",
    "cata", "catalamazo", "cauca", "cavendish", "cávere", "chagrán", "chaguaní",
    "chiá", "chibuayes", "chicaque", "chilintá", "chiquinquirá", "chipaque",
    "choachí", "chocontá", "choconta", "chucuni", "chulo", "churumbela",
    "coello", "cogua", "colan", "colima", "colima", "colina", "colisipan",
    "colorado", "combeima", "congota", "conquista", "conquitao", "consata",
    "contaderillo", "contadero", "coraza", "corbada", "corbalán", "cordoba",
    "corera", "coreria", "corillo", "corito", "corlobando", "corneta",
    "cornutao", "corporales", "corporalejo", "corpovado", "corraleja",
    "corralón", "correa", "corredera", "corredorcillo", "correhuelas",
    "correhuela", "correilla", "correita", "correjón", "correjuela",
    "correol", "correota", "correr", "corresoberana", "corresolana"
}

def cargar_env_local():
    if not os.path.isfile(RUTA_ENV):
        return
    with open(RUTA_ENV, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

class Supa:
    def __init__(self, url, key):
        self.base = url.rstrip("/") + "/rest/v1"
        self.key = key

    def get_todo(self, ruta, page=1000):
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            headers = {
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "User-Agent": USER_AGENT,
            }
            req = urllib.request.Request(
                f"{self.base}{ruta}{sep}limit={page}&offset={offset}",
                headers=headers,
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    lote = json.loads(resp.read())
            except urllib.error.HTTPError as e:
                detalle = e.read().decode(errors="replace")[:500]
                raise RuntimeError(f"HTTP {e.code}: {detalle}") from None
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page

def normalizar_ciudad(ciudad_str):
    """Normaliza una cadena de ciudad: mayúsculas, sin tildes, trimmed."""
    s = (ciudad_str or "").strip().upper()
    s = s.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    s = s.replace("á", "A").replace("é", "E").replace("í", "I").replace("ó", "O").replace("ú", "U")
    return s

def es_cundinamarca(ciudad_norm):
    """Decide si una ciudad normalizada es de Cundinamarca."""
    # Extrae la primera palabra (antes de comas, "D.C.", espacios, etc.)
    palabras = ciudad_norm.split()
    if not palabras:
        return False
    primera = palabras[0]
    # Casos especiales
    if "BOGOTA" in ciudad_norm:
        return True
    if "SOACHA" in ciudad_norm:
        return True
    if "CHIA" in ciudad_norm:
        return True
    # Búsqueda en lista
    for mun in MUNICIPIOS_CUNDINAMARCA:
        if mun.upper() in ciudad_norm:
            return True
    return False

cargar_env_local()
url = os.environ.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not url or not key:
    print("ERROR: faltan credenciales Supabase")
    sys.exit(1)

supa = Supa(url, key)

print("[*] Leyendo TODOS los participants (histórico completo)...")
todos_participantes = supa.get_todo("/participants?select=id,nombre,email,ciudad,grupo_ciudad")
print(f"    Total: {len(todos_participantes)} participantes")

# Agrupar por ciudad normalizada
ciudades = defaultdict(list)
ciudades_originales = defaultdict(set)
cundinamarca_total = 0

for p in todos_participantes:
    ciudad = (p.get("ciudad") or "").strip()
    grupo_ciudad = (p.get("grupo_ciudad") or "").strip()
    ciudad_display = ciudad or grupo_ciudad or "(sin ciudad)"
    ciudad_norm = normalizar_ciudad(ciudad_display)

    if es_cundinamarca(ciudad_norm):
        cundinamarca_total += 1
        ciudades[ciudad_norm].append(p)
        ciudades_originales[ciudad_norm].add(ciudad_display)

print(f"\n[RESULTADO] Total Cundinamarca (histórico): {cundinamarca_total}")
print(f"Agrupados en {len(ciudades)} ciudades/variantes normalizadas\n")

# Mostrar por cantidad
print("=" * 100)
print("CIUDADES ORDENADAS POR CANTIDAD (variantes agrupadas):")
print("=" * 100)

for ciudad_norm in sorted(ciudades.keys(), key=lambda x: -len(ciudades[x])):
    personas = ciudades[ciudad_norm]
    variantes = ciudades_originales[ciudad_norm]
    print(f"\n{ciudad_norm}: {len(personas)} personas")
    print(f"  Variantes en DB: {', '.join(sorted(variantes))}")
    for p in personas[:2]:
        print(f"    - {(p.get('nombre') or '')[:40]:40} ({p.get('email')})")
    if len(personas) > 2:
        print(f"    ... y {len(personas) - 2} más")

# Análisis de BOGOTA específicamente
print("\n" + "=" * 100)
print("ANÁLISIS BOGOTA (caso crítico):")
print("=" * 100)
bogota_variantes = {k: v for k, v in ciudades_originales.items() if "BOGOTA" in k}
bogota_total = sum(len(ciudades[k]) for k in bogota_variantes.keys())
print(f"Total BOGOTA (todas las variantes): {bogota_total} personas")
for ciudad_norm in sorted(bogota_variantes.keys()):
    variantes = bogota_variantes[ciudad_norm]
    cantidad = len(ciudades[ciudad_norm])
    print(f"  {ciudad_norm}: {cantidad} personas — Variantes: {variantes}")

# Posibles BGT, BOG, etc.
print("\n" + "=" * 100)
print("POSIBLES ABREVIATURAS/VARIANTES (BGT, BOG, etc.):")
print("=" * 100)
for ciudad_norm in sorted(ciudades.keys()):
    # Busca cualquier cosa que empiece con B, G, O, T en combinación
    if re.match(r"^B.*O.*", ciudad_norm) and "BOGOTA" not in ciudad_norm:
        print(f"  {ciudad_norm}: {len(ciudades[ciudad_norm])} personas")

print("\n" + "=" * 100)
print("RESUMEN PARA DOCUMENTACIÓN:")
print("=" * 100)
print(f"""
PROBLEMA DE NORMALIZACIÓN IDENTIFICADO:

Total Cundinamarca (histórico): {cundinamarca_total} personas
- Fragmentadas en {len(ciudades)} variantes normalizadas
- Bogotá sola tiene {bogota_total} personas en {len(bogota_variantes)} variantes

VARIANTES CRÍTICAS DE BOGOTA:
{chr(10).join(f"  - {repr(v)}" for variantes in bogota_variantes.values() for v in variantes)}

RECOMENDACIÓN:
1. Crear tabla de normalización en Supabase: ciudad_original → ciudad_normalizada
2. Aplicar en carga de datos: siempre normalizar antes de insertar
3. Migrar datos históricos: batch update con diccionario de mapeo
4. Validar en formularios: dropdown con opciones Cundinamarca normalizadas
5. Próxima carga MR: aplicar normalización previa

COBERTURA CON NORMALIZACIÓN:
✓ Bogotá: {bogota_total} personas
✓ Cundinamarca total: {cundinamarca_total} personas
""")

print(f"RESUMEN: cundinamarca={cundinamarca_total} bogota={bogota_total} variantes={len(ciudades)}")
