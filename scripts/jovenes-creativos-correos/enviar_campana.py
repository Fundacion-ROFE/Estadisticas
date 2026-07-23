#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Envío de correos parametrizados para Jóvenes creaTIvos (calcado de
scripts/mujeres-rofe-correos/enviar_campana.py, cuenta y banner propios).

USO:
  python enviar_campana.py --preview <campana.json>
  python enviar_campana.py --piloto <campana.json> <correo_piloto>
  python enviar_campana.py --enviar <campana.json>

SEGURIDAD:
  - Contraseña SIEMPRE en variable de entorno SMTP_PASSWORD_JC (no en código)
  - Validar config antes de enviar
  - Registro de todos los envíos para reanudar
"""
import argparse
import csv
import json
import os
import smtplib
import ssl
import sys
import time
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path
from string import Template

# ============================================================================
BASE = Path(__file__).parent
PROYECTO_ROOT = BASE.parent.parent  # admin-usable/
# PII (listas con nombre+correo, registros de envío) NUNCA en scripts/ (git) —
# siempre en tools/ (gitignoreado). Ver CLAUDE.md convención de privacidad.
TOOLS_DATA = PROYECTO_ROOT / "tools" / "jovenes-creativos-correos" / "data"
TOOLS_DATA.mkdir(parents=True, exist_ok=True)


def cargar_env_local():
    """Carga .env.local (raíz del repo) al entorno SIN sobreescribir lo ya definido."""
    env = PROYECTO_ROOT / ".env.local"
    if not env.is_file():
        return
    for linea in env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


cargar_env_local()  # debe correr antes de leer os.environ en CONFIG_SMTP

CONFIG_SMTP = {
    "SMTP_HOST": os.environ.get("SMTP_HOST_JC", "smtp.gmail.com"),
    "SMTP_PORT": 587,
    "SMTP_USER": os.environ.get("SMTP_USER_JC", "soporte@tocaunavida.org"),
    "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD_JC"),  # ← OBLIGATORIO EN VARIABLE
    "FROM_NAME": "Equipo Jóvenes creaTIvos",
    "REPLY_TO": os.environ.get("SMTP_REPLY_TO_JC", "soporte@tocaunavida.org"),
    # Imagen inline (JC no tiene imagen de firma/footer todavía — solo banner)
    "IMG_BANNER": BASE / "img" / "header.jpg",
    # Plantilla base
    "PLANTILLA_TEMPLATE": BASE / "templates" / "email_v2_template_jc.html",
}

# ============================================================================
def registrar_campana_supabase(campana_id, enviados, fallidos, programa):
    """Inserta UNA fila resumen (agregada, SIN correos) en Supabase campanas_enviadas.
    Nunca hace fallar el envío: si Supabase no está disponible, solo avisa."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("[AVISO] Sin credenciales Supabase — no se registró en campanas_enviadas")
        return
    fila = {"campana": campana_id, "enviados": enviados,
            "fallidos": fallidos, "programa": programa}
    req = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/campanas_enviadas",
        method="POST",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "panel-datos-etl/1.0",
            "Prefer": "return=minimal",
        },
        data=json.dumps(fila).encode(),
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        print(f"[OK] Registrado en campanas_enviadas: {campana_id} "
              f"(enviados={enviados}, fallidos={fallidos}, programa={programa})")
    except urllib.error.HTTPError as e:
        print(f"[AVISO] No se pudo registrar en campanas_enviadas: "
              f"HTTP {e.code} {e.read().decode(errors='replace')[:200]}")
    except Exception as e:
        print(f"[AVISO] No se pudo registrar en campanas_enviadas: {e}")


def verificar_config_smtp():
    """Valida que todas las credenciales SMTP estén presentes."""
    if not CONFIG_SMTP["SMTP_PASSWORD"]:
        raise ValueError(
            "ERROR CRITICO: falta variable de entorno SMTP_PASSWORD_JC\n"
            "Agrégala a .env.local o define en PowerShell:\n"
            '  $env:SMTP_PASSWORD_JC = "xxxx xxxx xxxx xxxx"  # contraseña app 16 dígitos\n'
        )
    if not CONFIG_SMTP["SMTP_USER"]:
        raise ValueError("ERROR: falta SMTP_USER_JC en variables de entorno")
    print(f"[OK] Config SMTP validada: {CONFIG_SMTP['SMTP_USER']} en {CONFIG_SMTP['SMTP_HOST']}")

