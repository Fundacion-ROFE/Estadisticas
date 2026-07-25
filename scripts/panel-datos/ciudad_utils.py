#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalización de ciudad — módulo de referencia, copiar/importar, no reescribir.

Resuelve el problema documentado en docs/convenciones.md ("Normalización de ciudades"):
cientos de variantes de una misma ciudad (tildes, mayúsculas, puntuación, nombre
administrativo vs común) rompían filtros silenciosamente (incidente 2026-07-24, ver
claude_sessions.md — un filtro `'BOGOTA' in ciudad.upper()` descartó 431/512 filas de
Bogotá porque .upper() no quita tildes).

Fuente de verdad real: Supabase. `normalizar_ciudad()` (función SQL, replicada aquí
byte a byte) ya vive como columna generada `ciudad_norm` en `participants`,
`postulantes_mr` y `postulantes_jc` — filtra SIEMPRE por esa columna, nunca por
`ciudad` crudo. `ciudad_alias` (tabla) fusiona nombres distintos del mismo municipio
(Bogotá D.C./BGT -> Bogotá, Cartagena de Indias -> Cartagena) — este módulo la lee
para expandir un filtro a todas las claves que aplican.

Uso típico en un script de extracción:

    from ciudad_utils import normalizar_ciudad, claves_para, Supa

    supa = Supa(url, key)
    claves = claves_para("Bogotá", supa)          # -> ['BOGOTA', 'BOGOTA DC']
    filtro = ",".join(claves)
    filas = supa.get_todo(f"/postulantes_mr?ciudad_norm=in.({filtro})&select=*")

Ver docs/migrations/013_normalizar_ciudad.sql para el origen de ciudad_norm/ciudad_alias.
"""
import json
import re
import unicodedata
import urllib.error
import urllib.request

USER_AGENT = "ciudad-utils/1.0"

_TABLA_TILDES = str.maketrans("ÁÉÍÓÚÑÜáéíóúñü", "AEIOUNUaeiounu")
_NO_ALFANUM = re.compile(r"[^A-Z0-9 ]")
_ESPACIOS = re.compile(r"\s+")


def normalizar_ciudad(valor):
    """Réplica exacta (mismo algoritmo) de public.normalizar_ciudad() en Supabase:
    quita tildes, mayúsculas, colapsa puntuación/espacios. NO expande alias — para
    eso usar claves_para()."""
    if not valor:
        return None
    limpio = valor.translate(_TABLA_TILDES).upper()
    limpio = _NO_ALFANUM.sub("", limpio)
    limpio = _ESPACIOS.sub(" ", limpio).strip()
    return limpio or None


class Supa:
    """Cliente REST mínimo contra PostgREST — copiado del patrón ya establecido
    (ver feedback: nunca reescribir Supa/get_todo de memoria, el bug offset+=page
    faltante ya causó un cuelgue real una vez)."""

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
            url = f"{self.base}{ruta}{sep}limit={page}&offset={offset}".replace(" ", "%20")
            req = urllib.request.Request(url, headers=headers)
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


def cargar_alias(supa):
    """dict clave_norm -> ciudad_canonica, leído en vivo de la tabla ciudad_alias.
    Si la tabla no existe o falla la consulta, devuelve {} (claves_para sigue
    funcionando, solo sin fusión de alias — degrada, no rompe)."""
    try:
        filas = supa.get_todo("/ciudad_alias?select=clave_norm,ciudad_canonica")
    except RuntimeError:
        return {}
    return {f["clave_norm"]: f["ciudad_canonica"] for f in filas}


def claves_para(ciudad, supa=None, alias=None):
    """Dada una ciudad tal como la escribiría un humano ("Bogotá", "cartagena"),
    devuelve la lista de valores de ciudad_norm que hay que incluir en un filtro
    `ciudad_norm=in.(...)` para cubrir todas sus variantes conocidas (incluyendo
    alias de mismo-municipio-nombre-distinto).

    Pasa `supa` (instancia Supa ya conectada) para leer ciudad_alias en vivo, o
    `alias` si ya lo cargaste antes (evita una consulta repetida en scripts que
    resuelven varias ciudades)."""
    clave = normalizar_ciudad(ciudad)
    if clave is None:
        return []
    if alias is None:
        alias = cargar_alias(supa) if supa is not None else {}

    # clave puede ser la clave_norm de un alias (ej. "BOGOTA DC") -> usar su canónica
    canonica = alias.get(clave, clave)
    # todas las claves (incluyendo la propia canónica) que apuntan a esa canónica
    claves = {canonica} | {k for k, v in alias.items() if v == canonica}
    return sorted(claves)
