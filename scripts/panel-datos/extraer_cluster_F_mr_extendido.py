# -*- coding: utf-8 -*-
"""
extraer_cluster_F_mr_extendido.py
=================================
Clúster F — enriquecimiento Mujeres ROFÉ (campos extendidos del perfil).

Extrae de la "BD-Mujeres ROFÉ 2026 - General.csv" los campos del perfil de las
mujeres de MR que HOY NO están en Supabase, y los ancla a la persona conocida
(canon) usando el Matcher compartido (prioridad cédula > correo > nombre).

Match: la columna `Numero de identificacion` es la cédula y `Correo` el email,
así que el match por cédula debería ser altísimo.

Campos objetivo (normalizados) → columna de origen en el CSV:
  direccion              ← "Dirección"
  departamento           ← "departamento con cc"
  grupo_etnico           ← "Grupo étnico"
  tipo_discapacidad      ← "Tipo discapacidad"
  sostenimiento          ← "Sostenimiento"
  canal_adquisicion      ← "¿Por dónde conociste Mujeres Rofé?"
  presentacion_personal  ← "Presentación personal"
  hobbies                ← "Hobbies"
  ingresos_familiares    ← "Ingresos familiares"
  personas_nucleo        ← "Personas del nucleo"
  codigo_promocional     ← "Codigo promocional"
  le_ayudaron_a_llenar   ← "¿Le ayudaron a llenar el formulario?"

NO se incluyen contraseña/usuario/celular (ya los tenemos o son sensibles sin
valor analítico). Valores basura ("N/A", "null", "#N/A", "#REF!", vacío) → se omiten.

Salidas (PII → tools/, gitignoreado; NUNCA a docs/ ni a Supabase):
  - tools/enriquecimiento/F_mr_extendido.json  (lista de {canon, cedula_fuente,
    campo, valor, metodo_match}; fuente fija = ese CSV)
  - tools/enriquecimiento/F_RESUMEN.md

Es SOLO LECTURA sobre el CSV. No hay red (salvo el roster ya generado en tools/).
Reutilizable / idempotente.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enriquecimiento_helper import Matcher, cargar_hoja  # noqa: E402

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #
FUENTE = Path(
    r"C:\Users\EstudiantesJC\Downloads\COMPLETE-ORDEN-INFORMATION"
    r"\Mujeres-Rofe-All-Data\BD-Mujeres ROFÉ 2026 - General.csv"
)
FUENTE_ETIQUETA = "BD-Mujeres ROFÉ 2026 - General.csv"

OUT_DIR = Path(
    r"C:\Users\EstudiantesJC\downloads\admin-usable\tools\enriquecimiento"
)

COL_CEDULA = "Numero de identificacion"
COL_EMAIL = "Correo"
COL_NOMBRE = "Nombre Completo"

# campo_normalizado -> columna en el CSV
CAMPOS = {
    "direccion": "Dirección",
    "departamento": "departamento con cc",
    "grupo_etnico": "Grupo étnico",
    "tipo_discapacidad": "Tipo discapacidad",
    "sostenimiento": "Sostenimiento",
    "canal_adquisicion": "¿Por dónde conociste Mujeres Rofé?",
    "presentacion_personal": "Presentación personal",
    "hobbies": "Hobbies",
    "ingresos_familiares": "Ingresos familiares",
    "personas_nucleo": "Personas del nucleo",
    "codigo_promocional": "Codigo promocional",
    "le_ayudaron_a_llenar": "¿Le ayudaron a llenar el formulario?",
}

# Valores basura → se omiten (comparación en minúsculas, sin espacios extremos).
BASURA = {"", "n/a", "na", "n/n", "null", "none", "#n/a", "#ref!", "#value!",
          "#name?", "#div/0!", "-", "."}


def limpiar(v) -> str:
    """Devuelve el valor limpio, o "" si es basura / vacío."""
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() in BASURA:
        return ""
    return s


def main():
    if not FUENTE.exists():
        sys.exit(f"[F] ERROR: no existe la fuente: {FUENTE}")

    m = Matcher.desde_archivo()
    cols, filas = cargar_hoja(str(FUENTE))

    # Validar que las columnas esperadas existan (por si cambia el archivo).
    faltan_cols = [c for c in ([COL_CEDULA, COL_EMAIL, COL_NOMBRE] + list(CAMPOS.values()))
                   if c not in cols]
    if faltan_cols:
        print(f"[F] AVISO: columnas no encontradas en el CSV: {faltan_cols}")

    payload = []
    n_filas = 0
    n_con_cedula_fuente = 0
    metodo_por_persona = {}        # canon -> metodo (el primero con que se ancló)
    canon_vistos = set()
    cobertura = Counter()          # campo -> nº de personas (canon) con valor
    cobertura_canon = defaultdict(set)  # campo -> {canon}
    ejemplos = {}                  # campo -> valor de ejemplo (primero no vacío)

    for fila in filas:
        n_filas += 1
        ced_fuente = limpiar(fila.get(COL_CEDULA))
        if ced_fuente:
            n_con_cedula_fuente += 1
        canon, metodo = m.match(
            cedula=fila.get(COL_CEDULA),
            email=fila.get(COL_EMAIL),
            nombre=fila.get(COL_NOMBRE),
        )
        if not canon:
            continue
        canon_vistos.add(canon)
        metodo_por_persona.setdefault(canon, metodo)

        for campo, col in CAMPOS.items():
            valor = limpiar(fila.get(col))
            if not valor:
                continue
            # Solo el primer valor por (canon, campo): el archivo trae 1 fila/persona,
            # pero por robustez ante duplicados nos quedamos con el primero no vacío.
            if canon in cobertura_canon[campo]:
                continue
            cobertura_canon[campo].add(canon)
            cobertura[campo] += 1
            ejemplos.setdefault(campo, valor)
            payload.append({
                "canon": canon,
                "cedula_fuente": ced_fuente,
                "campo": campo,
                "valor": valor,
                "metodo_match": metodo,
                "fuente": FUENTE_ETIQUETA,
            })

    # ---- Escritura payload ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "F_mr_extendido.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- Métricas de match ----
    n_personas = len(canon_vistos)
    metodos = Counter(metodo_por_persona.values())

    escribir_resumen(n_filas, n_con_cedula_fuente, n_personas, metodos,
                     cobertura, ejemplos, len(payload), faltan_cols)

    # ---- Reporte a consola ----
    print("=== CLÚSTER F — MR CAMPOS EXTENDIDOS ===")
    print(f"Filas leídas del CSV: {n_filas}")
    print(f"Filas con cédula en la fuente: {n_con_cedula_fuente}")
    print(f"Mujeres (canon) con match: {n_personas}")
    if n_personas:
        print("Match por método (personas):")
        for met, n in metodos.most_common():
            print(f"   {met:8} {n:5}  ({100*n/n_personas:.1f}%)")
    print(f"Registros en payload: {len(payload)}")
    print("Cobertura por campo (nº de personas con valor):")
    for campo in CAMPOS:
        n = cobertura.get(campo, 0)
        pct = (100 * n / n_personas) if n_personas else 0
        print(f"   {campo:24} {n:5}  ({pct:.1f}%)")
    print(f"\nSalidas en: {OUT_DIR}")


def escribir_resumen(n_filas, n_con_cedula_fuente, n_personas, metodos,
                     cobertura, ejemplos, n_payload, faltan_cols):
    L = []
    L.append("# Clúster F — Mujeres ROFÉ: campos extendidos del perfil\n")
    L.append(f"Fuente: `{FUENTE_ETIQUETA}` (solo lectura). "
             "Match por cédula/correo/nombre contra el roster de identidad.\n")
    L.append("## Resultado global\n")
    L.append(f"- Filas leídas del CSV: **{n_filas}**")
    L.append(f"- Filas con cédula en la fuente: **{n_con_cedula_fuente}**")
    L.append(f"- Mujeres (canon) con match: **{n_personas}**")
    L.append(f"- Registros (canon, campo) en el payload: **{n_payload}**\n")
    if faltan_cols:
        L.append(f"> AVISO: columnas no encontradas en el CSV: {faltan_cols}\n")

    L.append("## Match por método (personas)\n")
    L.append("| Método | Personas | % |")
    L.append("|---|---|---|")
    for met, n in metodos.most_common():
        pct = (100 * n / n_personas) if n_personas else 0
        L.append(f"| {met} | {n} | {pct:.1f}% |")
    L.append("")

    L.append("## Cobertura por campo\n")
    L.append("Nº de mujeres (canon) con valor no-basura en cada campo.\n")
    L.append("| Campo | Personas con valor | % de las matcheadas |")
    L.append("|---|---|---|")
    for campo in CAMPOS:
        n = cobertura.get(campo, 0)
        pct = (100 * n / n_personas) if n_personas else 0
        L.append(f"| {campo} | {n} | {pct:.1f}% |")
    L.append("")

    L.append("## Ejemplos de valor por campo\n")
    L.append("| Campo | Ejemplo |")
    L.append("|---|---|")
    for campo in CAMPOS:
        ej = str(ejemplos.get(campo, "—")).replace("\n", " ").replace("|", "/")
        if len(ej) > 80:
            ej = ej[:77] + "..."
        L.append(f"| {campo} | {ej} |")
    L.append("")

    (OUT_DIR / "F_RESUMEN.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
