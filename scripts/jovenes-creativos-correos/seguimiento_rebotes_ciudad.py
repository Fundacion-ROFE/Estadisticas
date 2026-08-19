#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seguimiento_rebotes_ciudad.py — DEMO: seguimiento semana a semana de rebotes JC por
ciudad, usando ÚNICAMENTE la cuenta madre `soporte@tocaunavida.org` (capturar_rebotes.py).

⚠ Alcance real (2026-08-19): esto NO mide "correos enviados" — hoy no existe ningún
registro de envíos exitosos de monitores (mandan por su cuenta, fuera de
enviar_campana.py). Lo único medible es el REBOTE (lo que sí sabemos que falló), vía
IMAP de la cuenta compartida. Este script cruza esos rebotes contra la ciudad de cada
persona (BD Seguimiento de Monitorias, pestaña `Seguimiento`, columna `Grupo`) y publica
un snapshot semanal — sirve como piloto antes de escalar a más cuentas (una por
monitor), que requiere credenciales que todavía no se tienen.

  1. Lee Supabase `email_bounces` (programa=jc) — email/tipo/veces_soft, un registro por
     email (la promoción soft→hard de capturar_rebotes.py ya evita el doble conteo).
  2. Lee la pestaña `Seguimiento` (Sheet vivo BD Seguimiento de Monitorias, mismo Sheet
     y Service Account que ya usa tools/exportar_sin_completar.py) → email → Grupo
     (código de ciudad) + total de emails registrados por ciudad (denominador).
  3. Cruza por email (no hay cédula en email_bounces) → agrega hard/soft/total por
     ciudad. Sin match → fila "SIN UBICACIÓN" (sin denominador, no es una ciudad real).
  4. Escribe/actualiza la pestaña `RebotesCiudad` del Sheet "RebotesJC" (mismo Sheet de
     capturar_rebotes.py): guarda snapshot de la semana ISO en curso, conserva semanas
     anteriores congeladas (mismo patrón "Historico" de exportar_sin_completar.py).

⚠ PRIVACIDAD: sin PII — la salida es solo conteos agregados por ciudad/semana.

Uso:
    python seguimiento_rebotes_ciudad.py             # escribe
    python seguimiento_rebotes_ciudad.py --dry-run    # solo reporta en consola
Consola (parseable):
    RESUMEN: ciudades=N hard=H soft=S total=T sin_ubicacion=U estado=exito
