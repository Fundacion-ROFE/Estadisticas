#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capturar_rebotes.py — Captura de rebotes (bounces) de Jóvenes creaTIvos (calcado de
scripts/mujeres-rofe-correos/capturar_rebotes.py, cuenta y Sheet propios).

  1. Lee por IMAP el buzón `soporte@tocaunavida.org` (misma app-password de `.env.local`,
     SMTP_USER_JC/SMTP_PASSWORD_JC — Gmail admite IMAP con app-password).
  2. Busca los DSN de `mailer-daemon` desde una fecha, clasifica hard (5.x, permanente) /
     soft (4.x, temporal).
  3. Upsert en Supabase `email_bounces` (MISMA tabla que usa MR — PK por email, no distingue
     programa; correcto porque las direcciones de JC y MR no se solapan).
  4. Vuelca la foto completa a la pestaña `Rebotes` del Sheet "RebotesJC" (compartido con la
     Service Account de Q10 el 2026-07-22).
  5. Marcador `alertas_datos` con id `correos_jc_desactualizados` (separado del de MR para no
     mezclar los conteos).

⚠ Nota (2026-07-22): `soporte@tocaunavida.org` es un buzón de soporte compartido — si además
recibe otro tráfico de mailer-daemon no relacionado con campañas de JC, este script lo capturaría
igual (solo filtra por remitente mailer-daemon + fecha, no por campaña). Revisar el reporte en
`tools/jovenes-creativos-correos/data/rebotes_jc_*.csv` antes de confiar ciegamente en los totales
hasta que haya un historial de campañas reales.

⚠ PRIVACIDAD: las direcciones rebotadas (PII) van SOLO a Supabase y a un reporte en `tools/`
(gitignoreado). A consola solo van conteos. Nunca a GitHub.

Uso:
    python capturar_rebotes.py                     # últimos 30 días, escribe
    python capturar_rebotes.py --desde 2026-07-14  # desde una fecha
    python capturar_rebotes.py --dry-run           # solo reporta, no escribe
Consola (parseable):
    RESUMEN: dsn=N rebotes=R hard=H soft=S insertados=I estado=exito
