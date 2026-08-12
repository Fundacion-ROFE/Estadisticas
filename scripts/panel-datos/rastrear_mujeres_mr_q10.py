# -*- coding: utf-8 -*-
"""
rastrear_mujeres_mr_q10.py — ¿Cuántas de las mujeres del CSV "Plataforma MR" están de
verdad en Q10/Supabase? Contraste RIGUROSO multi-campo (cédula → correo → nombre), año por
año, para no dar por "sin Q10" a alguien que sí está pero con la cédula escrita distinto.

Pedido del usuario (2026-08-12): "mira las mujeres del CSV, de qué año son, contrasta con
Supabase, si no la ves por cédula intenta nombre/número/correo, mira H1Test para corroborar,
al final dame la tabla del % real rastreado y exporta a xlsx las que no aparezcan por
ningún campo."

`participants` es la tabla derivada de Q10 (el usuario confirma: "todo Q10 ya está en
Supabase"). NO tiene columna de teléfono, así que el match por número no aplica CONTRA
participants — se deja constancia; se usa cédula/correo/nombre, que sí están.

Modo por defecto: SOLO REPORTE + xlsx de no-encontradas. Pasar --aplicar para además enlazar
en postulantes_mr.participant_id las que se resolvieron por correo/nombre (hoy sin enlace).

Uso:
    python rastrear_mujeres_mr_q10.py            # tabla año×método + xlsx de no-encontradas
    python rastrear_mujeres_mr_q10.py --aplicar   # + enlaza participant_id de los matches nuevos
"""

import argparse
import io
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_CSV = r"C:\Users\EstudiantesJC\Downloads\BD-Mujeres ROFÉ 2026 - Plataforma MR.csv"
RUTA_XLSX_OUT = r"C:\Users\EstudiantesJC\Downloads\mujeres_mr_sin_q10_%s.xlsx" % datetime.now().strftime("%Y%m%d_%H%M")

sys.path.insert(0, DIRECTORIO_SCRIPT)
from enriquecimiento_helper import cargar_hoja  # noqa: E402
from cargar_supabase import Supa, cargar_env_local  # noqa: E402


def log(msg): print(f"[rastreo-mr] {msg}", flush=True)