"""
import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import gspread
from google.oauth2.service_account import Credentials

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV = os.path.join(PROYECTO_ROOT, ".env.local")
CRED_SA = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion", "credenciales_service_account.json")
USER_AGENT = "panel-datos-etl/1.0"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Mismo Sheet que capturar_rebotes.py (ya compartido con la Service Account).
REBOTES_SHEET_ID = "1ACj0Dp-xv-f-NByfbyZLW8_h4ba1Bmb7aX7OUT6FKcI"
DESTINO_TAB = "RebotesCiudad"

# BD Seguimiento de Monitorias — mismo Sheet/pestaña que tools/exportar_sin_completar.py.
BD_SHEET_ID = "1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8"
BD_TAB = "Seguimiento"

GRUPO_LABEL = {
    "BOG": "Bogotá", "BAQ": "Barranquilla", "CTG": "Cartagena", "MED": "Medellín",
    "CAL": "Cali", "GYL": "Guayaquil", "PAN": "Panamá", "QTO": "Quito", "UY": "Uruguay",
}
SIN_UBICACION = "SIN UBICACIÓN"

HEADERS = ["Semana", "Rango", "Ciudad", "TotalSeguimiento", "Hard", "Soft", "TotalRebotes", "PctRebote"]

MESES_ES = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
            7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre",
            12: "diciembre"}


def log(msg):
    print(f"[rebotes-ciudad-jc] {msg}", flush=True)


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


def semana_actual(fecha=None):
    """(semana_iso 'AAAA-Www', rango legible) — mismo helper que exportar_sin_completar.py."""
    fecha = fecha or datetime.now()
    iso_year, iso_week, _ = fecha.isocalendar()
    lunes = fecha - timedelta(days=fecha.weekday())
    viernes = lunes + timedelta(days=4)
    if lunes.month == viernes.month:
        rango = f"{lunes.day}-{viernes.day} {MESES_ES[viernes.month]}"
    else:
        rango = f"{lunes.day} {MESES_ES[lunes.month]} - {viernes.day} {MESES_ES[viernes.month]}"
    return f"{iso_year}-W{iso_week:02d}", rango


# ── 1. Supabase: rebotes vigentes de JC ─────────────────────────────────────────
def leer_bounces(url, key):
    req = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/email_bounces?programa=eq.jc"
        "&select=email,tipo,veces_soft",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read() or b"[]")


# ── 2. BD Seguimiento: email → ciudad + total por ciudad ────────────────────────
def _col(headers, *needles):
    for i, h in enumerate(headers):
        if any(n in h for n in needles):
            return i
    return None


def leer_ciudad_por_email(gc):
    """Retorna (por_email {email: grupo}, total_por_grupo {grupo: N}) desde la pestaña
    Seguimiento del Sheet vivo (mismo Service Account que ya la lee en otros scripts)."""
    log(f"Leyendo BD Seguimiento (Sheet vivo, id {BD_SHEET_ID})...")
    sh = gc.open_by_key(BD_SHEET_ID)
    filas = sh.worksheet(BD_TAB).get_all_values()
    headers = [h.strip().lower() for h in filas[0]]
    i_grupo, i_email = _col(headers, "grupo"), _col(headers, "e-mail", "email")
    if i_grupo is None or i_email is None:
        raise ValueError(f"Seguimiento sin columnas Grupo/E-mail. Headers: {headers[:15]}")

    por_email, total_por_grupo = {}, {}
    for f in filas[1:]:
        email = (f[i_email].strip().lower() if i_email < len(f) else "")
        grupo = (f[i_grupo].strip().upper() if i_grupo < len(f) else "")
        if not email or not grupo:
            continue
        if email not in por_email:
            por_email[email] = grupo
            total_por_grupo[grupo] = total_por_grupo.get(grupo, 0) + 1
    log(f"  {len(por_email)} emails con ciudad en Seguimiento, {len(total_por_grupo)} ciudades")
    return por_email, total_por_grupo


# ── 3. Cruce + agregado por ciudad ───────────────────────────────────────────────
def agregar_por_ciudad(bounces, por_email, total_por_grupo):
    conteo = {}  # grupo -> {"hard": n, "soft": n}
    sin_ubicacion = {"hard": 0, "soft": 0}
    for b in bounces:
        email = (b.get("email") or "").strip().lower()
        tipo = b.get("tipo") or "hard"
        grupo = por_email.get(email)
        destino = conteo.setdefault(grupo, {"hard": 0, "soft": 0}) if grupo else sin_ubicacion
        destino[tipo] = destino.get(tipo, 0) + 1

    filas = []
    for grupo, c in conteo.items():
        total_seg = total_por_grupo.get(grupo, 0)
        total_reb = c["hard"] + c["soft"]
        pct = round(total_reb / total_seg * 100, 1) if total_seg else ""
        filas.append({"ciudad": f"{grupo} — {GRUPO_LABEL.get(grupo, grupo)}",
                      "total_seguimiento": total_seg, "hard": c["hard"], "soft": c["soft"],
                      "total": total_reb, "pct": pct})
    if sin_ubicacion["hard"] or sin_ubicacion["soft"]:
        t = sin_ubicacion["hard"] + sin_ubicacion["soft"]
        filas.append({"ciudad": SIN_UBICACION, "total_seguimiento": "",
                      "hard": sin_ubicacion["hard"], "soft": sin_ubicacion["soft"],
                      "total": t, "pct": ""})
    filas.sort(key=lambda f: (f["ciudad"] == SIN_UBICACION, -f["total"]))
    return filas


# ── 4. Escritura semanal (mismo patrón "Historico" de exportar_sin_completar.py) ──
def leer_historico(gc):
    sh = gc.open_by_key(REBOTES_SHEET_ID)
    try:
        ws = sh.worksheet(DESTINO_TAB)
    except gspread.WorksheetNotFound:
        return []
    vals = ws.get_all_values()
    if len(vals) < 2:
        return []
    idx = {h.strip(): i for i, h in enumerate(vals[0])}
    if not all(k in idx for k in HEADERS):
        return []
    filas = []
    for row in vals[1:]:
        if not any(row):
            continue
        filas.append({h: (row[idx[h]] if idx[h] < len(row) else "") for h in HEADERS})
    return filas


def escribir_historico(gc, previo, filas_actuales, semana_iso, rango):
    otras = [f for f in previo if f["Semana"] != semana_iso]
    nuevas = [{"Semana": semana_iso, "Rango": rango, "Ciudad": f["ciudad"],
               "TotalSeguimiento": f["total_seguimiento"], "Hard": f["hard"],
               "Soft": f["soft"], "TotalRebotes": f["total"], "PctRebote": f["pct"]}
              for f in filas_actuales]
    todas = otras + nuevas
    todas.sort(key=lambda f: (f["Semana"], f["Ciudad"] == SIN_UBICACION, f["Ciudad"]))

    sh = gc.open_by_key(REBOTES_SHEET_ID)
    try:
        old = sh.worksheet(DESTINO_TAB)
    except gspread.WorksheetNotFound:
        old = None
    ws = sh.add_worksheet(f"{DESTINO_TAB}_tmp", rows=len(todas) + 10, cols=len(HEADERS) + 2)
    if old is not None:
        sh.del_worksheet(old)
    ws.update_title(DESTINO_TAB)

    grid = [HEADERS] + [[f[h] for h in HEADERS] for f in todas]
    log(f"Escribiendo {len(todas)} filas ({len(otras)} previas + {len(nuevas)} de {semana_iso}) "
        f"en '{DESTINO_TAB}'...")
    ws.update(grid, "A1", raw=True)
    ws.freeze(rows=1)
    return len(todas)


def main():
    ap = argparse.ArgumentParser(description="Rebotes JC por ciudad (demo, solo cuenta soporte@)")
    ap.add_argument("--dry-run", action="store_true", help="Solo reporta, no escribe el Sheet")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (.env.local)")
        print("RESUMEN: ciudades=0 hard=0 soft=0 total=0 sin_ubicacion=0 estado=error_credenciales")
        return 1
    if not os.path.isfile(CRED_SA):
        log(f"ERROR: no se encontró {CRED_SA}")
        print("RESUMEN: ciudades=0 hard=0 soft=0 total=0 sin_ubicacion=0 estado=error_credenciales")
        return 1

    try:
        bounces = leer_bounces(url, key)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        log(f"ERROR Supabase: {e}")
        print("RESUMEN: ciudades=0 hard=0 soft=0 total=0 sin_ubicacion=0 estado=error_supabase")
        return 1
    log(f"{len(bounces)} rebotes vigentes (email_bounces, programa=jc)")

    creds = Credentials.from_service_account_file(CRED_SA, scopes=SCOPES)
    gc = gspread.authorize(creds)
    por_email, total_por_grupo = leer_ciudad_por_email(gc)

    filas = agregar_por_ciudad(bounces, por_email, total_por_grupo)
    hard_total = sum(f["hard"] for f in filas)
    soft_total = sum(f["soft"] for f in filas)
    sin_ubic = next((f["total"] for f in filas if f["ciudad"] == SIN_UBICACION), 0)

    semana_iso, rango = semana_actual()
    log(f"Semana {semana_iso} ({rango}): {len(filas)} filas, {hard_total} hard, {soft_total} soft, "
        f"{sin_ubic} sin ubicación")
    for f in filas:
        log(f"  {f['ciudad']:<28} total_seg={f['total_seguimiento']!s:<6} hard={f['hard']:<4} "
            f"soft={f['soft']:<4} pct={f['pct']}")

    if not args.dry_run:
        previo = leer_historico(gc)
        n = escribir_historico(gc, previo, filas, semana_iso, rango)
        log(f"OK — {n} filas totales en '{DESTINO_TAB}' (histórico acumulado)")
    else:
        log("dry-run: no se escribió el Sheet")

    print(f"RESUMEN: ciudades={len(filas)} hard={hard_total} soft={soft_total} "
          f"total={hard_total + soft_total} sin_ubicacion={sin_ubic} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
