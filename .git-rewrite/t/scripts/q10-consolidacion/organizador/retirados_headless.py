# -*- coding: utf-8 -*-
"""
retirados_headless.py — Organizador de la pestaña Retirados.
Lee Retirados (datos crudos del reporte Estudiantes cancelados de Q10) →
escribe Retirados-complete (bloques horizontales por Tipo de retiro + resumen).

Mismo patrón que organizador_headless.py (h2test): sin GUI, para n8n.

Uso:
    python retirados_headless.py
"""

import io
import os
import sys
from datetime import datetime

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ── Configuración ──────────────────────────────────────────────────────────────
SHEET_ID          = "1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs"
PESTANA_ORIGEN    = "Retirados"
PESTANA_DESTINO   = "Retirados-complete"

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CREDENCIALES_JSON = os.path.abspath(
    os.path.join(DIRECTORIO_SCRIPT, "..", "credenciales_service_account.json")
)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Orden fijo de los bloques por tipo de retiro
ORDEN_TIPOS = ["Cancelado", "Desertor", "Aplazado"]

# Columnas de cada bloque (Sede se omite: siempre "Principal - Única")
COLS_BLOQUE = ["Identificacion", "Nombre", "TipoDocumento", "Telefono",
               "Programa", "FechaCancelacion", "Causa", "Descripcion"]


# ── Utilidades ─────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[retirados] {msg}", flush=True)


def conectar() -> gspread.Client:
    if not os.path.isfile(CREDENCIALES_JSON):
        raise FileNotFoundError(f"Credenciales no encontradas: {CREDENCIALES_JSON}")
    creds = Credentials.from_service_account_file(CREDENCIALES_JSON, scopes=SCOPES)
    return gspread.authorize(creds)


# ── Lectura Retirados ──────────────────────────────────────────────────────────
def leer_retirados(gc: gspread.Client) -> pd.DataFrame:
    log(f"Leyendo pestaña '{PESTANA_ORIGEN}'...")
    ws = gc.open_by_key(SHEET_ID).worksheet(PESTANA_ORIGEN)
    datos = ws.get_all_records(default_blank="")
    if not datos:
        raise ValueError(f"La pestaña '{PESTANA_ORIGEN}' está vacía o sin encabezados.")

    df = pd.DataFrame(datos)

    columnas = ["Identificacion", "Nombre", "TipoDocumento", "Telefono", "Programa",
                "Sede", "FechaCancelacion", "Causa", "Descripcion", "Tipo"]
    for col in columnas:
        if col not in df.columns:
            raise KeyError(f"Columna requerida '{col}' no encontrada en {PESTANA_ORIGEN}.")
        df[col] = df[col].astype(str).str.replace("\n", " ", regex=False).str.strip()

    # Fecha "2023-10-30 00:00:00" → "2023-10-30"
    df["FechaCancelacion"] = df["FechaCancelacion"].str.split(" ").str[0]

    antes = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    if len(df) < antes:
        log(f"  {antes - len(df)} filas duplicadas exactas eliminadas.")

    log(f"  {len(df)} registros de retiro.")
    return df


# ── Resumen ────────────────────────────────────────────────────────────────────
def calcular_resumen(df: pd.DataFrame) -> dict:
    por_tipo  = df["Tipo"].value_counts().to_dict()
    por_causa = df["Causa"].value_counts().to_dict()
    # Mes de cancelación (YYYY-MM); fechas vacías se agrupan como "sin fecha"
    meses = df["FechaCancelacion"].str[:7].replace("", "sin fecha")
    por_mes = meses.value_counts().sort_index().to_dict()
    return {
        "total":     len(df),
        "por_tipo":  por_tipo,
        "por_causa": por_causa,
        "por_mes":   por_mes,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Escritura Retirados-complete ───────────────────────────────────────────────
def escribir_complete(gc: gspread.Client, df: pd.DataFrame, resumen: dict) -> int:
    log(f"Escribiendo '{PESTANA_DESTINO}'...")
    sh = gc.open_by_key(SHEET_ID)
    try:
        ws = sh.worksheet(PESTANA_DESTINO)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=PESTANA_DESTINO, rows="1000", cols="60")

    # clear() completo: los bloques superan el rango A1:Z1000 (ver gotcha h2test)
    ws.clear()

    tipos_extra = sorted(set(df["Tipo"].unique()) - set(ORDEN_TIPOS))
    tipos = [t for t in ORDEN_TIPOS if t in set(df["Tipo"].unique())] + tipos_extra

    n_cols = len(COLS_BLOQUE)
    bloques = []
    for tipo in tipos:
        df_t = df[df["Tipo"] == tipo].sort_values(
            by=["FechaCancelacion", "Nombre"], ascending=[False, True]
        )
        bloque = [
            [tipo.upper()] + [""] * (n_cols - 1),
            list(COLS_BLOQUE),
        ]
        for _, fila in df_t.iterrows():
            bloque.append([str(fila[c]) for c in COLS_BLOQUE])
        bloques.append(bloque)
        log(f"    {tipo}: {len(df_t)} estudiantes")

    # Bloque final: resumen agregado
    bloque_res = [
        ["RESUMEN", ""],
        ["Metrica", "Valor"],
        ["Total retirados", str(resumen["total"])],
    ]
    for tipo, n in sorted(resumen["por_tipo"].items(), key=lambda x: -x[1]):
        bloque_res.append([f"Tipo: {tipo}", str(n)])
    for causa, n in sorted(resumen["por_causa"].items(), key=lambda x: -x[1]):
        bloque_res.append([f"Causa: {causa}", str(n)])
    bloque_res.append(["Fecha actualizacion", resumen["timestamp"]])
    bloques.append(bloque_res)

    SEPARADOR = ["", ""]
    alto_max  = max(len(b) for b in bloques)
    matriz = []
    for fi in range(alto_max):
        fila_comb = []
        for bi, bloque in enumerate(bloques):
            ancho = len(bloque[0])
            if bi > 0:
                fila_comb.extend(SEPARADOR)
            fila_comb.extend(bloque[fi] if fi < len(bloque) else [""] * ancho)
        matriz.append(fila_comb)

    if matriz:
        ws.update(values=matriz, range_name="A1", value_input_option="RAW")

    log(f"  {PESTANA_DESTINO}: {len(tipos)} tipos, {alto_max} filas.")
    return alto_max


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    try:
        gc = conectar()
        df = leer_retirados(gc)
        resumen = calcular_resumen(df)
        escribir_complete(gc, df, resumen)

        pt = resumen["por_tipo"]
        log("=" * 60)
        log(f"  Total retirados : {resumen['total']}")
        for tipo, n in sorted(pt.items(), key=lambda x: -x[1]):
            log(f"    {tipo:<12}: {n}")
        log("=" * 60)
        print(
            f"RESUMEN: retirados={resumen['total']} "
            f"cancelados={pt.get('Cancelado', 0)} "
            f"desertores={pt.get('Desertor', 0)} "
            f"aplazados={pt.get('Aplazado', 0)} "
            f"estado=exito",
            flush=True,
        )

    except FileNotFoundError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except gspread.exceptions.SpreadsheetNotFound:
        print("\nERROR: Sheet no encontrado. Verifica acceso del Service Account.", file=sys.stderr)
        sys.exit(1)
    except gspread.exceptions.WorksheetNotFound as e:
        print(f"\nERROR: Pestaña no encontrada — {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\nERROR inesperado: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
