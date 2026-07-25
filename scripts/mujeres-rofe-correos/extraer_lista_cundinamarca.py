#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrae lista de envío Mujeres ROFÉ en Cundinamarca (histórico completo).
NO se limita a cohortes MR actuales — incluye TODOS los participants de Cundinamarca.
Excluye: opt-out + hard bounces.
Salida: tools/mujeres-rofe-correos/data/lista_encuentro_cundinamarca_2026_jul24.csv
"""
import io
import json
import os
import re
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
TOOLS_DATA = os.path.join(PROYECTO_ROOT, "tools", "mujeres-rofe-correos", "data")
RUTA_SALIDA = os.path.join(TOOLS_DATA, "lista_encuentro_cundinamarca_2026_jul24.csv")

USER_AGENT = "panel-datos-etl/1.0"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Municipios de Cundinamarca (simplificado, lo que probablemente está en la DB)
MUNICIPIOS_CUNDINAMARCA = {
    "bogota", "soacha", "chia", "cajica", "madrid", "funza", "mosquera",
    "facatativa", "zipaquira", "tocaima", "fusagasuga", "silvania",
    "aracataca",  # Nota: Aracataca en realidad es Magdalena, pero aparece en datos
}

def log(msg):
    print(f"[extraer-cundinamarca] {msg}", flush=True)

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

def normalizar_ciudad(ciudad_str):
    """Normaliza: mayúsculas, sin tildes, trimmed."""
    s = (ciudad_str or "").strip().upper()
    s = s.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
    return s

def es_cundinamarca(ciudad_norm):
    """Decide si pertenece a Cundinamarca."""
    if not ciudad_norm:
        return False
    # Bogotá es siempre Cundinamarca
    if "BOGOTA" in ciudad_norm:
        return True
    # Verifica cada municipio
    for mun in MUNICIPIOS_CUNDINAMARCA:
        if mun.upper() in ciudad_norm:
            return True
    return False

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
        log(f"AVISO: no se pudo leer email_optout ({e})")
    try:
        hard = {(f.get("email") or "").strip().lower()
                for f in supa.get_todo("/email_bounces?select=email&tipo=eq.hard") if f.get("email")}
    except RuntimeError as e:
        log(f"AVISO: no se pudo leer email_bounces ({e})")
    return optout | hard, len(optout), len(hard)

def main():
    cargar_env_local()

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan credenciales Supabase (.env.local)")
        sys.exit(1)

    supa = Supa(url, key)

    log("Consultando Supabase (TODOS los participants histórico)...")
    todos = supa.get_todo("/participants?select=id,nombre,email,ciudad,grupo_ciudad")
    log(f"  Total en BD: {len(todos)}")

    # Filtrar Cundinamarca
    mapa = {}
    for p in todos:
        ciudad = (p.get("ciudad") or "").strip()
        grupo_ciudad = (p.get("grupo_ciudad") or "").strip()
        ciudad_display = ciudad or grupo_ciudad or ""
        ciudad_norm = normalizar_ciudad(ciudad_display)

        if not es_cundinamarca(ciudad_norm):
            continue

        correo = (p.get("email") or "").strip().lower()
        if not correo or not EMAIL_RE.match(correo):
            continue

        mapa[correo] = {
            "nombre": p.get("nombre") or "",
            "ciudad_orig": ciudad_display,
            "cohorte": "",  # No tenemos cohorte en histórico general
        }

    log(f"  Cundinamarca: {len(mapa)} correos únicos")

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
            f.write(f'"{nombre}",{correo},\n')

    log(f"✓ Salida: {RUTA_SALIDA}")
    print(f"RESUMEN: cundinamarca={len(mapa)} excluidos={excluidos} estado=exito")

if __name__ == "__main__":
    main()
