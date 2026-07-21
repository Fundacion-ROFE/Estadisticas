#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capturar_rebotes.py — Captura de rebotes (bounces) → suppression list (Tarea 7).

Cierra el hueco detectado por Samuel (2026-07-15): `enviar_campana.py` solo registra la
ACEPTACIÓN SMTP, no la entrega. Los rebotes ASÍNCRONOS (buzón inválido/lleno) vuelven como
DSN (Delivery Status Notification) al buzón remitente `mujeres.rofe@tocaunavida.org` y nadie
los leía. Este script:

  1. Lee el buzón remitente por IMAP (misma app-password de `.env.local`, sin credenciales
     nuevas — Gmail admite IMAP con app-password).
  2. Busca los DSN de `mailer-daemon` (Mail Delivery Subsystem) desde una fecha.
  3. Parsea la(s) dirección(es) que rebotaron y su `Status` SMTP → clasifica:
       - `5.x` = HARD (permanente: dirección no existe / rechazada)  → a suppression list
       - `4.x` = SOFT (temporal: buzón lleno / greylisting)          → se registra, NO suprime
  4. Upsert en Supabase `email_bounces` (una fila por dirección, keep tipo peor + último visto).
  5. Vuelca la foto completa (enriquecida con NOMBRE, cruzando la lista de campaña + participants)
     a la pestaña `Rebotes` de la BD-Mujeres ROFÉ 2026, para que el equipo reconozca a quién
     hay que actualizarle el correo. La pestaña `General` resalta en ROJO (formato condicional
     sobre la columna AUXILIAR) las filas cuyo correo está en Rebotes — se recalcula solo.
  6. Actualiza el marcador `public.alertas_datos` (id='correos_mr_desactualizados', sin PII,
     lectura pública) con el total ACUMULADO de hard bounces — fácilmente identificable desde
     cualquier consulta/dashboard sin tener que escanear email_bounces completa.

La próxima corrida de `extraer_lista_mr_ultimos3anios.py` excluye los HARD automáticamente.

⚠ PRIVACIDAD: las direcciones rebotadas (PII) van SOLO a Supabase y a un reporte en `tools/`
(gitignoreado). A consola solo van conteos. Nunca a GitHub.

Credenciales (de `.env.local` raíz): `SMTP_USER`/`SMTP_PASSWORD` (IMAP) +
`SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` (escritura).

Uso:
    python capturar_rebotes.py                     # últimos 30 días, escribe
    python capturar_rebotes.py --desde 2026-07-14  # desde una fecha
    python capturar_rebotes.py --dry-run           # solo reporta, no escribe
Consola (parseable por n8n):
    RESUMEN: dsn=N rebotes=R hard=H soft=S insertados=I estado=exito
