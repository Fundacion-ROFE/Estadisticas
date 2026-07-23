#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enviar_con_adjunto.py — Envía una campaña normal (lista_<ID>.csv) adjuntando el MISMO
archivo PDF a todas las destinatarias. Reutiliza toda la infraestructura de
enviar_campana.py (plantilla, imágenes inline, conexión, cuota, registro reanudable) —
no la duplica. Complementa a certificados/enviar_certificados.py, que es para adjuntos
DISTINTOS por persona.

El JSON de campaña declara dos claves extra:
  "ADJUNTO":        ruta al PDF, relativa a este directorio (o absoluta)
  "ADJUNTO_NOMBRE": nombre con el que llega el archivo al correo

USO:
  python enviar_con_adjunto.py campanas/<campana>.json --preview
  python enviar_con_adjunto.py campanas/<campana>.json --piloto <correo>
  python enviar_con_adjunto.py campanas/<campana>.json --enviar
"""
import argparse
import smtplib
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent

from enviar_campana import (  # noqa: E402
    CONFIG_SMTP,
    TOOLS_DATA,
    accion_preview,
    cargar_campana,
    cargar_enviados,
    cargar_lista,
    cargar_plantilla,
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


def resolver_adjunto(campana):
    ruta = campana.get("ADJUNTO")
    if not ruta:
        raise ValueError("El JSON de campaña no declara ADJUNTO — usa enviar_campana.py directo")
    ruta = Path(ruta)
    if not ruta.is_absolute():
        ruta = (BASE / ruta).resolve()
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el adjunto: {ruta}")
    nombre = campana.get("ADJUNTO_NOMBRE") or ruta.name
    return ruta, nombre


def main():
    parser = argparse.ArgumentParser(description="Campaña con el mismo PDF adjunto para todas")
    parser.add_argument("campana_json", help="Archivo JSON con config de campaña")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--preview", action="store_true", help="Genera preview.html (no envía)")
    g.add_argument("--piloto", metavar="CORREO", help="Envía UN correo de prueba a CORREO")
    g.add_argument("--enviar", action="store_true", help="Envío masivo (pide confirmación)")
    args = parser.parse_args()

    plantilla = cargar_plantilla()
    campana = cargar_campana(args.campana_json)

    # Mismo override de imágenes por campaña que hace enviar_campana.main()
    if campana.get("IMG_BANNER"):
        CONFIG_SMTP["IMG_BANNER"] = BASE / campana["IMG_BANNER"]
    if campana.get("IMG_FIRMA"):
        CONFIG_SMTP["IMG_FIRMA"] = BASE / campana["IMG_FIRMA"]

    campana_id = campana.get("ID", "default")
    programa = campana.get("programa", "mr")
    archivo_registro = TOOLS_DATA / f"enviados_{campana_id}.csv"

    if args.preview:
        accion_preview(plantilla, campana)
        return

    adjunto = resolver_adjunto(campana)
    print(f"[*] Adjunto para todas: {adjunto[0].name} -> llega como '{adjunto[1]}'")

    if args.piloto:
        verificar_config_smtp()
        verificar_imagenes()
        print(f"\n[EMAIL] Enviando PILOTO a {args.piloto}...")
        vars_piloto = campana.copy()
        vars_piloto["NOMBRE"] = "Piloto Test"
        s = conectar_smtp()
        try:
            cids = nuevos_cids()
            msg = construir_mensaje("Piloto Mujeres ROFÉ", args.piloto, plantilla, cids,
                                    vars_piloto, adjunto=adjunto)
            s.send_message(msg)
            registrar_envio(archivo_registro, args.piloto, "OK", "Piloto con adjunto exitoso")
            print(f"[OK] Piloto enviado a {args.piloto}. Revisa la bandeja de entrada (y spam).")
            registrar_campana_supabase(f"{campana_id} (piloto)", 1, 0, programa)
        except Exception as e:
            registrar_envio(archivo_registro, args.piloto, "ERROR", str(e)[:200])
            print(f"[ERROR] Error enviando piloto: {e}")
            registrar_campana_supabase(f"{campana_id} (piloto)", 0, 1, programa)
            raise
        finally:
            s.quit()
        return

    # --enviar
    verificar_config_smtp()
    verificar_imagenes()
    archivo_lista = TOOLS_DATA / f"lista_{campana_id}.csv"
    if not archivo_lista.exists():
        raise FileNotFoundError(f"Falta CSV: {archivo_lista}")

    lista = cargar_lista(archivo_lista)
    enviados = cargar_enviados(archivo_registro)
    pendientes = [(d["nombre"], d["correo"]) for d in lista if d["correo"] not in enviados]

    print(f"  Total en lista: {len(lista)}")
    print(f"  Ya enviados: {len(enviados)}")
    print(f"  Pendientes: {len(pendientes)}")

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
        for i, (nombre, correo) in enumerate(pendientes, start=1):
            reintentos = 0
            while True:
                try:
                    vars_dest = campana.copy()
                    vars_dest["NOMBRE"] = nombre
                    cids = nuevos_cids()
                    msg = construir_mensaje(nombre, correo, plantilla, cids, vars_dest,
                                            adjunto=adjunto)
                    s.send_message(msg)
                    registrar_envio(archivo_registro, correo, "OK")
                    enviados_ok += 1
                    print(f"  [{i:4}/{len(pendientes)}] [OK] {correo}", flush=True)
                    break
                except smtplib.SMTPException as e:
                    if es_error_de_cuota(e):
                        registrar_envio(archivo_registro, correo, "CUOTA", str(e)[:200])
                        print(f"\n  [WARNING] LÍMITE DIARIO ALCANZADO en {correo}. "
                              f"Enviados hoy: {enviados_ok}. Vuelve a ejecutar mañana.")
                        registrar_campana_supabase(campana_id, enviados_ok, fallidos, programa)
                        return
                    if es_error_transitorio(e) and reintentos < 3:
                        reintentos += 1
                        espera = 5 * reintentos
                        print(f"  [{i:4}/{len(pendientes)}] [RETRY] reconectando ({reintentos}) en {espera}s", flush=True)
                        try:
                            s.quit()
                        except Exception:
                            pass
                        time.sleep(espera)
                        s = conectar_smtp()
                        continue
                    fallidos += 1
                    registrar_envio(archivo_registro, correo, "ERROR", str(e)[:200])
                    print(f"  [{i:4}/{len(pendientes)}] [ERROR] {correo} -> {e}", flush=True)
                    try:
                        s.quit()
                    except Exception:
                        pass
                    s = conectar_smtp()
                    break
            time.sleep(1.5)
    finally:
        try:
            s.quit()
        except Exception:
            pass

    print(f"\n[OK] Resultado: {enviados_ok} OK | {fallidos} ERRORES")
    print(f"  Registro: {archivo_registro}")
    registrar_campana_supabase(campana_id, enviados_ok, fallidos, programa)


if __name__ == "__main__":
    main()
