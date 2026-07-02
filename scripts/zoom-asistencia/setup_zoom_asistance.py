# -*- coding: utf-8 -*-
"""Setup de pestañas ZOOM-ASISTANCE + CUPOS + ZOOM-STATS en el spreadsheet H3Test.

Reemplaza la lógica manual de asistencia de la BD Seguimiento de Monitorias:
- ZOOM-ASISTANCE: destino de escritura del workflow n8n `Zoom - Asistencia`
  (mismos 8 headers que H3Test). Formato condicional: fila roja si % Asistencia < 70%,
  celda verde si >= 70%.
- CUPOS: cantidad de estudiantes inscritos por clase (denominador del "X de Y"),
  extraída de tools/cupos_clases.json (análisis local de la BD pseudonimizada).
- ZOOM-STATS: estadísticas automáticas por fórmula — por sesión (conectados,
  "X de Y", % del cupo, promedio % estancia, alumnos <70%) y por semana ISO.

Idempotente: si una pestaña ya existe se limpia y reconstruye.
Uso:  python setup_zoom_asistance.py [--sin-migrar]
"""
import argparse
import json
import sys
from pathlib import Path

import truststore

truststore.inject_into_ssl()

import gspread
from google.oauth2.service_account import Credentials

BASE = Path(__file__).resolve().parents[2]
CRED = BASE / "scripts" / "q10-consolidacion" / "credenciales_service_account.json"
CUPOS_JSON = BASE / "tools" / "cupos_clases.json"

SHEET_ID = "1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0"
TAB_ORIGEN = "H3Test"
TAB_ASIST = "ZOOM-ASISTANCE"
TAB_CUPOS = "CUPOS"
TAB_STATS = "ZOOM-STATS"

HEADERS = ["Nombre", "Apellido", "Correo electrónico", "Identificacion",
           "Instancias", "Curso", "Fecha", "% Asistencia"]

FILAS_ASIST = 20000     # capacidad de filas de asistencia
FILAS_SESIONES = 800    # sesiones (clase dictada) con fórmulas prellenadas
FILAS_SEMANAS = 60      # semanas con fórmulas prellenadas
UMBRAL = 70             # % mínimo de asistencia correcta

AREAS = {
    "Horario HTML": "HTML",
    "Horario Lógica": "Lógica",
    "Horario IA": "IA",
    "Horario EMP": "Emprendimiento",
    "Horario HE": "Habilidades Esenciales",
    "Horario Hackea": "Hackea tu cerebro",
    "Horario de Bienvenida": "Bienvenida",
}

# % Asistencia puede venir numérico (0.98, escrito por n8n con USER_ENTERED) o
# texto "98%" (escrituras manuales/retroactivas) — ambas formas se normalizan.
F_PCT_NUM = ('IF(ISNUMBER($H{f}), $H{f}*100, '
             'IFERROR(VALUE(SUBSTITUTE($H{f}&"","%","")),{defecto}))')


def loc(formula):
    """El spreadsheet tiene locale es_ES: el separador de argumentos es ';'.
    Ninguna fórmula de este script usa comas literales dentro de strings."""
    return formula.replace(",", ";")


def loc_filas(filas):
    return [[loc(c) if isinstance(c, str) and c.startswith("=") else c for c in fila]
            for fila in filas]


def color(hexcolor):
    h = hexcolor.lstrip("#")
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255,
            "blue": int(h[4:6], 16) / 255}


def regla_formula(sheet_id, r1, r2, c1, c2, formula, bg, fg=None, indice=0):
    """Request addConditionalFormatRule con fórmula personalizada (filas/cols 0-based, fin exclusivo)."""
    formato = {"backgroundColor": bg}
    if fg:
        formato["textFormat"] = {"foregroundColor": fg}
    return {"addConditionalFormatRule": {"index": indice, "rule": {
        "ranges": [{"sheetId": sheet_id, "startRowIndex": r1, "endRowIndex": r2,
                    "startColumnIndex": c1, "endColumnIndex": c2}],
        "booleanRule": {
            "condition": {"type": "CUSTOM_FORMULA",
                          "values": [{"userEnteredValue": loc(formula)}]},
            "format": formato,
        }}}}


