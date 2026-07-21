#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enviar_certificados.py — Envía cada certificado PDF (uno por página, generado por
preparar_certificados.py) a su dueña, con adjunto propio. Reutiliza toda la infraestructura
SMTP de enviar_campana.py (conexión, reintentos, cuota, registro reanudable) — no la duplica.

USO:
  python enviar_certificados.py campanas/<campana>.json --piloto <correo>
  python enviar_certificados.py campanas/<campana>.json --enviar
"""
import argparse
import csv
import smtplib
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE.parent))  # para importar enviar_campana.py

from enviar_campana import (  # noqa: E402
    CONFIG_SMTP,
    accion_preview,  # noqa: F401 (reexport, no se usa aquí pero mantiene paridad de API)
    cargar_campana,
    cargar_plantilla,
    cargar_enviados,
    conectar_smtp,
    construir_mensaje,
    es_error_de_cuota,
    es_error_transitorio,
    nuevos_cids,
    registrar_campana_supabase,
    registrar_envio,
    verificar_config_smtp,
    verificar_imagenes,
)

TOOLS_DATA = BASE.parent.parent.parent / "tools" / "mujeres-rofe-correos" / "data" / "certificados"
RUTA_MATCHES = TOOLS_DATA / "certificados_matches.csv"


def cargar_matches():
    """Carga certificados_matches.csv, filtrando filas sin correo o marcadas revisar=SI."""
    if not RUTA_MATCHES.exists():
        raise FileNotFoundError(f"Falta {RUTA_MATCHES} — corre primero preparar_certificados.py")

    validos, excluidos = [], []
    with open(RUTA_MATCHES, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            correo = (row.get("correo") or "").strip().lower()
            revisar = (row.get("revisar") or "").strip().upper()
            fila = {
                "nombre": row.get("nombre_bd") or row.get("nombre_certificado") or "",
                "correo": correo,
                "archivo_pdf": TOOLS_DATA / row["archivo_pdf"],
            }
            if correo and revisar != "SI":
                validos.append(fila)
            else:
                excluidos.append(fila)
    return validos, excluidos


def main():
    parser = argparse.ArgumentParser(description="Envía certificados personalizados con adjunto por destinataria")
    parser.add_argument("campana_json", help="Archivo JSON con config de campaña (asunto, copy del correo)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--piloto", metavar="CORREO", help="Envía UN certificado de prueba a CORREO")
    g.add_argument("--enviar", action="store_true", help="Envío masivo a todas las filas válidas")
    args = parser.parse_args()

    campana = cargar_campana(args.campana_json)
    campana_id = campana.get("ID", "certificados")

    # Plantilla propia de esta campaña (ej. sin banner de encabezado), igual patrón que
    # IMG_BANNER/IMG_FIRMA en enviar_campana.py. Si no la declara, usa la plantilla genérica.
    if campana.get("PLANTILLA_TEMPLATE"):
        plantilla = (BASE.parent / campana["PLANTILLA_TEMPLATE"]).read_text(encoding="utf-8")
    else:
        plantilla = cargar_plantilla()
    archivo_registro = BASE.parent.parent.parent / "tools" / "mujeres-rofe-correos" / "data" / f"enviados_{campana_id}.csv"

    validos, excluidos = cargar_matches()
    print(f"[*] {len(validos)} certificados listos para enviar | {len(excluidos)} excluidos (sin correo o revisar=SI)")

    if args.piloto:
        if not validos:
            raise ValueError("No hay ningún certificado válido en certificados_matches.csv para probar")
        verificar_config_smtp()
        verificar_imagenes()
        muestra = validos[0]
        print(f"\n[EMAIL] Enviando PILOTO a {args.piloto} (adjunto de muestra: {muestra['nombre']})...")

        vars_piloto = campana.copy()
        vars_piloto["NOMBRE"] = "Piloto Test"
        s = conectar_smtp()
        try:
            cids = nuevos_cids()
            msg = construir_mensaje(
                "Piloto Mujeres ROFÉ", args.piloto, plantilla, cids, vars_piloto,
                adjunto=(muestra["archivo_pdf"], f"certificado_{campana_id}.pdf"),
            )
            s.send_message(msg)
            registrar_envio(archivo_registro, args.piloto, "OK", "Piloto certificados exitoso")
            print(f"[OK] Piloto enviado a {args.piloto}. Revisa la bandeja de entrada (y spam).")
            registrar_campana_supabase(f"{campana_id} (piloto)", 1, 0, campana.get("programa", "mr"))
        except Exception as e:
            registrar_envio(archivo_registro, args.piloto, "ERROR", str(e)[:200])
            print(f"[ERROR] Error enviando piloto: {e}")
            registrar_campana_supabase(f"{campana_id} (piloto)", 0, 1, campana.get("programa", "mr"))
            raise
        finally:
            s.quit()
        return

    # --enviar
    if not validos:
        print("[OK] Nada que enviar (0 filas válidas).")
        return

    verificar_config_smtp()
    verificar_imagenes()

    enviados = cargar_enviados(archivo_registro)
    pendientes = [v for v in validos if v["correo"] not in enviados]

    print(f"  Total válidos: {len(validos)}")
    print(f"  Ya enviados: {len(enviados)}")
    print(f"  Pendientes: {len(pendientes)}")
    if excluidos:
        print(f"  [AVISO] {len(excluidos)} certificados excluidos (sin correo o revisar=SI) — no se envían:")
        for e in excluidos:
            print(f"    - pág {e['archivo_pdf'].name}: {e['nombre'] or '(sin nombre detectado)'}")

    if not pendientes:
        print("  [OK] Nada que enviar.")
        return

    conf = input(f'\n[WARNING]  Escribe "ENVIAR {len(pendientes)}" para confirmar: ').strip()
    if conf != f"ENVIAR {len(pendientes)}":
        print("Cancelado.")
        sys.exit(0)

    enviados_ok, fallidos = 0, 0
    s = conectar_smtp()
    try:
        for i, dest in enumerate(pendientes, start=1):
            try:
                vars_dest = campana.copy()
                vars_dest["NOMBRE"] = dest["nombre"]
                cids = nuevos_cids()
                nombre_archivo = f"certificado_{dest['nombre'].replace(' ', '_')}.pdf"
                msg = construir_mensaje(
                    dest["nombre"], dest["correo"], plantilla, cids, vars_dest,
                    adjunto=(dest["archivo_pdf"], nombre_archivo),
                )
                s.send_message(msg)
                registrar_envio(archivo_registro, dest["correo"], "OK")
                enviados_ok += 1
                print(f"  [{i:3}/{len(pendientes)}] [OK] {dest['correo']}", flush=True)
            except smtplib.SMTPException as e:
                if es_error_de_cuota(e):
                    registrar_envio(archivo_registro, dest["correo"], "CUOTA", str(e)[:200])
                    print(f"\n  [WARNING] LÍMITE DIARIO ALCANZADO en {dest['correo']}. Enviados: {enviados_ok}.")
                    break
                if es_error_transitorio(e):
                    print(f"  [{i:3}/{len(pendientes)}] [RETRY] reconectando...", flush=True)
                    try:
                        s.quit()
                    except Exception:
                        pass
                    time.sleep(5)
                    s = conectar_smtp()
                    try:
                        s.send_message(msg)
                        registrar_envio(archivo_registro, dest["correo"], "OK")
                        enviados_ok += 1
                        print(f"  [{i:3}/{len(pendientes)}] [OK] {dest['correo']} (tras reintento)", flush=True)
                        continue
                    except Exception as e2:
                        e = e2
                fallidos += 1
                registrar_envio(archivo_registro, dest["correo"], "ERROR", str(e)[:200])
                print(f"  [{i:3}/{len(pendientes)}] [ERROR] {dest['correo']} -> {e}", flush=True)
            time.sleep(1.5)
    finally:
        try:
            s.quit()
        except Exception:
            pass

    print(f"\n[OK] Resultado: {enviados_ok} OK | {fallidos} ERRORES")
    registrar_campana_supabase(campana_id, enviados_ok, fallidos, campana.get("programa", "mr"))


if __name__ == "__main__":
    main()