"""
import argparse
import csv
import email
import imaplib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

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
TOOLS_DATA = os.path.join(PROYECTO_ROOT, "tools", "mujeres-rofe-correos", "data")

IMAP_HOST = "imap.gmail.com"
USER_AGENT = "panel-datos-etl/1.0"

# Google Sheet donde se listan los rebotes (pestaña Rebotes) para el equipo MR — mismo
# Service Account de Q10. Es la BD-Mujeres ROFÉ 2026 (ya compartida como editor con la SA).
CRED_SA = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion", "credenciales_service_account.json")
SHEET_ID = "1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8"
SHEET_TAB = "Rebotes"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
RUTA_LISTA = os.path.join(TOOLS_DATA, "lista_mr_ultimos_3_anios.csv")  # email → nombre (campaña)
EMAIL_RE = re.compile(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+")
ENH_STATUS_RE = re.compile(r"\b([245]\.\d{1,3}\.\d{1,3})\b")       # status extendido, ej. 5.1.1
SMTP_LINE_RE = re.compile(r"\b[245]\d\d[\s-]+[245]\.\d{1,3}\.\d")  # línea "550 5.1.1 ..."


def log(msg):
    print(f"[capturar-rebotes] {msg}", flush=True)


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


# ── Parseo de un mensaje DSN ─────────────────────────────────────────────────────
def parsear_dsn(msg):
    """
    Retorna lista de (email_lower, status, diagnostico) por cada destinatario que rebotó.
    Prioriza la parte estructurada message/delivery-status (bloques Message con headers
    Final-Recipient/Status/Diagnostic-Code); si no da nada, cae al texto human-readable.
    """
    resultados = []

    # 1. Parte estructurada: message/delivery-status es multiparte (lista de Message).
    for parte in msg.walk():
        if parte.get_content_type() != "message/delivery-status":
            continue
        payload = parte.get_payload()
        if not isinstance(payload, list):
            continue
        for sub in payload:  # cada sub es un bloque de headers
            rcpt = sub.get("Final-Recipient") or ""
            em = EMAIL_RE.search(rcpt)
            if not em:
                continue
            status = (sub.get("Status") or "").strip()
            diag = " ".join((sub.get("Diagnostic-Code") or "").split())[:200]
            resultados.append((em.group(0).lower(), status, diag))
    if resultados:
        return resultados

    # 2. Fallback: texto plano ("...no se ha entregado a EMAIL... 550 5.1.1 ...").
    for parte in msg.walk():
        if parte.get_content_type() != "text/plain":
            continue
        try:
            texto = parte.get_payload(decode=True).decode(errors="replace")
        except Exception:
            continue
        if "@" not in texto:
            continue
        m_dest = re.search(r"(?:no se ha entregado a|wasn't delivered to)\s+(\S+@\S+)", texto)
        em = EMAIL_RE.search(m_dest.group(1)) if m_dest else EMAIL_RE.search(texto)
        if not em:
            continue
        m_st = ENH_STATUS_RE.search(texto)
        diag_line = next((ln.strip()[:180] for ln in texto.splitlines() if SMTP_LINE_RE.search(ln)), "")
        resultados.append((em.group(0).lower(), m_st.group(1) if m_st else "", diag_line))
        break
    return resultados


def clasificar(status):
    if status.startswith("5"):
        return "hard"
    if status.startswith("4"):
        return "soft"
    return "hard"  # sin status legible en un DSN → tratar como permanente (conservador)


# ── Lectura IMAP ─────────────────────────────────────────────────────────────────
def leer_rebotes(usuario, password, desde):
    """Retorna dict email_lower -> {tipo, codigo, fecha, motivo}. Keep: hard gana; fecha más reciente."""
    M = imaplib.IMAP4_SSL(IMAP_HOST)
    M.login(usuario, password)
    M.select("INBOX", readonly=True)

    desde_imap = desde.strftime("%d-%b-%Y")
    # DSN vienen de mailer-daemon (Gmail) — buscamos por remitente + fecha.
    typ, data = M.search(None, f'(SINCE {desde_imap} FROM "mailer-daemon")')
    ids = data[0].split() if data and data[0] else []
    log(f"{len(ids)} mensajes de mailer-daemon desde {desde_imap}")

    acumulado = {}
    for num in ids:
        typ, md = M.fetch(num, "(RFC822)")
        if typ != "OK" or not md or not md[0]:
            continue
        msg = email.message_from_bytes(md[0][1])
        try:
            fecha = parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else datetime.now()
            fecha_iso = fecha.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")
        except Exception:
            fecha_iso = datetime.now().isoformat(timespec="seconds")
        for em, status, diag in parsear_dsn(msg):
            tipo = clasificar(status)
            prev = acumulado.get(em)
            # hard gana sobre soft; a igualdad, la fecha más reciente
            if prev is None or (tipo == "hard" and prev["tipo"] == "soft") or fecha_iso > prev["fecha"]:
                acumulado[em] = {"tipo": tipo, "codigo": status or "", "fecha": fecha_iso,
                                 "motivo": diag or "sin diagnostico"}
    try:
        M.close()
    except Exception:
        pass
    M.logout()
    return acumulado


# ── Escritura Supabase ───────────────────────────────────────────────────────────
def upsert_bounces(filas):
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("AVISO: sin credenciales Supabase — no se escribió email_bounces")
        return 0
    cuerpo = [{"email": em, **datos} for em, datos in filas.items()]
    req = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/email_bounces?on_conflict=email",
        method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json", "User-Agent": USER_AGENT,
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps(cuerpo).encode())
    try:
        urllib.request.urlopen(req, timeout=60)
        return len(cuerpo)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from None


def guardar_reporte(filas):
    os.makedirs(TOOLS_DATA, exist_ok=True)
    ruta = os.path.join(TOOLS_DATA, f"rebotes_{datetime.now():%Y%m%d}.csv")
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        f.write("email,tipo,codigo,fecha,motivo\n")
        for em, d in sorted(filas.items()):
            motivo = d["motivo"].replace('"', "'")
            f.write(f'{em},{d["tipo"]},{d["codigo"]},{d["fecha"]},"{motivo}"\n')
    return ruta


# ── Enriquecimiento con nombre + volcado a Google Sheet ──────────────────────────
def get_bounces(url, key):
    """Lee TODOS los rebotes de Supabase (foto completa para el Sheet)."""
    req = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/email_bounces?select=email,tipo,codigo,fecha,motivo"
        "&order=tipo.asc,email.asc",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read() or b"[]")


def nombres_desde_lista():
    """email_lower → nombre, desde la lista de campaña (tools/, si existe).
    OJO: esta lista YA excluye los hard bounces, así que no cubre a los rebotados —
    es solo un complemento; la fuente principal de nombres es la pestaña General."""
    mapa = {}
    if not os.path.isfile(RUTA_LISTA):
        return mapa
    with open(RUTA_LISTA, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            correo = (row.get("correo") or "").strip().lower()
            if correo:
                mapa[correo] = (row.get("nombre") or "").strip()
    return mapa


def nombres_desde_general(sh):
    """email_lower → nombre, desde la pestaña General de la BD-Mujeres ROFÉ (roster
    completo, incluye a los rebotados). Mapeo de columnas igual que extraer_excel:
    nombre=col D (idx 3), correo=col E (idx 4) o H (idx 7)."""
    out = {}
    try:
        ws = sh.worksheet("General")
    except gspread.WorksheetNotFound:
        return out
    for row in ws.get_all_values()[1:]:
        nombre = row[3].strip() if len(row) > 3 else ""
        correo = ""
        if len(row) > 4 and (row[4] or "").strip():
            correo = row[4].strip().lower()
        elif len(row) > 7 and (row[7] or "").strip():
            correo = row[7].strip().lower()
        if correo:
            out[correo] = nombre
    return out


def nombres_desde_supabase(url, key, emails):
    """email_lower → nombre, desde participants (para los que la lista no cubre)."""
    out = {}
    if not emails:
        return out
    base = url.rstrip("/") + "/rest/v1/participants"
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT}
    lista = list(emails)
    for i in range(0, len(lista), 100):
        grp = lista[i:i + 100]
        val = "(" + ",".join('"%s"' % e for e in grp) + ")"
        q = base + "?select=email,nombre&email=in." + urllib.parse.quote(val)
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers=headers), timeout=60) as r:
                for reg in json.loads(r.read() or b"[]"):
                    em = (reg.get("email") or "").strip().lower()
                    if em and reg.get("nombre"):
                        out[em] = reg["nombre"]
        except Exception:
            pass
    return out


def actualizar_alerta(url, key, hard_total, soft_total):
    """Upsert del marcador public.alertas_datos — fácilmente identificable desde cualquier
    consulta/dashboard: 'hay correos que pueden estar desactualizados'. Sin PII (solo conteos)."""
    fila = {
        "id": "correos_mr_desactualizados",
        "activa": hard_total > 0,
        "cantidad": hard_total,
        "detalle": f"{hard_total} correos con rebote permanente (hard) + {soft_total} temporales "
                   f"(soft, buzón lleno) en email_bounces. Ver pestaña Rebotes de BD-Mujeres ROFÉ.",
        "actualizado_en": datetime.now().isoformat(timespec="seconds"),
    }
    req = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/alertas_datos?on_conflict=id",
        method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT,
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps(fila).encode())
    urllib.request.urlopen(req, timeout=30)


def escribir_sheet(url, key):
    """Vuelca la foto completa de email_bounces (enriquecida con nombre) a la pestaña Rebotes."""
    if not os.path.isfile(CRED_SA):
        log(f"AVISO: no se encontró {CRED_SA} — no se escribió el Sheet")
        return 0
    bounces = get_bounces(url, key)
    if not bounces:
        log("Sin rebotes en Supabase — no se escribe el Sheet")
        return 0

    creds = Credentials.from_service_account_file(CRED_SA, scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_key(SHEET_ID)

    # Nombres: General (roster completo MR, gana) → lista campaña → participants (Supabase).
    nombres = nombres_desde_lista()
    nombres.update({k: v for k, v in nombres_desde_general(sh).items() if v})
    faltan = [b["email"] for b in bounces if not nombres.get(b["email"])]
    nombres.update(nombres_desde_supabase(url, key, faltan))

    # hard primero, luego por nombre
    bounces.sort(key=lambda b: (0 if b.get("tipo") == "hard" else 1,
                                (nombres.get(b["email"], "") or "zzz").lower()))
    filas = [["Nombre", "Correo", "Tipo", "Codigo", "Fecha", "Motivo"]]
    for b in bounces:
        fecha = (b.get("fecha") or "")[:10]
        filas.append([nombres.get(b["email"], ""), b["email"], b.get("tipo", ""),
                      b.get("codigo", ""), fecha, b.get("motivo", "")])

    try:
        ws = sh.worksheet(SHEET_TAB)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SHEET_TAB, rows=max(100, len(filas) + 10), cols=6)
        log(f"Pestaña '{SHEET_TAB}' creada")
    ws.clear()
    ws.update(filas, "A1", raw=True)
    con_nombre = sum(1 for fila in filas[1:] if fila[0])
    log(f"Sheet '{SHEET_TAB}': {len(filas) - 1} rebotes escritos ({con_nombre} con nombre)")
    return len(filas) - 1


def main():
    ap = argparse.ArgumentParser(description="Captura de rebotes (IMAP) → email_bounces")
    ap.add_argument("--desde", help="Fecha inicio YYYY-MM-DD (default: hace 30 días)")
    ap.add_argument("--dry-run", action="store_true", help="No escribe en Supabase ni Sheet")
    ap.add_argument("--no-sheet", action="store_true", help="No actualiza la pestaña Rebotes")
    args = ap.parse_args()

    cargar_env_local()
    usuario = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    if not usuario or not password:
        log("ERROR: faltan SMTP_USER / SMTP_PASSWORD (.env.local) para IMAP")
        print("RESUMEN: dsn=0 rebotes=0 hard=0 soft=0 insertados=0 estado=error_credenciales")
        return 1

    desde = (datetime.strptime(args.desde, "%Y-%m-%d") if args.desde
             else datetime.now() - timedelta(days=30))

    try:
        filas = leer_rebotes(usuario, password, desde)
    except imaplib.IMAP4.error as e:
        log(f"ERROR IMAP: {e}")
        print("RESUMEN: dsn=0 rebotes=0 hard=0 soft=0 insertados=0 estado=error_imap")
        return 1

    hard = sum(1 for d in filas.values() if d["tipo"] == "hard")
    soft = len(filas) - hard
    log(f"{len(filas)} direcciones rebotadas ({hard} hard, {soft} soft)")

    insertados = en_sheet = 0
    if filas and not args.dry_run:
        ruta = guardar_reporte(filas)
        log(f"Reporte (PII): {ruta}")
        insertados = upsert_bounces(filas)
        log(f"Upsert email_bounces: {insertados}")
    elif args.dry_run:
        log("dry-run: no se escribió nada")

    # Volcado al Google Sheet (foto completa de email_bounces, enriquecida con nombre) +
    # marcador de alerta en Supabase (totales ACUMULADOS, no solo lo nuevo de esta corrida).
    if not args.dry_run:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if url and key:
            try:
                todos = get_bounces(url, key)
                hard_total = sum(1 for b in todos if b.get("tipo") == "hard")
                soft_total = len(todos) - hard_total
                actualizar_alerta(url, key, hard_total, soft_total)
                log(f"Alerta Supabase actualizada: {hard_total} hard acumulados (activa={hard_total > 0})")
            except Exception as e:
                log(f"AVISO: no se pudo actualizar alertas_datos ({e})")
            if not args.no_sheet:
                try:
                    en_sheet = escribir_sheet(url, key)
                except Exception as e:
                    log(f"AVISO: no se pudo escribir el Sheet ({e}) — Supabase quedó al día igual")

    print(f"RESUMEN: dsn={len(filas)} rebotes={len(filas)} hard={hard} soft={soft} "
          f"insertados={insertados} sheet={en_sheet} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
