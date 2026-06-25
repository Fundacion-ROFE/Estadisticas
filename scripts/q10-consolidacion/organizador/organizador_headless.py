# -*- coding: utf-8 -*-
"""
organizador_headless.py — Versión sin GUI del Organizador Q10.
Lee H1Test → ordena por curso → escribe h2test + Observaciones + Estadisticas.

Extrae la lógica de negocio de organizador_Q10.py para uso en n8n y automatizaciones.
No requiere pantalla ni interacción del usuario.

Uso:
    python organizador_headless.py
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
SHEET_ORIGEN_ID  = "1d3S41J9nlVI3qCy-WF_D3ZezTwRCW17vnL7u284XDG0"
SHEET_DESTINO_ID = "1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs"

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CREDENCIALES_JSON = os.path.abspath(
    os.path.join(DIRECTORIO_SCRIPT, "..", "credenciales_service_account.json")
)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# ── Utilidades ─────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[organizador] {msg}", flush=True)


# ── Conexión ───────────────────────────────────────────────────────────────────
def conectar() -> gspread.Client:
    if not os.path.isfile(CREDENCIALES_JSON):
        raise FileNotFoundError(
            f"Credenciales no encontradas: {CREDENCIALES_JSON}"
        )
    creds = Credentials.from_service_account_file(CREDENCIALES_JSON, scopes=SCOPES)
    return gspread.authorize(creds)


# ── Lectura H1Test ─────────────────────────────────────────────────────────────
def leer_h1test(gc: gspread.Client) -> pd.DataFrame:
    log("Leyendo H1Test...")
    ws = gc.open_by_key(SHEET_ORIGEN_ID).worksheet("H1Test")
    datos = ws.get_all_records(default_blank="")
    if not datos:
        raise ValueError("H1Test está vacía o sin encabezados.")

    df = pd.DataFrame(datos)

    columnas_requeridas = ["Identificacion", "Nombre", "Celular", "Email", "Curso", "Avance"]
    for col in columnas_requeridas:
        if col not in df.columns:
            match = [c for c in df.columns if c.lower() == col.lower()]
            if match:
                df.rename(columns={match[0]: col}, inplace=True)
            else:
                raise KeyError(f"Columna requerida '{col}' no encontrada en H1Test.")

    if "Estado" not in df.columns:
        match = [c for c in df.columns if c.lower() == "estado"]
        if match:
            df.rename(columns={match[0]: "Estado"}, inplace=True)
        else:
            df["Estado"] = "A"

    for col in columnas_requeridas + ["Estado"]:
        df[col] = df[col].astype(str).str.strip()
    df['Avance'] = df['Avance'].str.replace('%', '', regex=False).str.strip()

    df['_av_num'] = pd.to_numeric(df['Avance'], errors='coerce').fillna(-1)
    df = (df.sort_values('_av_num', ascending=False)
            .drop_duplicates(subset=['Identificacion', 'Curso'], keep='first')
            .drop(columns=['_av_num'])
            .reset_index(drop=True))

    log(f"  {len(df)} filas tras deduplicación.")
    return df


# ── Lógica de anomalías (misma que organizador_Q10.py) ────────────────────────
def calcular_observaciones(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for _, fila in df.iterrows():
        email     = fila['Email']
        curso     = fila['Curso']
        avance_str = fila['Avance']
        try:
            avance_num = float(avance_str) if avance_str != "" else None
        except ValueError:
            avance_num = None

        estado = fila.get('Estado', 'A').strip().upper()
        base = {
            "Identificacion": fila['Identificacion'],
            "Nombre":         fila['Nombre'],
            "Celular":        fila.get('Celular', ''),
            "Email":          email,
            "Curso":          curso,
            "Avance":         avance_str,
            "Estado":         estado,
        }

        if estado not in ('A', ''):
            filas.append({**base, "Categoria": "NO HABILITADO", "Curso": curso or "[N/A]",
                          "Observacion": f"Estado Q10: {estado}"})
            continue
        if curso == "" and avance_str == "" and email != "":
            filas.append({**base, "Categoria": "SIN MATCH", "Curso": "[N/A]",
                          "Observacion": "Email no encontrado en reporte de cursos"})
            continue
        if curso == "":
            filas.append({**base, "Categoria": "SIN CURSO",
                          "Observacion": "Sin curso asignado en Q10"})
        if curso != "" and avance_str in ("0", "0.0", "0%"):
            filas.append({**base, "Categoria": "AVANCE 0%",
                          "Observacion": "Matriculado pero sin actividad registrada"})
        if avance_num is not None and avance_num > 100.0:
            filas.append({**base, "Categoria": "AVANCE IRREGULAR",
                          "Observacion": "Avance superior al 100% — revisar en Q10"})

    cols = ["Categoria", "Identificacion", "Nombre", "Celular",
            "Email", "Curso", "Avance", "Estado", "Observacion"]
    return pd.DataFrame(filas, columns=cols) if filas else pd.DataFrame(columns=cols)


def calcular_estadisticas(df: pd.DataFrame) -> dict:
    emails_validos   = df['Email'].replace("", pd.NA).dropna()
    avance_num       = pd.to_numeric(df['Avance'], errors='coerce')
    avance_valido    = avance_num.dropna()
    df_con_curso     = df[df['Curso'] != ""].copy()
    df_con_curso['_av'] = pd.to_numeric(df_con_curso['Avance'], errors='coerce')

    stats_por_curso = []
    for curso in sorted(df_con_curso['Curso'].unique()):
        df_c = df_con_curso[df_con_curso['Curso'] == curso]
        av_c = df_c['_av'].dropna()
        stats_por_curso.append({
            'Curso':       curso,
            'Estudiantes': len(df_c),
            'Promedio':    round(av_c.mean(), 1) if not av_c.empty else 0.0,
            'Min':         round(av_c.min(),  1) if not av_c.empty else 0.0,
            'Max':         round(av_c.max(),  1) if not av_c.empty else 0.0,
        })

    df_obs    = calcular_observaciones(df)
    anomalias = {
        'NO HABILITADO':    int((df_obs['Categoria'] == 'NO HABILITADO').sum()),
        'SIN CURSO':        int((df_obs['Categoria'] == 'SIN CURSO').sum()),
        'AVANCE 0%':        int((df_obs['Categoria'] == 'AVANCE 0%').sum()),
        'SIN MATCH':        int((df_obs['Categoria'] == 'SIN MATCH').sum()),
        'AVANCE IRREGULAR': int((df_obs['Categoria'] == 'AVANCE IRREGULAR').sum()),
    }

    if 'Estado' in df.columns:
        df_hab = df[df['Estado'].str.upper().isin(['A', ''])]
        total_habilitados = int(df_hab['Email'].replace("", pd.NA).dropna().nunique())
    else:
        total_habilitados = int(emails_validos.nunique())

    return {
        'total_registros':    len(df),
        'total_estudiantes':  int(emails_validos.nunique()),
        'total_habilitados':  total_habilitados,
        'promedio_general':   round(avance_valido.mean(), 1) if not avance_valido.empty else 0.0,
        'stats_por_curso':    stats_por_curso,
        'anomalias':          anomalias,
        'timestamp':          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Escritura h2test (bloques horizontales por curso) ─────────────────────────
def escribir_h2test(gc: gspread.Client, df: pd.DataFrame) -> tuple:
    log("Escribiendo h2test...")
    sheet_destino = gc.open_by_key(SHEET_DESTINO_ID)

    try:
        ws_h2 = sheet_destino.worksheet("h2test")
    except gspread.exceptions.WorksheetNotFound:
        ws_h2 = sheet_destino.add_worksheet(title="h2test", rows="1000", cols="100")

    try:
        sheet_destino.values_clear("'h2test'!A1:Z1000")
    except Exception:
        ws_h2.clear()

    cursos_detectados = sorted(df[df['Curso'] != '']['Curso'].unique())

    bloques = []
    for curso in cursos_detectados:
        df_c = df[df['Curso'] == curso].sort_values(by='Nombre')
        bloque = [
            [curso.upper(), "", "", "", "", ""],
            ["Identificacion", "Nombre", "Celular", "Email", "Avance", "Estado"],
        ]
        for _, fila in df_c.iterrows():
            bloque.append([str(fila['Identificacion']), str(fila['Nombre']),
                           str(fila['Celular']), str(fila['Email']),
                           str(fila['Avance']), str(fila.get('Estado', ''))])
        bloques.append(bloque)
        hab = int((df_c.get('Estado', pd.Series(['A'] * len(df_c))).str.upper().isin(['A', ''])).sum())
        log(f"    {curso}: {len(df_c)} estudiantes ({hab} activos)")

    df_sc = df[df['Curso'] == ""].sort_values(by='Nombre')
    bloque_sc = [
        ["SIN CURSO ASIGNADO", "", "", "", "", ""],
        ["Identificacion", "Nombre", "Celular", "Email", "", "Estado"],
    ]
    for _, fila in df_sc.iterrows():
        bloque_sc.append([str(fila['Identificacion']), str(fila['Nombre']),
                          str(fila['Celular']), str(fila['Email']), "",
                          str(fila.get('Estado', ''))])
    bloques.append(bloque_sc)

    COLS_BLOQUE = 6
    SEPARADOR   = ["", ""]
    alto_max    = max(len(b) for b in bloques) if bloques else 0

    matriz_salida = []
    for fi in range(alto_max):
        fila_combinada = []
        for bi, bloque in enumerate(bloques):
            if bi > 0:
                fila_combinada.extend(SEPARADOR)
            fila_combinada.extend(bloque[fi] if fi < len(bloque) else [""] * COLS_BLOQUE)
        matriz_salida.append(fila_combinada)

    if matriz_salida:
        ws_h2.update(values=matriz_salida, range_name="A1")

    log(f"  h2test: {len(cursos_detectados)} cursos, {alto_max} filas.")
    return cursos_detectados, len(df_sc)


# ── Escritura Observaciones ────────────────────────────────────────────────────
def escribir_observaciones(gc: gspread.Client, df: pd.DataFrame) -> int:
    log("Escribiendo Observaciones...")
    sheet_destino = gc.open_by_key(SHEET_DESTINO_ID)
    try:
        ws_obs = sheet_destino.worksheet("Observaciones")
    except gspread.exceptions.WorksheetNotFound:
        ws_obs = sheet_destino.add_worksheet(title="Observaciones", rows="2000", cols="10")

    try:
        sheet_destino.values_clear("'Observaciones'!A1:J2000")
    except Exception:
        ws_obs.clear()

    df_obs  = calcular_observaciones(df)
    cols_obs = ["Categoria", "Identificacion", "Nombre", "Celular",
                "Email", "Curso", "Avance", "Estado", "Observacion"]
    filas   = [cols_obs] + [[str(fila[c]) for c in cols_obs] for _, fila in df_obs.iterrows()]
    ws_obs.update(values=filas, range_name="A1")
    log(f"  Observaciones: {len(filas) - 1} casos.")
    return len(filas) - 1


# ── Escritura Estadisticas ─────────────────────────────────────────────────────
def escribir_estadisticas(gc: gspread.Client, df: pd.DataFrame) -> dict:
    log("Escribiendo Estadisticas...")
    sheet_destino = gc.open_by_key(SHEET_DESTINO_ID)
    try:
        ws_stats = sheet_destino.worksheet("Estadisticas")
    except gspread.exceptions.WorksheetNotFound:
        ws_stats = sheet_destino.add_worksheet(title="Estadisticas", rows="200", cols="10")

    try:
        sheet_destino.values_clear("'Estadisticas'!A1:J200")
    except Exception:
        ws_stats.clear()

    stats = calcular_estadisticas(df)
    filas = [
        ["RESUMEN GENERAL", ""],
        ["Metrica", "Valor"],
        ["Total registros",         stats['total_registros']],
        ["Estudiantes matriculados", stats['total_estudiantes']],
        ["Estudiantes activos (A)", stats.get('total_habilitados', stats['total_estudiantes'])],
        ["Promedio avance general", f"{stats['promedio_general']}%"],
        ["Fecha actualizacion",     stats['timestamp']],
        ["", ""],
        ["POR CURSO", "", "", "", ""],
        ["Curso", "Estudiantes", "Promedio %", "Min %", "Max %"],
    ]
    for s in stats['stats_por_curso']:
        filas.append([s['Curso'], s['Estudiantes'],
                      f"{s['Promedio']}%", f"{s['Min']}%", f"{s['Max']}%"])
    filas += [["", ""], ["ANOMALIAS", ""], ["Categoria", "Cantidad"]]
    for cat, cant in stats['anomalias'].items():
        filas.append([cat, cant])

    ws_stats.update(values=filas, range_name="A1")
    log(f"  Estadisticas: {len(stats['stats_por_curso'])} cursos procesados.")
    return stats


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    try:
        gc = conectar()
        df = leer_h1test(gc)

        cursos, sin_curso = escribir_h2test(gc, df)
        obs_count         = escribir_observaciones(gc, df)
        stats             = escribir_estadisticas(gc, df)

        log("=" * 60)
        log(f"  Cursos procesados   : {len(cursos)}")
        log(f"  Sin curso           : {sin_curso}")
        log(f"  Observaciones       : {obs_count}")
        log(f"  Promedio general    : {stats['promedio_general']}%")
        log("=" * 60)
        print(
            f"RESUMEN: cursos={len(cursos)} "
            f"estudiantes={stats['total_estudiantes']} "
            f"habilitados={stats.get('total_habilitados', stats['total_estudiantes'])} "
            f"promedio={stats['promedio_general']} "
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
