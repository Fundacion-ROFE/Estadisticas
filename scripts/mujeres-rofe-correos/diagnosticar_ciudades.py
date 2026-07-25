#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnóstico: cuáles ciudades hay en participants (MR)."""
import io
import json
import os
import sys
import urllib.error
import urllib.request

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

cargar_env_local()
url = os.environ.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not url or not key:
    print("ERROR: faltan credenciales Supabase")
    sys.exit(1)

supa = Supa(url, key)

# Obtener cursos MR
print("[*] Leyendo cursos MR...")
cursos = supa.get_todo("/courses?programa=eq.mr&select=id,cohorte")
cohorte_por_curso = {c["id"]: c["cohorte"] for c in cursos}
ids_cursos = list(cohorte_por_curso.keys())
print(f"    {len(ids_cursos)} cursos MR encontrados")

# Obtener matrículas
print("[*] Leyendo matrículas...")
matriculas = []
LOTE_IN = 200
for i in range(0, len(ids_cursos), LOTE_IN):
    grupo = ids_cursos[i:i + LOTE_IN]
    filtro = ",".join(grupo)
    matriculas.extend(supa.get_todo(
        f"/enrollments?course_id=in.({filtro})&select=participant_id,course_id"))
print(f"    {len(matriculas)} matrículas encontradas")

cohorte_por_participante = {}
for m in matriculas:
    cohorte = cohorte_por_curso.get(m["course_id"])
    actual = cohorte_por_participante.get(m["participant_id"])
    if actual is None or (cohorte and cohorte > actual):
        cohorte_por_participante[m["participant_id"]] = cohorte

# Obtener participantes (TODAS las ciudades)
print("[*] Leyendo participantes MR...")
ids_participantes = list(cohorte_por_participante.keys())
ciudades = {}

for i in range(0, len(ids_participantes), LOTE_IN):
    grupo = ids_participantes[i:i + LOTE_IN]
    filtro = ",".join(grupo)
    participantes = supa.get_todo(
        f"/participants?id=in.({filtro})&select=id,nombre,email,ciudad,grupo_ciudad")
    for p in participantes:
        ciudad = (p.get("ciudad") or "").strip()
        grupo_ciudad = (p.get("grupo_ciudad") or "").strip()
        clave = ciudad or grupo_ciudad or "(sin ciudad)"
        if clave not in ciudades:
            ciudades[clave] = []
        ciudades[clave].append({
            "nombre": p.get("nombre") or "",
            "email": p.get("email") or "",
            "ciudad": ciudad,
            "grupo_ciudad": grupo_ciudad,
        })

print(f"\n[RESULTADO] {len(ciudades)} ciudades/grupos encontrados:")
print("=" * 80)
for ciudad in sorted(ciudades.keys(), key=lambda x: -len(ciudades[x])):
    print(f"\n{ciudad}: {len(ciudades[ciudad])} personas")
    for p in ciudades[ciudad][:3]:
        print(f"  - {p['nombre'][:40]:40} ({p['email']})")
    if len(ciudades[ciudad]) > 3:
        print(f"  ... y {len(ciudades[ciudad]) - 3} más")