"""
import argparse
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
TOOLS_DATA = os.path.join(PROYECTO_ROOT, "tools", "jovenes-creativos-correos", "data")

IMAP_HOST = "imap.gmail.com"
USER_AGENT = "panel-datos-etl/1.0"

# Mismo Service Account de Q10, compartido como Editor con "RebotesJC" el 2026-07-22.
CRED_SA = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion", "credenciales_service_account.json")
SHEET_ID = "1ACj0Dp-xv-f-NByfbyZLW8_h4ba1Bmb7aX7OUT6FKcI"
SHEET_TAB = "Rebotes"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
EMAIL_RE = re.compile(r"[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+")
ENH_STATUS_RE = re.compile(r"\b([245]\.\d{1,3}\.\d{1,3})\b")
SMTP_LINE_RE = re.compile(r"\b[245]\d\d[\s-]+[245]\.\d{1,3}\.\d")


def log(msg):
    print(f"[capturar-rebotes-jc] {msg}", flush=True)


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


# ── Parseo de un mensaje DSN (idéntico al de MR) ────────────────────────────────
def parsear_dsn(msg):
    resultados = []
    for parte in msg.walk():
        if parte.get_content_type() != "message/delivery-status":
            continue
        payload = parte.get_payload()
        if not isinstance(payload, list):
            continue
        for sub in payload:
            rcpt = sub.get("Final-Recipient") or ""
            em = EMAIL_RE.search(rcpt)
            if not em:
                continue
            status = (sub.get("Status") or "").strip()
            diag = " ".join((sub.get("Diagnostic-Code") or "").split())[:200]
            resultados.append((em.group(0).lower(), status, diag))
    if resultados:
        return resultados

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
    return "hard"


def leer_rebotes(usuario, password, desde):
    """Retorna dict email_lower -> {tipo, codigo, fecha, motivo}."""
    M = imaplib.IMAP4_SSL(IMAP_HOST)
    M.login(usuario, password)
    M.select("INBOX", readonly=True)

    desde_imap = desde.strftime("%d-%b-%Y")
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
            if prev is None or (tipo == "hard" and prev["tipo"] == "soft") or fecha_iso > prev["fecha"]:
                acumulado[em] = {"tipo": tipo, "codigo": status or "", "fecha": fecha_iso,
                                 "motivo": diag or "sin diagnostico"}
    try:
        M.close()
    except Exception:
        pass
    M.logout()
    return acumulado


def upsert_bounces(filas):
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("AVISO: sin credenciales Supabase — no se escribió email_bounces")
        return 0
    cuerpo = [{"email": em, "programa": "jc", **datos} for em, datos in filas.items()]
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
    ruta = os.path.join(TOOLS_DATA, f"rebotes_jc_{datetime.now():%Y%m%d}.csv")
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        f.write("email,tipo,codigo,fecha,motivo\n")
        for em, d in sorted(filas.items()):
            motivo = d["motivo"].replace('"', "'")
            f.write(f'{em},{d["tipo"]},{d["codigo"]},{d["fecha"]},"{motivo}"\n')
    return ruta


# ── Enriquecimiento con nombre (solo Supabase participants — JC no tiene un Excel
#    "General" equivalente al de MR) + volcado a Google Sheet ──────────────────
def get_bounces(url, key):
    """Rebotes de JC ÚNICAMENTE (programa=jc) — email_bounces es compartida con MR
    (misma tabla, PK por email) desde que ambos programas empezaron a capturar rebotes
    el 2026-07-22; sin este filtro el Sheet/alerta de JC mostraría también los de MR."""
    req = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/email_bounces?programa=eq.jc"
        "&select=email,tipo,codigo,fecha,motivo&order=tipo.asc,email.asc",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read() or b"[]")


def nombres_desde_supabase(url, key, emails):
    """email_lower → nombre, desde participants (programa=jc)."""
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
    """Marcador separado del de MR (id distinto) para no mezclar conteos por programa."""
    fila = {
        "id": "correos_jc_desactualizados",
        "activa": hard_total > 0,
        "cantidad": hard_total,
        "detalle": f"{hard_total} correos con rebote permanente (hard) + {soft_total} temporales "
                   f"(soft, buzón lleno) en email_bounces. Ver pestaña Rebotes del Sheet RebotesJC.",
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
    """Vuelca la foto completa de email_bounces (enriquecida con nombre) a RebotesJC!Rebotes."""
    if not os.path.isfile(CRED_SA):
        log(f"AVISO: no se encontró {CRED_SA} — no se escribió el Sheet")
        return 0
    todos = get_bounces(url, key)
    if not todos:
        log("Sin rebotes en Supabase — no se escribe el Sheet")
        return 0

    creds = Credentials.from_service_account_file(CRED_SA, scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_key(SHEET_ID)

    nombres = nombres_desde_supabase(url, key, [b["email"] for b in todos])

    todos.sort(key=lambda b: (0 if b.get("tipo") == "hard" else 1,
                              (nombres.get(b["email"], "") or "zzz").lower()))
    filas = [["Nombre", "Correo", "Tipo", "Codigo", "Fecha", "Motivo"]]
    for b in todos:
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
    ap = argparse.ArgumentParser(description="Captura de rebotes JC (IMAP) → email_bounces")
    ap.add_argument("--desde", help="Fecha inicio YYYY-MM-DD (default: hace 30 días)")
    ap.add_argument("--dry-run", action="store_true", help="No escribe en Supabase ni Sheet")
    ap.add_argument("--no-sheet", action="store_true", help="No actualiza la pestaña Rebotes")
    args = ap.parse_args()

    cargar_env_local()
    usuario = os.environ.get("SMTP_USER_JC", "")
    password = os.environ.get("SMTP_PASSWORD_JC", "")
    if not usuario or not password:
        log("ERROR: faltan SMTP_USER_JC / SMTP_PASSWORD_JC (.env.local) para IMAP")
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
