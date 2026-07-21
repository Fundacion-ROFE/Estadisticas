# -*- coding: utf-8 -*-
"""
sync_emoflow_participacion.py — % de participación Emoflow por ciudad → Supabase.

Fuente: pestaña `Estadísticas` de la BD Seguimiento de Monitorias (mismo Google Sheet que
`+Ingresos-EmoFlow`/`Avance`, id 1ggzoJeZR...). Es un tablero apilado con muchos bloques
verticales (uno por curso/métrica); el bloque que nos interesa tiene encabezado 'EMOFLOW' en
columna A, con 9 filas de ciudad + fila total, y columna `Avance` = Completado/Real = "%
participación". Una fila arriba trae la etiqueta "Semana N".

⚠ El bloque NO tiene posición fija — se mueve cada semana según lo que el equipo agrega/borra
arriba. Por eso se localiza SIEMPRE por texto (buscar 'EMOFLOW' en columna A), nunca por número
de fila fijo. Verificado empíricamente: entre el 09-jul y el 15-jul la fila del bloque cambió de
169 a 184 al pasar de "Semana 15" a "Semana 16".

⚠ El bloque tampoco preserva semanas anteriores (se sobrescribe/mueve). Por eso este script hace
UPSERT DIARIO por (fecha_corte, grupo_ciudad): leer el mismo bloque "Semana N" varios días
seguidos captura cómo sube Completado/Real DENTRO de esa semana; el histórico real lo construye
Supabase acumulando snapshots, no la Sheet.

Solo agregados por ciudad — sin PII (no hay cédulas ni correos en este bloque).

Uso:
    python sync_emoflow_participacion.py [--dry-run]
Consola (parseable por n8n):
    RESUMEN: semana=N ciudades=M estado=exito

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime

try:
    import truststore
    truststore.inject_into_ssl()          # SSL corporativo (convención del proyecto)
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import gspread
from google.oauth2.service_account import Credentials

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_CREDENCIALES = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion",
                                 "credenciales_service_account.json")

SHEET_ID   = "1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8"   # BD Seguimiento de Monitorias
PESTANA    = "Estadísticas"
USER_AGENT = "panel-datos-etl/1.0"   # Supabase rechaza secrets con UA de navegador
BUSQUEDA_MAX_FILAS = 2500            # techo razonable de la pestaña (hoy ~2228 filas)

CIUDADES_VALIDAS = {"BAQ", "BOG", "CAL", "CTG", "MED", "GYL", "QTO", "PAN", "UY"}


def log(msg: str) -> None:
    print(f"[sync-emoflow-participacion] {msg}", flush=True)


def cargar_env_local() -> None:
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
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.key = key

    def _req(self, metodo: str, ruta: str, cuerpo=None, prefer: str = ""):
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}",
                   "Content-Type": "application/json", "User-Agent": USER_AGENT}
        if prefer:
            headers["Prefer"] = prefer
        req = urllib.request.Request(self.base + ruta, method=metodo, headers=headers,
                                     data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                datos = resp.read()
                return resp.status, json.loads(datos) if datos else None
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: "
                               f"{e.read().decode(errors='replace')[:500]}") from None

    def upsert(self, tabla: str, filas: list, conflicto: str) -> int:
        if not filas:
            return 0
        self._req("POST", f"/{tabla}?on_conflict={conflicto}", filas,
                  prefer="resolution=merge-duplicates,return=minimal")
        return len(filas)


def parse_int(valor) -> int | None:
    v = str(valor).strip().replace(".", "").replace(",", "")
    return int(v) if v.lstrip("-").isdigit() else None


def parse_pct(valor) -> float | None:
    """'53,85%' → 53.85 (escala 0-100, mismo criterio que pct_aprobados en el proyecto)."""
    v = str(valor).strip().replace("%", "").replace(",", ".")
    try:
        return round(float(v), 2)
    except ValueError:
        return None


def ubicar_bloque_emoflow(ws) -> tuple[int, int]:
    """Busca 'EMOFLOW' en la columna A → (fila_header, semana). Nunca asumir fila fija:
    el bloque se mueve en la hoja de una corrida a otra (verificado 09-jul→15-jul)."""
    col_a = ws.col_values(1)[:BUSQUEDA_MAX_FILAS]
    fila_header = next((i + 1 for i, v in enumerate(col_a) if v.strip().upper() == "EMOFLOW"), None)
    if fila_header is None:
        raise RuntimeError("No se encontró el bloque 'EMOFLOW' en columna A de Estadísticas — "
                            "¿cambió de nombre o se movió fuera del rango de búsqueda?")

    # La etiqueta "Semana N" vive una fila arriba, en la misma columna que el encabezado
    # 'Sin completar' (offset, no en columna A) — se busca en toda la fila.
    fila_arriba = ws.row_values(fila_header - 1)
    texto_semana = next((c for c in fila_arriba if isinstance(c, str) and "semana" in c.lower()), None)
    if not texto_semana:
        raise RuntimeError(f"Bloque EMOFLOW en fila {fila_header} pero sin etiqueta 'Semana N' "
                            f"en la fila anterior — revisar estructura manualmente.")
    m = re.search(r"\d+", texto_semana)
    semana = int(m.group()) if m else None
    if semana is None:
        raise RuntimeError(f"Etiqueta de semana sin número reconocible: {texto_semana!r}")

    return fila_header, semana


def leer_bloque(ws, fila_header: int) -> list[dict]:
    """Filas de ciudad bajo el header, hasta la primera fila totalmente vacía. Se descarta la
    fila de totales (Grupo vacío) — es un agregado derivable, no una fila por ciudad."""
    filas = []
    fila = fila_header + 1
    while True:
        vals = ws.row_values(fila)
        vals += [""] * (10 - len(vals))  # normalizar largo (A..J)
        grupo = vals[1].strip().upper()
        if not any(v.strip() for v in vals[:10]):
            break  # fila en blanco → fin del bloque
        if grupo and grupo in CIUDADES_VALIDAS:
            filas.append({
                "grupo_ciudad":    grupo,
                "seleccionados":   parse_int(vals[2]),
                "seleccionados_f": parse_int(vals[3]),
                "real":            parse_int(vals[4]),
                "revocados":       parse_int(vals[5]),
                "retirados":       parse_int(vals[6]),
                "sin_completar":   parse_int(vals[7]),
                "completado":      parse_int(vals[8]),
                "avance_pct":      parse_pct(vals[9]),
            })
        elif grupo and grupo not in CIUDADES_VALIDAS:
            log(f"ADVERTENCIA: fila {fila} con Grupo desconocido {grupo!r} — omitida")
        fila += 1
        if fila - fila_header > 15:  # tope de seguridad (9 ciudades + total + margen)
            log("ADVERTENCIA: bloque más largo de lo esperado, corte de seguridad en 15 filas")
            break
    return filas


def main() -> int:
    ap = argparse.ArgumentParser(description="% participación Emoflow (Estadísticas) → Supabase")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log("ERROR: falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY (.env.local)")
        print("RESUMEN: semana=0 ciudades=0 estado=error")
        return 1

    creds = Credentials.from_service_account_file(
        RUTA_CREDENCIALES, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    ws = gspread.authorize(creds).open_by_key(SHEET_ID).worksheet(PESTANA)
    log(f"Leyendo pestaña '{PESTANA}'...")

    fila_header, semana = ubicar_bloque_emoflow(ws)
    log(f"Bloque EMOFLOW localizado en fila {fila_header} — Semana {semana}")

    ciudades = leer_bloque(ws, fila_header)
    if not ciudades:
        log("ERROR: el bloque EMOFLOW no trajo filas de ciudad válidas")
        print("RESUMEN: semana=0 ciudades=0 estado=error")
        return 1
    log(f"{len(ciudades)} ciudades leídas")

    hoy = date.today().isoformat()
    filas = [{**c, "fecha_corte": hoy, "semana": semana, "fuente": "sync-diario"}
              for c in ciudades]

    if args.dry_run:
        for f in filas:
            log(f"  {f['grupo_ciudad']}: real={f['real']} completado={f['completado']} "
                f"avance={f['avance_pct']}%")
        print(f"RESUMEN: semana={semana} ciudades={len(filas)} estado=dry-run")
        return 0

    supa = Supa(url, key)
    supa.upsert("emoflow_participacion_semanal", filas, "fecha_corte,grupo_ciudad")
    log(f"Upsert OK: {len(filas)} filas (fecha_corte={hoy}, semana={semana})")

    print(f"RESUMEN: semana={semana} ciudades={len(filas)} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
