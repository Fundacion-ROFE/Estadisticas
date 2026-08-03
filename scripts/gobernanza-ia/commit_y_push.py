"""
commit_y_push.py — Snapshot de usuarios-ia/ (o de una sola persona) al repo de gobernanza.

Flujo:
1. Detecta qué archivos cambiaron dentro de usuarios-ia/ (git status --porcelain), o solo
   dentro de usuarios-ia/<usuario>/ si se pasa --usuario.
2. Excluye _plantilla/ (nunca contiene datos reales).
3. Corre scan_pii.py sobre cada archivo modificado en logs/.
4. Si CUALQUIER archivo falla el scan: no se commitea nada de ese ciclo, se imprime
   alerta (pensada para conectarse a Telegram, ver más abajo) y se sale con código != 0.
5. Si todo pasa: commit + push. Nunca falla en silencio (mismo estándar mínimo que
   cualquier workflow n8n del proyecto — ver docs/convenciones.md).

Dos formas de disparar este script, según dónde vive la instancia:
- **Sin --usuario** (todo el árbol de una vez): pensado para un nodo Execute Command de un
  workflow n8n con Schedule, solo tiene sentido si todas las carpetas de usuarios-ia/ viven
  en la misma máquina que corre n8n (hoy, la de Samuel). NO configurado ni programado
  todavía (ver docs/procesos/gobernanza-contexto-ia.md, sección Pendiente).
- **Con --usuario <nombre>** (solo esa carpeta): pensado para un hook `Stop` de Claude Code
  en el `settings.json` local de esa persona, que corre al final de cada sesión en SU propia
  máquina — es el mecanismo real para Lina/Rocío/Cristian, cuyas instancias no corren en la
  máquina de Samuel. Comando exacto documentado en docs/procesos/gobernanza-contexto-ia.md.

Requiere que el repo ya tenga (una sola vez, igual que cualquier repo nuevo en esta red):
    git config --local http.sslBackend schannel
    git config --local credential.interactive never
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]  # scripts/gobernanza-ia/ -> raíz del repo
USUARIOS_DIR = RAIZ / "usuarios-ia"
SCAN_SCRIPT = Path(__file__).resolve().parent / "scan_pii.py"


def git(*args, timeout=180) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=RAIZ, capture_output=True, text=True, timeout=timeout
    )


def archivos_modificados_en_usuarios_ia(usuario: str | None) -> list[str]:
    ruta_objetivo = f"usuarios-ia/{usuario}" if usuario else "usuarios-ia"
    r = git("status", "--porcelain", "--", ruta_objetivo)
    if r.returncode != 0:
        print(f"git status falló: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    archivos = []
    for linea in r.stdout.splitlines():
        # formato "XY ruta" — nos quedamos con la ruta, sin importar el estado exacto
        ruta = linea[3:].strip()
        if ruta and "_plantilla/" not in ruta:
            archivos.append(ruta)
    return archivos


def es_log(ruta: str) -> bool:
    return "/logs/" in ruta.replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--usuario",
        help="Acotar el commit/push a usuarios-ia/<usuario> únicamente (uso: hook local "
        "por persona). Sin este flag, se sube todo usuarios-ia/ de una vez.",
    )
    args = ap.parse_args()

    if args.usuario and not (USUARIOS_DIR / args.usuario).is_dir():
        print(f"No existe usuarios-ia/{args.usuario}/ — nada que pushear.", file=sys.stderr)
        return 1

    ruta_objetivo = f"usuarios-ia/{args.usuario}" if args.usuario else "usuarios-ia"
    archivos = archivos_modificados_en_usuarios_ia(args.usuario)
    if not archivos:
        print(f"Sin cambios en {ruta_objetivo} — nada que pushear.", file=sys.stderr)
        return 0

    logs_a_escanear = [a for a in archivos if es_log(a)]
    if logs_a_escanear:
        r = subprocess.run(
            [sys.executable, str(SCAN_SCRIPT), *logs_a_escanear],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=60,
        )
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        if r.returncode != 0:
            print(
                "\nALERTA: push cancelado — scan_pii.py encontró PII sin pseudonimizar. "
                "Ningún archivo de este ciclo se subió. Revisar arriba, pseudonimizar y "
                "reintentar. (Conectar esta salida a Telegram vía n8n, mismo patrón que "
                "alerta-fallo-workflow.)",
                file=sys.stderr,
            )
            return 1

    add = git("add", ruta_objetivo)
    if add.returncode != 0:
        print(f"git add falló: {add.stderr}", file=sys.stderr)
        return 1

    sufijo_usuario = f" ({args.usuario})" if args.usuario else ""
    mensaje = f"gobernanza-ia: snapshot automático{sufijo_usuario} {date.today().isoformat()}"
    commit = git("commit", "-m", mensaje)
    if commit.returncode != 0:
        # "nothing to commit" no es un error real (puede pasar si solo cambiaron permisos)
        if "nothing to commit" in commit.stdout.lower():
            print("Sin cambios netos para commitear.", file=sys.stderr)
            return 0
        print(f"git commit falló: {commit.stderr}", file=sys.stderr)
        return 1

    push = git("push", "origin", "HEAD")
    if push.returncode != 0:
        print(f"git push falló: {push.stderr}", file=sys.stderr)
        return 1

    print(f"OK — {len(archivos)} archivo(s) pusheados ({mensaje}).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
