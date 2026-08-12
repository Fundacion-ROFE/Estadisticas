# -*- coding: utf-8 -*-
"""
cargar_historico_2019_2022_jc.py — "Jóvenes Creativos única tabla.xlsx" (consolidado
oficial, ver docs/procesos/plan-enriquecimiento-final-2026-08-12.md) → participants +
curso-sello/retiros en Supabase, para JC 2019-2022 (años que Q10 nunca exportó).

Mismo patrón YA aprobado por el usuario el 2026-08-04 para el hueco de 2023
(cargar_bd2023_jc.py --crear-nuevos): un curso "sello" por año representa la selección
sin fingir detalle de materia que la fuente no tiene. Diferencia con ese precedente: aquí
la fuente SÍ distingue estado=SELECCIONADO (culminante) vs RETIRADO, así que:
  - SELECCIONADO → participant + enrollment en el curso sello del año (avance=100,
    completado) → v_gui_personas los cuenta vía enroll_resumen (igual que cualquier
    matriculado real).
  - RETIRADO → participant + fila en `retiros` (SIN enrollment) → v_gui_personas los
    recoge por la rama de reconciliación ya construida en la migración 043
    (2026-08-12, "retirados de cohortes cerradas... avance NULL") — cero cambios de vista
    necesarios, reusa exactamente el mecanismo que ya existe.

Filtro de privacidad (mismo criterio que la etapa de enriquecimiento, decisión del
usuario 2026-08-12): SOLO estado ∈ {SELECCIONADO, RETIRADO} — se EXCLUYEN a propósito
NO SELECCIONADO y REVOCADO (nunca fueron aceptados al programa).

Verificado 2026-08-12: los conteos por año (25/100/90/300 = SELECCIONADO+RETIRADO) cuadran
EXACTOS con el canon ya vigente en `cohorte_historico` (cargado 2026-08-11 desde el mismo
consolidado oficial) — cero riesgo de reconciliación.

Modo por defecto: SOLO REPORTE (no escribe). Pasar --aplicar para ejecutar.

Uso:
    python cargar_historico_2019_2022_jc.py             # reporte
    python cargar_historico_2019_2022_jc.py --aplicar    # crea participants + sello/retiros
"""

import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_XLSX = (r"C:\Users\EstudiantesJC\Downloads\COMPLETE-ORDEN-INFORMATION"
             r"\Jóvenes Creativos única tabla.xlsx")

sys.path.insert(0, DIRECTORIO_SCRIPT)
from enriquecimiento_helper import cargar_hoja  # noqa: E402

USER_AGENT = "panel-datos-etl/1.0"
ANIOS = ("2019", "2020", "2021", "2022")
ESTADOS_INCLUIDOS = {"SELECCIONADO", "RETIRADO"}
FUENTE = "jc_historico_2019_2022_unica_tabla"

# Mismo criterio que cargar_bd2023_jc.py:MAPA_GRUPO — reusado tal cual (las 5 ciudades de
# este subconjunto ya están todas cubiertas).
MAPA_GRUPO = {
    "MEDELLIN": "MED", "ENVIGADO": "MED", "SABANETA": "MED", "ITAGUI": "MED",
    "CALI": "CAL",
    "BARRANQUILLA": "BAQ",
    "BOGOTA DC": "BOG", "BOGOTA": "BOG",
    "CARTAGENA DE INDIAS": "CTG", "CARTAGENA": "CTG",
    "PAYSANDU": "UY", "GUICHON": "UY", "GUICHN": "UY", "FRAY BENTOS": "UY", "QUEBRACHO": "UY",
}

# participants.tipo_vivienda es un ENUM (vivienda_type: arrendado|familiar|propia|otro) —
# BUG encontrado 2026-08-12 en la primera corrida: se mandaba el texto crudo de la fuente
# ("Propia"/"Familiar"/"Arrendada") y Postgres rechazaba el INSERT completo (89 personas de
# 2021 fallaron, ninguna se creó). Mapeo verificado contra el enum real en Supabase.
MAPA_VIVIENDA = {"PROPIA": "propia", "FAMILIAR": "familiar", "ARRENDADA": "arrendado",
                 "ARRENDADO": "arrendado"}