def norm_ced(v): return re.sub(r"\D", "", str(v or "")).lstrip("0")
def norm_email(v):
    s = str(v or "").strip().lower()
    m = re.search(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", s)
    return m.group(0) if m else ""
def _sin_tildes(s): return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
def norm_nombre(v):
    s = _sin_tildes(str(v or "")).lower()
    s = re.sub(r"[^a-z\s]", " ", s)
    toks = [t for t in s.split() if len(t) > 1]
    return " ".join(sorted(toks))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--solo-correo", action="store_true",
                    help="al enlazar, usar SOLO matches por correo (excluye nombre, riesgo homónimo)")
    args = ap.parse_args()

    cargar_env_local()
    supa = Supa(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    # 1) CSV
    _cols, filas = cargar_hoja(RUTA_CSV)
    mujeres, vistos = [], set()
    for f in filas:
        ced = norm_ced(f.get("documentNumber"))
        clave = ced or norm_email(f.get("email"))
        if not clave or clave in vistos:
            continue
        vistos.add(clave)
        mujeres.append({
            "cedula": ced,
            "cedula_digits": re.sub(r"\D", "", str(f.get("documentNumber") or "")),  # sin lstrip — formato de postulantes_mr
            "cedula_raw": str(f.get("documentNumber") or "").strip(),
            "anio": str(f.get("Año") or "").strip() or "sin año",
            "nombre": f"{(f.get('firstName') or '').strip()} {(f.get('lastName') or '').strip()}".strip(),
            "email": norm_email(f.get("email")),
            "celular": re.sub(r"\D", "", str(f.get("phoneNumber") or "")),
        })
    log(f"CSV: {len(mujeres)} mujeres únicas")

    # 2) participants (Q10) — índices por cédula / correo / nombre
    parts = supa.get_todo("/participants?select=id,q10_id,nombre,email")
    by_ced = {norm_ced(p["q10_id"]): p["id"] for p in parts if p.get("q10_id")}
    by_email = {}
    by_nombre = {}
    for p in parts:
        e = norm_email(p.get("email"))
        if e:
            by_email.setdefault(e, p["id"])
        n = norm_nombre(p.get("nombre"))
        if n:
            by_nombre.setdefault(n, p["id"])
    log(f"participants (Q10): {len(parts)} · índices: cédula={len(by_ced)} correo={len(by_email)} nombre={len(by_nombre)}")

    # 3) match multi-campo, prioridad cédula > correo > nombre
    for m in mujeres:
        if m["cedula"] and m["cedula"] in by_ced:
            m["metodo"], m["pid"] = "cédula", by_ced[m["cedula"]]
        elif m["email"] and m["email"] in by_email:
            m["metodo"], m["pid"] = "correo", by_email[m["email"]]
        elif norm_nombre(m["nombre"]) in by_nombre and norm_nombre(m["nombre"]):
            m["metodo"], m["pid"] = "nombre", by_nombre[norm_nombre(m["nombre"])]
        else:
            m["metodo"], m["pid"] = "NO ENCONTRADA", None

    # 4) tabla año × método
    anios = sorted({m["anio"] for m in mujeres})
    metodos = ["cédula", "correo", "nombre", "NO ENCONTRADA"]
    tabla = defaultdict(lambda: Counter())
    for m in mujeres:
        tabla[m["anio"]][m["metodo"]] += 1

    print("\n" + "=" * 78)
    print(f"{'Año':<10}{'Total':>8}{'Cédula':>9}{'Correo':>9}{'Nombre':>9}{'NO ENC.':>9}{'% en Q10':>11}")
    print("-" * 78)
    g = Counter()
    for a in anios:
        t = sum(tabla[a].values())
        enc = t - tabla[a]["NO ENCONTRADA"]
        print(f"{a:<10}{t:>8}{tabla[a]['cédula']:>9}{tabla[a]['correo']:>9}{tabla[a]['nombre']:>9}"
              f"{tabla[a]['NO ENCONTRADA']:>9}{100*enc/t:>10.1f}%")
        for k, v in tabla[a].items():
            g[k] += v
    tot = sum(g.values())
    enc_g = tot - g["NO ENCONTRADA"]
    print("-" * 78)
    print(f"{'TOTAL':<10}{tot:>8}{g['cédula']:>9}{g['correo']:>9}{g['nombre']:>9}"
          f"{g['NO ENCONTRADA']:>9}{100*enc_g/tot:>10.1f}%")
    print("=" * 78)
    log(f"Rastreadas en Q10: {enc_g}/{tot} ({100*enc_g/tot:.1f}%) · NO encontradas: {g['NO ENCONTRADA']}")

    # 5) xlsx de las NO encontradas
    no_enc = [m for m in mujeres if m["metodo"] == "NO ENCONTRADA"]
    if no_enc:
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "sin_q10"
        ws.append(["cedula", "nombre", "email", "celular", "anio"])
        for m in sorted(no_enc, key=lambda x: (x["anio"], x["nombre"])):
            ws.append([m["cedula_raw"], m["nombre"], m["email"], m["celular"], m["anio"]])
        wb.save(RUTA_XLSX_OUT)
        log(f"xlsx de {len(no_enc)} mujeres NO encontradas → {RUTA_XLSX_OUT}")

    # 6) --aplicar: enlazar participant_id de los matches por correo/nombre (hoy sin enlace)
    if args.aplicar:
        metodos_ok = ("correo",) if args.solo_correo else ("correo", "nombre")
        nuevos_enlaces = [m for m in mujeres if m["metodo"] in metodos_ok and m["pid"] and m["cedula_digits"]]
        log(f"Enlazando participant_id de {len(nuevos_enlaces)} matches ({'+'.join(metodos_ok)}) "
            "en postulantes_mr (solo si participant_id está NULL)...")
        ok = 0
        for m in nuevos_enlaces:
            try:
                supa._req("PATCH",
                          f"/postulantes_mr?cedula=eq.{m['cedula_digits']}&participant_id=is.null",
                          {"participant_id": m["pid"]})
                ok += 1
            except Exception as e:
                log(f"  aviso cedula={m['cedula_digits']}: {e}")
        log(f"Enlazados: {ok} (nota: si el filtro no matcheó, la fila ya tenía participant_id o "
            "la cédula difiere de formato — no destructivo)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
