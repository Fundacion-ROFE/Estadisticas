#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrae lista de envío para Mujeres ROFÉ en Bogotá (programa=mr, ciudad=Bogotá).
Combina Supabase (histórico actual) + Excel (2024, cohortes faltantes).
Excluye: opt-out + hard bounces.
Salida: tools/mujeres-rofe-correos/data/lista_encuentro_bogota_2026_jul24.csv
"""
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from openpyxl import load_workbook

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_BD_DEFAULT = r"C:\Users\EstudiantesJC\Downloads\BD-Mujeres ROFÉ 2026 (2).xlsx"
TOOLS_DATA = os.path.join(PROYECTO_ROOT, "tools", "mujeres-rofe-correos", "data")
RUTA_SALIDA = os.path.join(TOOLS_DATA, "lista_encuentro_bogota_2026_jul24.csv")

USER_AGENT = "panel-datos-etl/1.0"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def log(msg):
    print(f"[extraer-bogota] {msg}", flush=True)


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
                raise RuntimeError(f"HTTP {e.code} en GET {ruta}: {detalle}") from None
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page


def extraer_supabase_bogota():
    """Devuelve dict correo_lower -> {nombre, cohorte, fuente='supabase'}
    para Bogotá y programa=mr."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan credenciales Supabase (.env.local)")
        return {}

    supa = Supa(url, key)

    # Paso 1: Obtener cursos MR
    cursos = supa.get_todo("/courses?programa=eq.mr&select=id,cohorte")
    if not cursos:
        log("AVISO: no hay courses con programa=mr en Supabase")
        return {}
    cohorte_por_curso = {c["id"]: c["cohorte"] for c in cursos}
    ids_cursos = list(cohorte_por_curso.keys())

    # Paso 2: Obtener matrículas para esos cursos
    matriculas = []
    LOTE_IN = 200
    for i in range(0, len(ids_cursos), LOTE_IN):
        grupo = ids_cursos[i:i + LOTE_IN]
        filtro = ",".join(grupo)
        matriculas.extend(supa.get_todo(
            f"/enrollments?course_id=in.({filtro})&select=participant_id,course_id"))

    # Paso 3: Cohorte máxima por participante
    cohorte_por_participante = {}
    for m in matriculas:
        cohorte = cohorte_por_curso.get(m["course_id"])
        actual = cohorte_por_participante.get(m["participant_id"])
        if actual is None or (cohorte and cohorte > actual):
            cohorte_por_participante[m["participant_id"]] = cohorte

    # Paso 4: Obtener participantes (Bogotá solamente)
    ids_participantes = list(cohorte_por_participante.keys())
    resultado = {}

    # Filtro: ciudad='Bogotá' (o 'BOGOTA' — revisar la BD)
    for i in range(0, len(ids_participantes), LOTE_IN):
        grupo = ids_participantes[i:i + LOTE_IN]
        filtro = ",".join(grupo)
        participantes = supa.get_todo(
            f"/participants?id=in.({filtro})&select=id,nombre,email,ciudad")
        for p in participantes:
            # Filtrar por ciudad Bogotá (flexible: cualquier variante con "bogot")
            ciudad = (p.get("ciudad") or "").strip()
            ciudad_norm = ciudad.upper().replace("Á", "A").replace("Ó", "O")
            # Busca cualquier variante: "BOGOTA", "BOGOTA D.C.", "BOGOTA, D.C.", etc.
            if not ciudad_norm.startswith("BOGOTA"):
                continue

            correo = (p.get("email") or "").strip().lower()
            if not correo or not EMAIL_RE.match(correo):
                continue
            resultado[correo] = {
                "nombre": p.get("nombre") or "",
                "cohorte": cohorte_por_participante.get(p["id"], ""),
                "fuente": "supabase",
            }
    return resultado


def extraer_supresiones():
    """Set de correos (lowercase) a excluir: opt-out + hard bounces."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return set(), 0, 0
    supa = Supa(url, key)
    optout, hard = set(), set()
    try:
        optout = {(f.get("email") or "").strip().lower()
                  for f in supa.get_todo("/email_optout?select=email") if f.get("email")}
    except RuntimeError as e:
        log(f"AVISO: no se pudo leer email_optout ({e}) — no se excluye opt-out")
    try:
        hard = {(f.get("email") or "").strip().lower()
                for f in supa.get_todo("/email_bounces?select=email&tipo=eq.hard") if f.get("email")}
    except RuntimeError as e:
        log(f"AVISO: no se pudo leer email_bounces ({e}) — no se excluyen rebotes")
    return optout | hard, len(optout), len(hard)


def main():
    cargar_env_local()

    log("Consultando Supabase (programa=mr, ciudad=Bogotá)...")
    mapa = extraer_supabase_bogota()
    log(f"  Encontrados: {len(mapa)} correos únicos")

    # Excluir supresiones
    supresiones, n_optout, n_hard = extraer_supresiones()
    excluidos = 0
    if supresiones:
        antes = len(mapa)
        mapa = {c: d for c, d in mapa.items() if c not in supresiones}
        excluidos = antes - len(mapa)

    log(f"Supresiones: {n_optout} opt-out, {n_hard} hard bounces → {excluidos} excluidos")
    log(f"Lista final: {len(mapa)} correos")

    # Generar CSV
    os.makedirs(TOOLS_DATA, exist_ok=True)
    with open(RUTA_SALIDA, "w", encoding="utf-8", newline="") as f:
        f.write("nombre,correo,cohorte\n")
        for correo in sorted(mapa.keys()):
            d = mapa[correo]
            nombre = (d.get("nombre") or "").replace('"', '""')
            f.write(f'"{nombre}",{correo},{d.get("cohorte") or ""}\n')

    log(f"✓ Salida: {RUTA_SALIDA}")
    print(f"RESUMEN: bogota={len(mapa)} excluidos={excluidos} estado=exito")


if __name__ == "__main__":
    main()
