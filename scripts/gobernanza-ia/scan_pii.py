"""
scan_pii.py — Barrido de PII sin pseudonimizar antes de commitear logs de uso de IA.

Reutiliza los mismos patrones de detección que docs/pseudonimizador/index.html (regex de
columna + regex de contenido) pero aplicados a texto libre (transcripciones), no a
encabezados de Excel.

Uso:
    python scan_pii.py archivo1.md archivo2.md ...     -> exit 0 si limpio, 1 si encontró algo
    python scan_pii.py --dir usuarios-ia/samuel/logs   -> escanea todo el árbol

Regla del proyecto (ver docs/convenciones.md, gotcha "secreto commiteado por error"):
NUNCA imprimir el valor real encontrado. Solo una versión enmascarada + dónde está.
"""

import argparse
import re
import sys
from pathlib import Path

# --- Patrones de contenido (adaptados de la detección del pseudonimizador) ---

PATRONES = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    # cédula/documento colombiano típico: 7-10 dígitos seguidos, no parte de un número mayor
    "cedula_o_documento": re.compile(r"(?<!\d)\d{7,10}(?!\d)"),
    # celular colombiano: 10 dígitos empezando por 3, o con prefijo internacional +57
    "celular": re.compile(r"(?<!\d)(?:\+?57)?3\d{9}(?!\d)"),
    # credenciales en texto plano cerca de estas palabras clave (2026-07-01, mismo hallazgo
    # que el pseudonimizador tras la auditoría de seguridad externa)
    "credencial_en_texto_plano": re.compile(
        r"(?i)\b(contrase[ñn]a|password|clave|credencial|api[_-]?key|secret|token)\s*[:=]\s*\S+"
    ),
}

# Palabras clave que, si aparecen justo antes de un número, suben la confianza de que es PII
# real y no un ID de curso/factura/etc. (mismo criterio que la detección por nombre de columna
# del pseudonimizador: cédula, identificación, celular, teléfono, documento).
CONTEXTO_ALTA_CONFIANZA = re.compile(
    r"(?i)\b(c[ée]dula|identificaci[óo]n|documento|celular|tel[ée]fono|nombre completo)\b"
)


def enmascarar(valor: str) -> str:
    """Nunca devolver el valor real — solo largo + primer/último caracter."""
    if len(valor) <= 2:
        return "*" * len(valor)
    return valor[0] + "*" * (len(valor) - 2) + valor[-1]


def escanear_texto(texto: str, origen: str) -> list[str]:
    """Devuelve una lista de hallazgos enmascarados (vacía si está limpio)."""
    hallazgos = []
    for etiqueta, patron in PATRONES.items():
        for m in patron.finditer(texto):
            valor = m.group(0)
            linea = texto.count("\n", 0, m.start()) + 1
            hallazgos.append(
                f"{origen}:{linea} — posible {etiqueta} ({enmascarar(valor)})"
            )
    return hallazgos


def escanear_archivo(path: Path) -> list[str]:
    try:
        texto = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [f"{path} — no se pudo leer ({e}); tratar como no-limpio hasta revisar a mano"]
    return escanear_texto(texto, str(path))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archivos", nargs="*", help="Archivos puntuales a escanear")
    ap.add_argument("--dir", help="Escanear recursivamente todos los .md/.txt de este directorio")
    args = ap.parse_args()

    objetivos: list[Path] = [Path(a) for a in args.archivos]
    if args.dir:
        objetivos += sorted(Path(args.dir).rglob("*.md")) + sorted(Path(args.dir).rglob("*.txt"))

    if not objetivos:
        print("Nada que escanear (pasa archivos o --dir).", file=sys.stderr)
        return 0

    todos_hallazgos = []
    for path in objetivos:
        if not path.exists():
            continue
        todos_hallazgos.extend(escanear_archivo(path))

    if todos_hallazgos:
        print("BLOQUEADO — posible PII sin pseudonimizar:", file=sys.stderr)
        for h in todos_hallazgos:
            print(f"  - {h}", file=sys.stderr)
        print(
            "\nNo se hace commit/push de estos archivos. Pseudonimizar con "
            "docs/pseudonimizador/index.html antes de reintentar, o confirmar que es un "
            "falso positivo (ID de curso, número de proceso, etc.) y ajustar el patrón aquí "
            "si se repite.",
            file=sys.stderr,
        )
        return 1

    print(f"OK — {len(objetivos)} archivo(s) sin hallazgos.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