def verificar_imagenes():
    """Verifica que exista la imagen inline (solo banner — JC no tiene firma aún)."""
    if not CONFIG_SMTP["IMG_BANNER"].exists():
        raise FileNotFoundError(f"Falta imagen banner: {CONFIG_SMTP['IMG_BANNER']}")
    print(f"[OK] Imagen verificada ({CONFIG_SMTP['IMG_BANNER']})")

def cargar_plantilla():
    """Carga el template HTML."""
    if not CONFIG_SMTP["PLANTILLA_TEMPLATE"].exists():
        raise FileNotFoundError(f"Falta plantilla: {CONFIG_SMTP['PLANTILLA_TEMPLATE']}")
    return CONFIG_SMTP["PLANTILLA_TEMPLATE"].read_text(encoding="utf-8")

def cargar_campana(archivo_json):
    """Carga config de campaña desde JSON."""
    try:
        return json.loads(Path(archivo_json).read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Error cargando campaña JSON: {e}")

def cargar_lista(archivo_csv):
    """Carga lista de destinatarios (nombre, correo, [cohorte])."""
    destinatarios = []
    try:
        with open(archivo_csv, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("correo"):
                    destinatarios.append({
                        "nombre": row.get("nombre", "").strip(),
                        "correo": row.get("correo", "").strip().lower(),
                        "cohorte": row.get("cohorte", "").strip(),
                    })
    except Exception as e:
        raise ValueError(f"Error cargando CSV: {e}")
    if not destinatarios:
        raise ValueError(f"CSV vacío o sin columnas 'nombre', 'correo': {archivo_csv}")
    return destinatarios

def cargar_enviados(archivo_registro):
    """Devuelve set de correos con estado OK ya enviados."""
    if not Path(archivo_registro).exists():
        return set()
    enviados_ok = set()
    try:
        with open(archivo_registro, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("correo") and (row.get("estado") or "").upper() == "OK":
                    enviados_ok.add(row["correo"].strip().lower())
    except Exception:
        pass
    return enviados_ok

def registrar_envio(archivo_registro, correo, estado, detalle=""):
    """Registra intento de envío."""
    nuevo = not Path(archivo_registro).exists()
    with open(archivo_registro, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["correo", "campana", "fecha", "estado", "detalle"])
        w.writerow([correo, "", time.strftime("%Y-%m-%d %H:%M:%S"), estado, detalle[:200]])

def nuevos_cids():
    """Genera IDs únicos para la imagen inline."""
    return {"banner": make_msgid(domain="jovenescreativos")}

def construir_mensaje(dest_nombre, dest_correo, html, cids, vars_campana):
    """Construye EmailMessage con HTML + banner inline."""
    msg = EmailMessage()
    msg["Subject"] = vars_campana.get("ASUNTO", "Jóvenes creaTIvos")
    msg["From"] = formataddr((CONFIG_SMTP["FROM_NAME"], CONFIG_SMTP["SMTP_USER"]))
    msg["To"] = formataddr((dest_nombre or "", dest_correo))
    if CONFIG_SMTP["REPLY_TO"]:
        msg["Reply-To"] = CONFIG_SMTP["REPLY_TO"]

    # Cuerpo en texto plano (fallback)
    texto = (
        f"Hola {dest_nombre},\n\n"
        f"{vars_campana.get('PARRAFO_INTRO', 'Te estamos escribiendo...')}\n\n"
        f"Más info: {vars_campana.get('URL_CTA', 'https://tocaunavida.org')}\n\n"
        f"Equipo Jóvenes creaTIvos"
    )
    msg.set_content(texto)

    # HTML con variables interpoladas
    html_final = Template(html).safe_substitute(**vars_campana)
    html_final = html_final.replace("cid:banner", "cid:" + cids["banner"].strip("<>"))
    msg.add_alternative(html_final, subtype="html")

    payload = msg.get_payload()[1]  # parte HTML
    if ("cid:" + cids["banner"].strip("<>")) in html_final and CONFIG_SMTP["IMG_BANNER"].exists():
        ruta = CONFIG_SMTP["IMG_BANNER"]
        data = ruta.read_bytes()
        subtype = ruta.suffix.lstrip(".").lower() or "jpeg"
        if subtype == "jpg":
            subtype = "jpeg"
        payload.add_related(data, maintype="image", subtype=subtype, cid=cids["banner"])

    return msg

def conectar_smtp():
    """Abre conexión SMTP segura (TLS)."""
    ctx = ssl.create_default_context()
    if CONFIG_SMTP["SMTP_PORT"] == 465:
        s = smtplib.SMTP_SSL(CONFIG_SMTP["SMTP_HOST"], CONFIG_SMTP["SMTP_PORT"], context=ctx, timeout=60)
    else:
        s = smtplib.SMTP(CONFIG_SMTP["SMTP_HOST"], CONFIG_SMTP["SMTP_PORT"], timeout=60)
        s.ehlo()
        s.starttls(context=ctx)
        s.ehlo()
    s.login(CONFIG_SMTP["SMTP_USER"], CONFIG_SMTP["SMTP_PASSWORD"])
    return s

def es_error_de_cuota(exc):
    """Detecta si es límite diario de Google."""
    txt = (str(getattr(exc, "smtp_error", b"")) + " " + str(exc)).lower()
    claves = ("5.4.5", "daily user sending limit", "daily sending quota", "5.7.1", "exceeded", "quota")
    return any(k in txt for k in claves)

def es_error_transitorio(exc):
    """Detecta si es error temporal (reconectar)."""
    code = getattr(exc, "smtp_code", None)
    txt = (str(getattr(exc, "smtp_error", b"")) + " " + str(exc)).lower()
    if es_error_de_cuota(exc):
        return False
    if code in (421, 451, 454):
        return True
    claves = ("try reconnecting", "connection expired", "4.7.0", "try again later", "too many")
    return any(k in txt for k in claves)

# ============================================================================
# ACCIONES

def accion_preview(plantilla, campana, archivo_salida="preview.html"):
    """Genera preview sin enviar."""
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print(f"\n[*] Generando vista previa...")
    vars_demo = campana.copy()
    vars_demo["NOMBRE"] = "Camilo (DEMO)"
    vars_demo["ASUNTO"] = vars_demo.get("ASUNTO", "[Demo]")

    html_final = Template(plantilla).safe_substitute(**vars_demo)
    banner_rel = CONFIG_SMTP["IMG_BANNER"].relative_to(BASE).as_posix()
    html_final = html_final.replace("cid:banner", banner_rel)

    Path(archivo_salida).write_text(html_final, encoding="utf-8")
    print(f"[OK] Preview guardado: {archivo_salida}")
    print(f"     Abre en navegador para revisar HTML, colores, imagen, responsivo.")

def accion_piloto(plantilla, campana, correo_piloto, archivo_registro):
    """Envía UN correo de prueba."""
    print(f"\n[EMAIL] Enviando PILOTO a {correo_piloto}...")
    verificar_config_smtp()
    verificar_imagenes()

    vars_piloto = campana.copy()
    vars_piloto["NOMBRE"] = "Piloto Test"

    campana_id = campana.get("ID", "default")
    programa = campana.get("programa", "jc")
    s = conectar_smtp()
    try:
        cids = nuevos_cids()
        msg = construir_mensaje("Piloto Jóvenes creaTIvos", correo_piloto, plantilla, cids, vars_piloto)
        s.send_message(msg)
        registrar_envio(archivo_registro, correo_piloto, "OK", "Piloto exitoso")
        print(f"[OK] Piloto enviado a {correo_piloto}")
        print(f"  Revisa la bandeja de entrada (y spam).")
        registrar_campana_supabase(f"{campana_id} (piloto)", 1, 0, programa)
    except Exception as e:
        registrar_envio(archivo_registro, correo_piloto, "ERROR", str(e)[:200])
        print(f"[ERROR] Error enviando piloto: {e}")
        registrar_campana_supabase(f"{campana_id} (piloto)", 0, 1, programa)
        raise
    finally:
        s.quit()

def accion_enviar(plantilla, campana, archivo_lista, archivo_registro, tam_lote=500, pausa_correos=1.5, pausa_lotes=30):
    """Envío masivo con reintentos y registro."""
    print(f"\n[SEND] ENVÍO MASIVO")
    verificar_config_smtp()
    verificar_imagenes()

    lista = cargar_lista(archivo_lista)
    enviados = cargar_enviados(archivo_registro)
    pendientes = [(d["nombre"], d["correo"]) for d in lista if d["correo"] not in enviados]

    print(f"  Total en lista: {len(lista)}")
    print(f"  Ya enviados: {len(enviados)}")
    print(f"  Pendientes: {len(pendientes)}")
    print(f"  Lotes de {tam_lote}: {(len(pendientes) + tam_lote - 1) // tam_lote}")

    if not pendientes:
        print("  [OK] Nada que enviar.")
        return

    conf = input(f'\n[WARNING]  Escribe "ENVIAR {len(pendientes)}" para confirmar: ').strip()
    if conf != f"ENVIAR {len(pendientes)}":
        print("Cancelado.")
        sys.exit(0)

    enviados_ok = 0
    fallidos = 0
    s = conectar_smtp()

    try:
        cuota_alcanzada = False
        for i, (nombre, correo) in enumerate(pendientes, start=1):
            reintentos = 0
            while True:
                try:
                    vars_dest = campana.copy()
                    vars_dest["NOMBRE"] = nombre
                    cids = nuevos_cids()
                    msg = construir_mensaje(nombre, correo, plantilla, cids, vars_dest)
                    s.send_message(msg)
                    registrar_envio(archivo_registro, correo, "OK")
                    enviados_ok += 1
                    print(f"  [{i:5}/{len(pendientes)}] [OK] {correo}", flush=True)
                    break
                except smtplib.SMTPException as e:
                    if es_error_de_cuota(e):
                        registrar_envio(archivo_registro, correo, "CUOTA", str(e)[:200])
                        print(f"\n  [WARNING]  LÍMITE DIARIO ALCANZADO en {correo}")
                        print(f"      Enviados hoy: {enviados_ok}. Vuelve a ejecutar mañana.")
                        cuota_alcanzada = True
                        break
                    if es_error_transitorio(e) and reintentos < 3:
                        reintentos += 1
                        espera = 5 * reintentos
                        print(f"  [{i:5}/{len(pendientes)}] [RETRY] reconectando ({reintentos}) en {espera}s", flush=True)
                        try:
                            s.quit()
                        except:
                            pass
                        time.sleep(espera)
                        s = conectar_smtp()
                        continue
                    fallidos += 1
                    registrar_envio(archivo_registro, correo, "ERROR", str(e)[:200])
                    print(f"  [{i:5}/{len(pendientes)}] [ERROR] {correo} → {e}", flush=True)
                    try:
                        s.quit()
                    except:
                        pass
                    s = conectar_smtp()
                    break

            if cuota_alcanzada:
                break

            time.sleep(pausa_correos)
            if i % tam_lote == 0 and i < len(pendientes):
                print(f"  --- Lote {i//tam_lote} completado. Pausa {pausa_lotes}s ---")
                time.sleep(pausa_lotes)

    finally:
        try:
            s.quit()
        except:
            pass

    print(f"\n[OK] Resultado: {enviados_ok} OK | {fallidos} ERRORES")
    print(f"  Registro: {archivo_registro}")
    registrar_campana_supabase(campana.get("ID", "default"), enviados_ok, fallidos,
                               campana.get("programa", "jc"))

# ============================================================================
# MAIN

def main():
    parser = argparse.ArgumentParser(
        description="Envío parametrizado para Jóvenes creaTIvos (segura + reutilizable)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EJEMPLOS:
  python enviar_campana.py --preview campanas/recordatorio_charla_ejemplo.json
  python enviar_campana.py --piloto campanas/recordatorio_charla_ejemplo.json samueldavidvida@gmail.com
  python enviar_campana.py --enviar campanas/recordatorio_charla_ejemplo.json
        """)

    parser.add_argument("campana_json", help="Archivo JSON con config de campaña")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--preview", action="store_true", help="Genera preview.html (no envía)")
    g.add_argument("--piloto", metavar="CORREO", help="Envía UN correo de prueba a CORREO")
    g.add_argument("--enviar", action="store_true", help="Envío masivo (pide confirmación)")

    args = parser.parse_args()

    plantilla = cargar_plantilla()
    campana = cargar_campana(args.campana_json)

    if campana.get("IMG_BANNER"):
        CONFIG_SMTP["IMG_BANNER"] = BASE / campana["IMG_BANNER"]

    archivo_registro = TOOLS_DATA / f"enviados_{campana.get('ID', 'default')}.csv"

    if args.preview:
        accion_preview(plantilla, campana)
    elif args.piloto:
        accion_piloto(plantilla, campana, args.piloto, archivo_registro)
    elif args.enviar:
        archivo_lista = TOOLS_DATA / f"lista_{campana.get('ID', 'default')}.csv"
        if not archivo_lista.exists():
            raise FileNotFoundError(f"Falta CSV: {archivo_lista}")
        accion_enviar(plantilla, campana, archivo_lista, archivo_registro)

if __name__ == "__main__":
    main()
