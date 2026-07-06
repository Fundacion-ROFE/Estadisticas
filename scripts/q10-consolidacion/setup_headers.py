# -*- coding: utf-8 -*-
"""
setup_headers.py — Escribe los encabezados de fila 1 en H1Test UNA SOLA VEZ.
Fundación ROFÉ | Jóvenes creaTIvos

Uso: python setup_headers.py [--pestaña NOMBRE] [--confirmar]
  --pestaña   Nombre de la pestaña a configurar (default: H1Test)
  --confirmar Necesario para realmente escribir; sin él solo muestra diagnóstico
"""

import argparse
import io
import os
import sys

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# UTF-8 en consola Windows (evita UnicodeEncodeError con → y acentos en cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import gspread
from google.oauth2.service_account import Credentials

CREDENCIALES_JSON = "credenciales_service_account.json"
DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Mapa: pestaña → Sheet ID
# NOTA: "h2test" es minúsculas intencional — así está nombrada la pestaña en Google Sheets
SHEET_IDS_POR_PESTANA = {
    "H1Test":    "1d3S41J9nlVI3qCy-WF_D3ZezTwRCW17vnL7u284XDG0",
    "h2test":    "1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs",
    "Retirados": "1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs",
}

# Mapa: pestaña → headers esperados (en orden exacto)
HEADERS_POR_PESTANA = {
    "H1Test": ["Identificacion", "Nombre", "Celular", "Email", "Curso", "Avance", "Estado"],
    "h2test": ["Identificacion", "Nombre", "Celular", "Email", "Curso", "Avance"],
    "Retirados": ["Identificacion", "Nombre", "TipoDocumento", "Telefono",
                  "Programa", "Sede", "FechaCancelacion", "Causa",
                  "Descripcion", "Tipo"],
}


def log(msg: str) -> None:
    print(f"[setup-headers] {msg}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Escribe headers de fila 1 en una pestaña de H1Test"
    )
    parser.add_argument("--pestaña", default="H1Test", help="Pestaña a configurar")
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="Sin este flag solo se muestra diagnóstico, no se escribe nada",
    )
    args = parser.parse_args()
    nombre_hoja = args.pestaña

    if nombre_hoja not in HEADERS_POR_PESTANA:
        print(f"ERROR: pestaña '{nombre_hoja}' no reconocida.", file=sys.stderr)
        print(f"  Pestañas configuradas: {list(HEADERS_POR_PESTANA.keys())}", file=sys.stderr)
        sys.exit(1)

    headers_esperados = HEADERS_POR_PESTANA[nombre_hoja]
    sheet_id = SHEET_IDS_POR_PESTANA[nombre_hoja]

    # Conectar
    ruta_creds = os.path.join(DIRECTORIO_SCRIPT, CREDENCIALES_JSON)
    if not os.path.isfile(ruta_creds):
        print(f"ERROR: no se encontró '{CREDENCIALES_JSON}'.", file=sys.stderr)
        sys.exit(1)

    log(f"Conectando a Google Sheets — pestaña '{nombre_hoja}' | Sheet ID: {sheet_id}")
    creds = Credentials.from_service_account_file(ruta_creds, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    hoja = sh.worksheet(nombre_hoja)
    log(f"  Conectado.")

    # Leer fila 1 actual
    fila1_actual = hoja.row_values(1)
    log(f"Fila 1 actual: {fila1_actual if fila1_actual else '(vacía)'}")

    # Verificar el estado
    if fila1_actual and fila1_actual != headers_esperados:
        log("ADVERTENCIA: la fila 1 ya tiene contenido distinto al esperado.")
        log(f"  Actual   : {fila1_actual}")
        log(f"  Esperado : {headers_esperados}")
        log("  → NO se sobrescribirá. Ajusta manualmente si es necesario.")
        sys.exit(1)

    if fila1_actual == headers_esperados:
        log("La fila 1 ya tiene exactamente los headers correctos. Nada que hacer.")
        sys.exit(0)

    # Fila vacía — lista para escribir
    log(f"La fila 1 está vacía. Headers a escribir: {headers_esperados}")

    if not args.confirmar:
        log("Modo diagnóstico (sin --confirmar). Para escribir, ejecuta:")
        log(f"  python setup_headers.py --pestaña {nombre_hoja} --confirmar")
        sys.exit(0)

    # Escribir
    log("Escribiendo headers en fila 1...")
    hoja.update(values=[headers_esperados], range_name="A1",
                value_input_option="RAW")

    # Verificar
    fila1_resultado = hoja.row_values(1)
    if fila1_resultado == headers_esperados:
        log(f"  OK Headers escritos correctamente: {fila1_resultado}")
    else:
        log(f"  ERROR Algo fallo. Fila 1 resultante: {fila1_resultado}")
        sys.exit(1)


if __name__ == "__main__":
    main()