def normalizar_vivienda(valor):
    if not valor:
        return None
    return MAPA_VIVIENDA.get(str(valor).strip().upper(), "otro")


def log(msg: str) -> None:
    print(f"[historico-jc-2019-2022] {msg}", flush=True)


def normalizar_ciudad(valor):
    if not valor:
        return None
    tabla = str.maketrans("ÁÉÍÓÚÑÜáéíóúñü", "AEIOUNUaeiounu")
    limpio = valor.translate(tabla).upper()
    limpio = re.sub(r"[^A-Z0-9 ]", "", limpio)
    return re.sub(r"\s+", " ", limpio).strip() or None


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


def req(url_base, key, metodo, ruta, cuerpo=None, prefer=""):
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json", "User-Agent": USER_AGENT}
    if prefer:
        headers["Prefer"] = prefer
    r = urllib.request.Request(url_base.rstrip("/") + "/rest/v1" + ruta, method=metodo,
                                headers=headers,
                                data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            datos = resp.read()
            return resp.status, json.loads(datos) if datos else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: "
                            f"{e.read().decode(errors='replace')[:500]}") from None


def get_todo(url, key, ruta, page=1000):
    filas, offset = [], 0
    sep = "&" if "?" in ruta else "?"
    while True:
        _, lote = req(url, key, "GET", f"{ruta}{sep}limit={page}&offset={offset}")
        filas.extend(lote or [])
        if not lote or len(lote) < page:
            return filas
        offset += page


def leer_fuente():
    _cols, filas = cargar_hoja(RUTA_XLSX, sheet="Hoja1")
    sub = [f for f in filas
           if str(f.get("anio")) in ANIOS and f.get("estado") in ESTADOS_INCLUIDOS]

    vistos, limpias, sin_cedula, duplicadas = set(), [], 0, 0
    for f in sub:
        cedula = re.sub(r"\D", "", str(f.get("documento_norm") or ""))
        if not cedula:
            sin_cedula += 1
            continue
        anio = str(f["anio"])
        clave = (cedula, anio)
        if clave in vistos:
            duplicadas += 1
            continue
        vistos.add(clave)

        ciudad_raw = (f.get("ciudad") or "").strip() or None
        clave_ciudad = normalizar_ciudad(ciudad_raw)
        email = (f.get("correo_norm") or "").strip().lower() or None
        limpias.append({
            "cedula": cedula,
            "anio": anio,
            "nombre": f"{(f.get('nombres') or '').strip()} {(f.get('apellidos') or '').strip()}".strip()
                      or "(sin nombre)",
            "email": email,
            "ciudad_raw": ciudad_raw,
            "grupo_ciudad": MAPA_GRUPO.get(clave_ciudad) if clave_ciudad else None,
            "genero": (f.get("genero") or "").strip() or None,
            "edad": f.get("edad_reportada"),
            "estrato": f.get("estrato"),
            "tipo_vivienda": normalizar_vivienda(f.get("tipo_vivienda")),
            "retirado": f["estado"] == "RETIRADO",
        })
    log(f"Fuente: {len(sub)} filas (estado∈SELECCIONADO/RETIRADO) → {len(limpias)} limpias "
        f"(sin_cedula={sin_cedula} duplicadas={duplicadas})")
    return limpias