def recrear(sh, titulo, filas, cols):
    try:
        ws = sh.worksheet(titulo)
        sh.del_worksheet(ws)
        print(f"  Pestaña {titulo} existía — recreada desde cero")
    except gspread.WorksheetNotFound:
        pass
    return sh.add_worksheet(title=titulo, rows=filas, cols=cols)


def construir_zoom_asistance(sh, migrar):
    ws = recrear(sh, TAB_ASIST, FILAS_ASIST, len(HEADERS))
    ws.update(values=[HEADERS], range_name="A1", value_input_option="USER_ENTERED")

    if migrar:
        origen = sh.worksheet(TAB_ORIGEN)
        filas = origen.get_all_values()[1:]
        if filas:
            ws.update(values=filas, range_name="A2", value_input_option="USER_ENTERED")
        print(f"  Migradas {len(filas)} filas desde {TAB_ORIGEN}")

    rojo_fila = ("=AND($H2<>\"\", " + F_PCT_NUM.format(f="2", defecto=100)
                 + f" < {UMBRAL})")
    verde_celda = ("=AND($H2<>\"\", " + F_PCT_NUM.format(f="2", defecto=0)
                   + f" >= {UMBRAL})")
    requests = [
        {"updateSheetProperties": {"properties": {
            "sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount"}},
        {"repeatCell": {"range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {"userEnteredFormat": {
                            "textFormat": {"bold": True, "foregroundColor": color("#ffffff")},
                            "backgroundColor": color("#1f4e79")}},
                        "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
        # Fila completa roja cuando el estudiante no tomó bien la clase (<70%)
        regla_formula(ws.id, 1, FILAS_ASIST, 0, 8, rojo_fila,
                      color("#f4c7c3"), color("#990000"), 0),
        # Celda del % en verde cuando cumplió
        regla_formula(ws.id, 1, FILAS_ASIST, 7, 8, verde_celda,
                      color("#c6e7c8"), color("#1a5e20"), 1),
    ]
    sh.batch_update({"requests": requests})
    print(f"  {TAB_ASIST} lista: headers + formato condicional (<{UMBRAL}% rojo / >={UMBRAL}% verde)")
    return ws


def construir_cupos(sh):
    datos = json.loads(CUPOS_JSON.read_text(encoding="utf-8"))
    cupos = datos["cupos_por_columna"]

    # Preservar los alias Zoom escritos a mano por el equipo (columna D)
    alias_previos = {}
    try:
        previa = sh.worksheet(TAB_CUPOS).get_all_values()
        for f in previa[1:]:
            if len(f) >= 4 and f[1].strip() and f[3].strip():
                alias_previos[f[1].strip()] = f[3].strip()
    except gspread.WorksheetNotFound:
        pass

    filas = [["Área", "Clase", "Inscritos", "Alias Zoom (topic exacto de la reunión)"]]
    resumen = [["Área", "Clases", "Total estudiantes"]]
    for col_horario, area in AREAS.items():
        clases = cupos.get(col_horario, {})
        for clase, n in sorted(clases.items(), key=lambda kv: (-kv[1], kv[0])):
            filas.append([area, clase, n, alias_previos.get(clase, "")])
        resumen.append([area, len(clases), sum(clases.values())])

    ws = recrear(sh, TAB_CUPOS, max(len(filas) + 10, 120), 8)
    ws.update(values=filas, range_name="A1", value_input_option="USER_ENTERED")
    ws.update(values=resumen, range_name="E1", value_input_option="USER_ENTERED")
    ws.update(values=[[f"Fuente: {datos['fuente']} — análisis {datos['fecha_analisis']}. "
                       "Regenerar con tools/analizar_cupos_bd.py y re-ejecutar este setup."]],
              range_name="E{}".format(len(resumen) + 2),
              value_input_option="USER_ENTERED")

    sh.batch_update({"requests": [
        {"updateSheetProperties": {"properties": {
            "sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount"}},
        {"repeatCell": {"range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat"}},
        {"updateDimensionProperties": {"range": {"sheetId": ws.id, "dimension": "COLUMNS",
                                                 "startIndex": 1, "endIndex": 2},
                                       "properties": {"pixelSize": 420}, "fields": "pixelSize"}},
    ]})
    print(f"  {TAB_CUPOS} lista: {len(filas) - 1} clases con cupo, resumen por área")
    return ws


def construir_zoom_stats(sh):
    filas_helper = FILAS_ASIST + 5
    ws = recrear(sh, TAB_STATS, filas_helper, 21)

    q = f"'{TAB_ASIST}'"
    # Helpers R:U — aplanan ZOOM-ASISTANCE con % numérico y semana ISO
    pct = ("=ARRAYFORMULA(IF({q}!H2:H=\"\",, IF(ISNUMBER({q}!H2:H), {q}!H2:H*100, "
           "IFERROR(VALUE(SUBSTITUTE({q}!H2:H,\"%\",\"\"))))))").format(q=q)
    semana = ("=ARRAYFORMULA(IF(S2:S=\"\",, IFERROR("
              "IF(ISNUMBER(S2:S), YEAR(S2:S)&\"-S\"&TEXT(ISOWEEKNUM(S2:S),\"00\"), "
              "YEAR(DATEVALUE(LEFT(S2:S,10)))&\"-S\"&TEXT(ISOWEEKNUM(DATEVALUE(LEFT(S2:S,10))),\"00\")"
              "),\"\")))")

    ws.update(values=[["curso", "fecha", "pct_num", "semana"]], range_name="R1",
              value_input_option="USER_ENTERED")
    ws.update(values=loc_filas([[f"=ARRAYFORMULA({q}!F2:F)", f"=ARRAYFORMULA({q}!G2:G)", pct, semana]]),
              range_name="R2", value_input_option="USER_ENTERED")

    # ---- Tabla por sesión (A:I) ----
    ws.update(values=[["📊 POR SESIÓN — cada clase dictada (se actualiza sola con cada toma de asistencia)"]],
              range_name="A1", value_input_option="USER_ENTERED")
    ws.update(values=[["Semana", "Curso", "Fecha", "Conectados", "Cupo", "Conexión",
                       "% del cupo", "Prom. % estancia", f"Alumnos <{UMBRAL}%"]],
              range_name="A2", value_input_option="USER_ENTERED")
    # En es_ES el separador de columnas dentro de {arrays} es "\" (no coma)
    ws.update(values=loc_filas([["=IFERROR(SORT(UNIQUE(FILTER({$U$2:$U\\$R$2:$R\\$S$2:$S}, $R$2:$R<>\"\")), 3, FALSE),)"]]),
              range_name="A3", value_input_option="USER_ENTERED")

    filas_sesion = []
    for i in range(3, FILAS_SESIONES + 3):
        filas_sesion.append([
            f"=IF($B{i}=\"\",,COUNTIFS($R:$R,$B{i},$S:$S,$C{i}))",
            (f"=IF($B{i}=\"\",,IFERROR(VLOOKUP($B{i},{TAB_CUPOS}!$B:$C,2,FALSE),"
             f"IFERROR(INDEX({TAB_CUPOS}!$C:$C,MATCH($B{i},{TAB_CUPOS}!$D:$D,0)),\"—\")))"),
            (f"=IF($B{i}=\"\",,IF(ISNUMBER($E{i}),"
             f"$D{i}&\" de \"&$E{i}&\" estudiantes\","
             f"$D{i}&\" conectados (clase sin cupo en {TAB_CUPOS})\"))"),
            f"=IF(ISNUMBER($E{i}),ROUND($D{i}/$E{i}*100)&\"%\",\"\")",
            f"=IF($B{i}=\"\",,ROUND(AVERAGEIFS($T:$T,$R:$R,$B{i},$S:$S,$C{i}),1)&\"%\")",
            f"=IF($B{i}=\"\",,COUNTIFS($R:$R,$B{i},$S:$S,$C{i},$T:$T,\"<{UMBRAL}\"))",
        ])
    ws.update(values=loc_filas(filas_sesion), range_name=f"D3:I{FILAS_SESIONES + 2}",
              value_input_option="USER_ENTERED")

    # ---- Tabla por semana (K:O) ----
    ws.update(values=[["📅 POR SEMANA (semana ISO)"]], range_name="K1",
              value_input_option="USER_ENTERED")
    ws.update(values=[["Semana", "Clases dictadas", "Conexiones totales",
                       "Prom. conectados por clase", "Prom. % estancia"]],
              range_name="K2", value_input_option="USER_ENTERED")
    ws.update(values=loc_filas([["=IFERROR(SORT(UNIQUE(FILTER($U$2:$U,$U$2:$U<>\"\")),1,FALSE),)"]]),
              range_name="K3", value_input_option="USER_ENTERED")
    filas_semana = []
    for i in range(3, FILAS_SEMANAS + 3):
        filas_semana.append([
            f"=IF($K{i}=\"\",,COUNTA(UNIQUE(FILTER($R$2:$R&\"§\"&$S$2:$S,$U$2:$U=$K{i}))))",
            f"=IF($K{i}=\"\",,COUNTIF($U:$U,$K{i}))",
            f"=IF($K{i}=\"\",,ROUND($M{i}/$L{i},1))",
            f"=IF($K{i}=\"\",,ROUND(AVERAGEIFS($T:$T,$U:$U,$K{i}),1)&\"%\")",
        ])
    ws.update(values=loc_filas(filas_semana), range_name=f"L3:O{FILAS_SEMANAS + 2}",
              value_input_option="USER_ENTERED")

    fin_sesion = FILAS_SESIONES + 2
    rojo_pct = (f"=AND($G3<>\"\", IFERROR(VALUE(SUBSTITUTE($G3,\"%\",\"\")),100)<{UMBRAL})")
    rojo_estancia = (f"=AND($H3<>\"\", IFERROR(VALUE(SUBSTITUTE($H3,\"%\",\"\")),100)<{UMBRAL})")
    naranja_alumnos = "=AND(ISNUMBER($I3),$I3>0)"
    requests = [
        {"updateSheetProperties": {"properties": {
            "sheetId": ws.id, "gridProperties": {"frozenRowCount": 2}},
            "fields": "gridProperties.frozenRowCount"}},
        {"repeatCell": {"range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 2},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat"}},
        # Columnas helper ocultas
        {"updateDimensionProperties": {"range": {"sheetId": ws.id, "dimension": "COLUMNS",
                                                 "startIndex": 17, "endIndex": 21},
                                       "properties": {"hiddenByUser": True},
                                       "fields": "hiddenByUser"}},
        {"updateDimensionProperties": {"range": {"sheetId": ws.id, "dimension": "COLUMNS",
                                                 "startIndex": 1, "endIndex": 2},
                                       "properties": {"pixelSize": 380}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": ws.id, "dimension": "COLUMNS",
                                                 "startIndex": 5, "endIndex": 6},
                                       "properties": {"pixelSize": 220}, "fields": "pixelSize"}},
        # La fecha de sesión llega como serial desde UNIQUE({...}) — formatearla
        {"repeatCell": {"range": {"sheetId": ws.id, "startRowIndex": 2, "endRowIndex": fin_sesion,
                                  "startColumnIndex": 2, "endColumnIndex": 3},
                        "cell": {"userEnteredFormat": {"numberFormat": {
                            "type": "DATE_TIME", "pattern": "yyyy-mm-dd hh:mm"}}},
                        "fields": "userEnteredFormat.numberFormat"}},
        regla_formula(ws.id, 2, fin_sesion, 6, 7, rojo_pct,
                      color("#f4c7c3"), color("#990000"), 0),
        regla_formula(ws.id, 2, fin_sesion, 7, 8, rojo_estancia,
                      color("#f4c7c3"), color("#990000"), 1),
        regla_formula(ws.id, 2, fin_sesion, 8, 9, naranja_alumnos,
                      color("#fce8b2"), color("#7f6000"), 2),
    ]
    sh.batch_update({"requests": requests})
    print(f"  {TAB_STATS} lista: por sesión ({FILAS_SESIONES} filas) + por semana ({FILAS_SEMANAS} filas)")
    return ws


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-migrar", action="store_true",
                        help="No copiar las filas existentes de H3Test")
    args = parser.parse_args()

    if not CUPOS_JSON.exists():
        sys.exit(f"Falta {CUPOS_JSON} — ejecutar antes tools/analizar_cupos_bd.py")

    creds = Credentials.from_service_account_file(
        str(CRED), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)

    print(f"Spreadsheet: {sh.title}")
    construir_zoom_asistance(sh, migrar=not args.sin_migrar)
    construir_cupos(sh)
    construir_zoom_stats(sh)
    print("Setup completo.")


if __name__ == "__main__":
    main()
