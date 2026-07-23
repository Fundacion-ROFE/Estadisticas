# -*- coding: utf-8 -*-
"""
Cruce de solo-lectura: mujeres-rofe-db.Users (2023/2024) y jovenes-creativos.User (2023)
contra participants de Supabase, por cédula/email — SOLO conteos agregados, nunca se
imprime una cédula/email individual. No escribe nada en ninguna de las dos bases.

Uso:
    python cruzar_mongo_supabase.py
"""

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

from pymongo import MongoClient


def cargar_env_local():
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ruta = os.path.join(raiz, ".env.local")
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip())


def limpiar_cedula(v):
    if not v:
        return None
    v = re.sub(r"\D", "", str(v))
    return v or None


def limpiar_email(v):
    if not v:
        return None
    return str(v).strip().lower() or None


def supabase_get_paginado(url, headers, tabla, select, tam_pagina=1000):
    filas = []
    desde = 0
    while True:
        req = urllib.request.Request(
            f"{url}/rest/v1/{tabla}?select={select}",
            headers={**headers, "Range-Unit": "items", "Range": f"{desde}-{desde + tam_pagina - 1}"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            pagina = json.loads(resp.read())
        filas.extend(pagina)
        if len(pagina) < tam_pagina:
            break
        desde += tam_pagina
    return filas


def main():
    cargar_env_local()
    mongo_uri = os.environ["MONGO_URI"]
    sb_url = os.environ["SUPABASE_URL"].rstrip("/")
    sb_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "User-Agent": "panel-datos-etl/1.0",
    }

    print("Cargando participants de Supabase (cedula + email, todos los programas)...")
    filas = supabase_get_paginado(sb_url, headers, "participants", "q10_id,email")
    cedulas_sb = {limpiar_cedula(f["q10_id"]) for f in filas if limpiar_cedula(f["q10_id"])}
    emails_sb = {limpiar_email(f["email"]) for f in filas if limpiar_email(f["email"])}
    print(f"  Supabase: {len(filas)} participants -> {len(cedulas_sb)} cédulas únicas, {len(emails_sb)} emails únicos\n")

    cliente = MongoClient(mongo_uri, serverSelectionTimeoutMS=15000)

    # --- mujeres-rofe-db.Users, 2023 y 2024 ---
    for anio in (2023, 2024):
        col = cliente["mujeres-rofe-db"]["Users"]
        docs = list(
            col.find(
                {"creationDate": {"$gte": f"{anio}-01-01", "$lt": f"{anio + 1}-01-01"}},
                {"documentNumber": 1, "email": 1},
            )
        )
        # creationDate puede ser string o date; si el filtro de string no matchea, reintenta con datetime
        if not docs:
            from datetime import datetime

            docs = list(
                col.find(
                    {"creationDate": {"$gte": datetime(anio, 1, 1), "$lt": datetime(anio + 1, 1, 1)}},
                    {"documentNumber": 1, "email": 1},
                )
            )
        cedulas_mongo = {limpiar_cedula(d.get("documentNumber")) for d in docs if limpiar_cedula(d.get("documentNumber"))}
        emails_mongo = {limpiar_email(d.get("email")) for d in docs if limpiar_email(d.get("email"))}

        nueva_por_cedula = cedulas_mongo - cedulas_sb
        nueva_por_email = emails_mongo - emails_sb
        # "genuinamente nueva" = ni la cédula NI el email están en Supabase
        set_emails_de_cedulas_conocidas = set()  # placeholder si se quisiera cruzar combinado

        print(f"mujeres-rofe-db.Users — cohorte {anio}")
        print(f"  documentos: {len(docs)}  (con cédula: {len(cedulas_mongo)}, con email: {len(emails_mongo)})")
        print(f"  cédulas que YA existen en Supabase: {len(cedulas_mongo & cedulas_sb)}")
        print(f"  cédulas que NO existen en Supabase (candidatas a nuevas): {len(nueva_por_cedula)}")
        print(f"  emails que YA existen en Supabase: {len(emails_mongo & emails_sb)}")
        print(f"  emails que NO existen en Supabase: {len(nueva_por_email)}\n")

    # --- jovenes-creativos.User, 2023 ---
    col = cliente["jovenes-creativos"]["User"]
    docs = list(
        col.find(
            {"creationDate": {"$gte": "2023-01-01", "$lt": "2024-01-01"}},
            {"profile.documentNumber": 1, "profile.email": 1},
        )
    )
    if not docs:
        from datetime import datetime

        docs = list(
            col.find(
                {"creationDate": {"$gte": datetime(2023, 1, 1), "$lt": datetime(2024, 1, 1)}},
                {"profile.documentNumber": 1, "profile.email": 1},
            )
        )
    cedulas_mongo = {
        limpiar_cedula((d.get("profile") or {}).get("documentNumber")) for d in docs
    } - {None}
    emails_mongo = {limpiar_email((d.get("profile") or {}).get("email")) for d in docs} - {None}

    print("jovenes-creativos.User — cohorte 2023")
    print(f"  documentos: {len(docs)}  (con cédula: {len(cedulas_mongo)}, con email: {len(emails_mongo)})")
    print(f"  cédulas que YA existen en Supabase: {len(cedulas_mongo & cedulas_sb)}")
    print(f"  cédulas que NO existen en Supabase (candidatas a nuevas): {len(cedulas_mongo - cedulas_sb)}")
    print(f"  emails que YA existen en Supabase: {len(emails_mongo & emails_sb)}")
    print(f"  emails que NO existen en Supabase: {len(emails_mongo - emails_sb)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