def asegurar_curso_sello(url, key, anio):
    nombre = f"Seleccionados {anio} (consolidado histórico, sin curso específico)"
    _, existentes = req(url, key, "GET",
                         f"/courses?nombre=eq.{urllib.parse.quote(nombre)}"
                         f"&cohorte=eq.{anio}&programa=eq.jc&select=id")
    if existentes:
        return existentes[0]["id"]
    _, creado = req(url, key, "POST", "/courses",
                     cuerpo={"nombre": nombre, "cohorte": anio, "programa": "jc",
                             "estado": "completado"},
                     prefer="return=representation")
    return creado[0]["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true", help="ejecuta las escrituras (default: solo reporte)")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan credenciales Supabase")
        return 1
    if not os.path.isfile(RUTA_XLSX):
        log(f"ERROR: no existe la fuente: {RUTA_XLSX}")
        return 1

    filas = leer_fuente()
    por_anio = Counter(f["anio"] for f in filas)
    por_estado = Counter("RETIRADO" if f["retirado"] else "SELECCIONADO" for f in filas)
    log(f"Por año: {dict(sorted(por_anio.items()))}")
    log(f"Por estado: {dict(por_estado)}")

    sin_grupo = [f for f in filas if f["ciudad_raw"] and not f["grupo_ciudad"]]
    if sin_grupo:
        log(f"ADVERTENCIA: {len(sin_grupo)} filas con ciudad sin mapear a grupo (se cargan igual, "
            f"grupo_ciudad=NULL):")
        for f in sin_grupo[:10]:
            log(f"  cedula={f['cedula']} ciudad={f['ciudad_raw']!r}")

    log("Descargando participants existentes (q10_id) desde Supabase...")
    existentes = get_todo(url, key, "/participants?select=id,q10_id&q10_id=not.is.null")
    ids_por_cedula = {p["q10_id"]: p["id"] for p in existentes if p.get("q10_id")}
    ya_en_supabase = sum(1 for f in filas if f["cedula"] in ids_por_cedula)
    log(f"De las {len(filas)} personas de la fuente, {ya_en_supabase} YA existen en Supabase "
        f"(se reusa su participant_id, no se duplica) y {len(filas) - ya_en_supabase} son nuevas.")

    if not args.aplicar:
        log("Modo reporte (sin --aplicar): no se escribió nada en Supabase.")
        return 0

    cursos_sello = {}
    creados = reusados = enrollments_creados = retiros_creados = fallos = 0

    for f in filas:
        try:
            participant_id = ids_por_cedula.get(f["cedula"])
            if participant_id:
                reusados += 1
            else:
                _, creado = req(url, key, "POST", "/participants", cuerpo={
                    "q10_id": f["cedula"], "nombre": f["nombre"], "email": f["email"],
                    "ciudad": f["ciudad_raw"], "grupo_ciudad": f["grupo_ciudad"],
                    "genero": f["genero"], "edad": f["edad"], "estrato": f["estrato"],
                    "tipo_vivienda": f["tipo_vivienda"], "source_system": FUENTE,
                }, prefer="return=representation")
                participant_id = creado[0]["id"]
                ids_por_cedula[f["cedula"]] = participant_id
                creados += 1

            if f["retirado"]:
                _, ya = req(url, key, "GET",
                            f"/retiros?participant_id=eq.{participant_id}"
                            f"&programa=eq.jc&cohorte=eq.{f['anio']}&select=id")
                if not ya:
                    req(url, key, "POST", "/retiros", cuerpo={
                        "participant_id": participant_id, "cedula": f["cedula"],
                        "programa": "jc", "cohorte": f["anio"],
                        "motivo": "Consolidado histórico oficial JC — motivo no registrado por año",
                        "fuente": FUENTE,
                    })
                    retiros_creados += 1
            else:
                if f["anio"] not in cursos_sello:
                    cursos_sello[f["anio"]] = asegurar_curso_sello(url, key, f["anio"])
                curso_id = cursos_sello[f["anio"]]
                _, ya = req(url, key, "GET",
                            f"/enrollments?participant_id=eq.{participant_id}"
                            f"&course_id=eq.{curso_id}&select=id")
                if not ya:
                    req(url, key, "POST", "/enrollments", cuerpo={
                        "participant_id": participant_id, "course_id": curso_id,
                        "porcentaje_avance": 100, "estado": "completado",
                    })
                    enrollments_creados += 1
        except RuntimeError as e:
            fallos += 1
            log(f"ERROR cedula={f['cedula']} anio={f['anio']}: {e}")

    log(f"RESUMEN --aplicar: participants_creados={creados} reusados={reusados} "
        f"enrollments_sello_creados={enrollments_creados} retiros_creados={retiros_creados} "
        f"fallos={fallos} estado={'exito' if fallos == 0 else 'con_errores'}")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
