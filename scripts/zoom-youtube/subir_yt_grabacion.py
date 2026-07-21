# -*- coding: utf-8 -*-
"""
Zoom (grabacion en la nube) -> YouTube (clases Mujeres ROFE) o Drive (sesiones NOVA).

Enrutamiento por topic: si contiene "nova" -> MP4 + transcripcion VTT a la carpeta de
Drive NOVA (subcarpeta NOVA-DD-MM-YYYY); TODO lo demas -> YouTube unlisted (decision
2026-07-16: se graba y sube todo; MR_KEYWORDS ya no filtra, solo ETIQUETA el programa
"Mujeres ROFE" vs "Jovenes creaTIvos" en el log y la descripcion del video). El evento
recording.transcript_completed (suscrito en el Marketplace) trae la transcripcion cuando
Zoom la termina (despues del video) y la rama NOVA la agrega a la misma subcarpeta sin
duplicar el MP4; para YouTube ese evento se ignora.

Recibe el payload del webhook `recording.completed` de Zoom (guardado en un archivo JSON
por el workflow n8n antes de llamar este script, para evitar problemas de escapado de
comillas en Execute Command), filtra si es una clase MR por palabras clave del topic
(JC y MR comparten el mismo host `comunicaciones@tocaunavida.org`, no se puede filtrar
por host), descarga el MP4 principal desde Zoom, lo sube a YouTube como `unlisted` y
registra la subida en una pestaña de log en Sheets (idempotente por meeting UUID).

Uso (payload real, desde n8n vía Execute Command -- base64 evita problemas de escapado de
comillas/saltos de línea en el shell de Windows):
  python subir_yt_grabacion.py --payload-b64 <base64 del body JSON del webhook>

Uso (payload real, desde archivo):
  python subir_yt_grabacion.py --payload-file ruta/al/payload.json

Uso (backfill, sin webhook):
  python subir_yt_grabacion.py --meeting-uuid <uuid> --host comunicaciones@tocaunavida.org

Requiere:
  - scripts/zoom-asistencia/.env  (ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET)
  - scripts/zoom-youtube/.env     (YT_OAUTH_CLIENT_ID, YT_OAUTH_CLIENT_SECRET, YT_REFRESH_TOKEN)
  - scripts/q10-consolidacion/credenciales_service_account.json (log en Sheets)
"""
import argparse
import base64
import io
import json
import os
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

BASE = Path(__file__).resolve().parents[2]
ZOOM_ENV = BASE / "scripts" / "zoom-asistencia" / ".env"
YT_ENV = BASE / "scripts" / "zoom-youtube" / ".env"
SA_CRED = BASE / "scripts" / "q10-consolidacion" / "credenciales_service_account.json"

LOG_SHEET_ID = "1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0"  # mismo spreadsheet H3Test
LOG_TAB = "YT-GRABACIONES-LOG"
LOG_HEADERS = ["Fecha", "Topic", "Duracion (min)", "Meeting UUID", "Video URL", "Video ID", "Programa", "Playlist"]

# Desde 2026-07-16 se sube TODO a YouTube (antes era filtro): estas palabras clave de los
# cursos MR (naming inconsistente, ver docs/procesos/zoom-youtube.md) ahora solo deciden
# la ETIQUETA de programa (Mujeres ROFE vs Jovenes creaTIvos) en log y descripcion.
MR_KEYWORDS = [
    "emprend", "ventas", "finanzas", "negocio", "habilidades del ser",
    "estrategias digitales", "mujeres rofe", "mujeres rofé",
]

# Rama NOVA: las sesiones/entrevistas NOVA NO van a YouTube — van a una carpeta de
# Google Drive (MP4 + transcripcion VTT), en una subcarpeta "NOVA-DD-MM-YYYY" por dia.
# La subida usa el MISMO OAuth de comunicaciones@ que YouTube (la service account no
# tiene cuota de almacenamiento en My Drive). Requiere scope drive en YT_REFRESH_TOKEN.
NOVA_KEYWORDS = ["nova"]
NOVA_DRIVE_FOLDER_ID = "18eu7pveWJmvTb_rLPHGVmPZ41PE-zUGV"  # carpeta TEST-16-07-2026
NOVA_LOG_TAB = "NOVA-GRABACIONES-LOG"
NOVA_LOG_HEADERS = ["Fecha", "Topic", "Duracion (min)", "Meeting UUID", "Archivos subidos", "Carpeta URL"]


def _parse_env_file(path: Path) -> dict:
    vals = {}
    if not path.is_file():
        return vals
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


def es_clase_mr(topic: str) -> bool:
    t = (topic or "").lower()
    return any(kw in t for kw in MR_KEYWORDS)


def es_nova(topic: str) -> bool:
    t = (topic or "").lower()
    return any(kw in t for kw in NOVA_KEYWORDS)


def fecha_bogota(start_time_utc: str):
    """'2026-07-16T14:45:10Z' (UTC) -> datetime local Bogota (UTC-5, sin DST)."""
    from datetime import datetime, timedelta
    dt = datetime.strptime(start_time_utc, "%Y-%m-%dT%H:%M:%SZ")
    return dt - timedelta(hours=5)


def obtener_token_zoom(zoom_vals: dict) -> str:
    cid = zoom_vals["ZOOM_CLIENT_ID"]
    csec = zoom_vals["ZOOM_CLIENT_SECRET"]
    acc = zoom_vals["ZOOM_ACCOUNT_ID"]
    req = urllib.request.Request(
        f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={acc}",
        method="POST",
        headers={"Authorization": "Basic " + base64.b64encode(f"{cid}:{csec}".encode()).decode()},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def obtener_grabacion_por_uuid(access_token: str, meeting_uuid: str) -> dict:
    """Fallback para backfill: consulta la grabacion por UUID (doble encode si empieza con /
    o contiene //, mismo gotcha que past_meetings en zoom-asistencia)."""
    uuid_enc = urllib.parse.quote(urllib.parse.quote(meeting_uuid, safe=""), safe="")
    req = urllib.request.Request(
        f"https://api.zoom.us/v2/meetings/{uuid_enc}/recordings",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def elegir_archivo_mp4(recording_files: list) -> dict:
    candidatos = [f for f in recording_files if f.get("file_type") == "MP4"]
    if not candidatos:
        raise ValueError("No hay archivo MP4 en recording_files")
    preferido = next(
        (f for f in candidatos if f.get("recording_type") == "shared_screen_with_speaker_view"),
        None,
    )
    return preferido or max(candidatos, key=lambda f: f.get("file_size", 0))


def descargar_mp4(archivo: dict, access_token: str, download_token: str = None, suffix: str = ".mp4") -> str:
    """Descarga un archivo de grabacion por streaming a un temporal. Retorna la ruta local."""
    url = archivo["download_url"]
    token = download_token or access_token
    sep = "&" if "?" in url else "?"
    url_con_token = f"{url}{sep}access_token={token}"

    fd, ruta = tempfile.mkstemp(suffix=suffix, prefix="zoom_yt_")
    os.close(fd)

    req = urllib.request.Request(url_con_token)
    with urllib.request.urlopen(req, timeout=120) as resp, open(ruta, "wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    return ruta


def _credenciales_oauth(yt_vals: dict):
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=None,
        refresh_token=yt_vals["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=yt_vals["YT_OAUTH_CLIENT_ID"],
        client_secret=yt_vals["YT_OAUTH_CLIENT_SECRET"],
        # Todos los scopes otorgados en el consentimiento (ver obtener_refresh_token.py).
        # Declarar un subconjunto aqui restringiria el access_token refrescado a ese
        # subconjunto (Google permite "down-scoping" en el refresh) y romperia las demas
        # llamadas (playlist a futuro, Drive para NOVA).
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/drive",
        ],
    )


def construir_youtube_client(yt_vals: dict):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_credenciales_oauth(yt_vals))


def construir_drive_client(yt_vals: dict):
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=_credenciales_oauth(yt_vals))


def normalizar_curso(topic: str) -> str:
    """Nombre de playlist = curso: quita el sufijo ' - Sala N' de las breakout rooms
    para que las salas caigan en la playlist del curso madre."""
    import re
    return re.sub(r"\s*-?\s*sala\s*\d+\s*$", "", (topic or "").strip(), flags=re.IGNORECASE).strip()


def asegurar_playlist(youtube, titulo: str) -> str:
    """Busca (o crea, unlisted) una playlist del canal por titulo exacto. Retorna su id."""
    token_pagina = None
    while True:
        res = youtube.playlists().list(part="snippet", mine=True, maxResults=50,
                                       pageToken=token_pagina).execute()
        for pl in res.get("items", []):
            if pl["snippet"]["title"].strip().lower() == titulo.strip().lower():
                return pl["id"]
        token_pagina = res.get("nextPageToken")
        if not token_pagina:
            break
    creada = youtube.playlists().insert(
        part="snippet,status",
        body={"snippet": {"title": titulo},
              "status": {"privacyStatus": "unlisted"}},
    ).execute()
    print(f"Playlist creada: {titulo}")
    return creada["id"]


def agregar_a_playlist(youtube, playlist_id: str, video_id: str, intentos: int = 4):
    """playlistItems.insert falla a veces con 409 SERVICE_UNAVAILABLE transitorio
    (tipico justo despues de crear la playlist) -> reintentar con espera."""
    import time
    for i in range(intentos):
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={"snippet": {"playlistId": playlist_id,
                                  "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
            ).execute()
            return
        except Exception as e:
            if i == intentos - 1:
                raise
            espera = 5 * (i + 1)
            print(f"  playlistItems.insert fallo ({e.__class__.__name__}), reintento en {espera}s...")
            time.sleep(espera)


def asegurar_subcarpeta_nova(drive, fecha_ddmmyyyy: str) -> str:
    """Busca (o crea) la subcarpeta 'NOVA-DD-MM-YYYY' dentro de la carpeta NOVA. Retorna su id."""
    nombre = f"NOVA-{fecha_ddmmyyyy}"
    q = (f"'{NOVA_DRIVE_FOLDER_ID}' in parents and name = '{nombre}' "
         "and mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    res = drive.files().list(q=q, fields="files(id)", pageSize=1).execute()
    if res.get("files"):
        return res["files"][0]["id"]
    carpeta = drive.files().create(
        body={"name": nombre, "mimeType": "application/vnd.google-apps.folder",
              "parents": [NOVA_DRIVE_FOLDER_ID]},
        fields="id",
    ).execute()
    print(f"Subcarpeta creada: {nombre}")
    return carpeta["id"]


def nombres_en_carpeta(drive, folder_id: str) -> set:
    res = drive.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(name)", pageSize=1000,
    ).execute()
    return {f["name"] for f in res.get("files", [])}


def subir_a_drive(drive, folder_id: str, ruta_local: str, nombre: str, mimetype: str) -> str:
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(ruta_local, chunksize=10 * 1024 * 1024, resumable=True, mimetype=mimetype)
    request = drive.files().create(
        body={"name": nombre, "parents": [folder_id]}, media_body=media, fields="id",
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Subiendo a Drive... {int(status.progress() * 100)}%")
    return response["id"]


def subir_video(youtube, ruta_archivo: str, topic: str, fecha: str, etiqueta: str) -> dict:
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": f"{topic} - {fecha}"[:100],
            "description": f"Clase {etiqueta} - {topic}\nFecha: {fecha}",
            "categoryId": "27",  # Education
        },
        "status": {
            "privacyStatus": "unlisted",  # revision humana antes de pasar a publico (PII)
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(ruta_archivo, chunksize=10 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Subiendo... {int(status.progress() * 100)}%")
    return response


def conectar_sheets():
    import gspread
    from google.oauth2.service_account import Credentials

    if not SA_CRED.exists():
        raise FileNotFoundError(f"No encontrado: {SA_CRED}")
    creds = Credentials.from_service_account_file(
        str(SA_CRED), scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)


def asegurar_tab_log(gc, tab=LOG_TAB, headers=LOG_HEADERS):
    sh = gc.open_by_key(LOG_SHEET_ID)
    try:
        ws = sh.worksheet(tab)
        if ws.row_values(1) != headers:  # p.ej. columna Programa agregada 2026-07-16
            ws.update("A1", [headers])
    except Exception:
        ws = sh.add_worksheet(title=tab, rows=1000, cols=len(headers))
        ws.update("A1", [headers])
    return ws


def ya_subido(ws, meeting_uuid: str) -> bool:
    uuids = ws.col_values(4)  # columna "Meeting UUID"
    return meeting_uuid in uuids


def registrar_log(ws, fecha, topic, duracion, meeting_uuid, video_url, video_id, programa, playlist=""):
    ws.append_row([fecha, topic, duracion, meeting_uuid, video_url, video_id, programa, playlist])


def procesar_nova(meeting_obj: dict, download_token: str, dry_run: bool) -> int:
    """Sesion NOVA -> Drive: MP4 principal + transcripcion(es) VTT a la subcarpeta
    NOVA-DD-MM-YYYY. Idempotente por nombre de archivo YA presente en la subcarpeta
    (asi el evento recording.transcript_completed puede llegar despues y solo agrega
    la transcripcion sin duplicar el video)."""
    topic = meeting_obj.get("topic", "")
    meeting_uuid = meeting_obj.get("uuid", "")
    duracion = meeting_obj.get("duration", "")
    start_time = meeting_obj.get("start_time", "")
    recording_files = meeting_obj.get("recording_files", [])

    print(f"Sesion NOVA detectada: {topic} ({meeting_uuid})")

    yt_vals = _parse_env_file(YT_ENV)
    if "YT_REFRESH_TOKEN" not in yt_vals:
        print("[ERROR] Falta YT_REFRESH_TOKEN en scripts/zoom-youtube/.env")
        return 1

    local = fecha_bogota(start_time)
    fecha_str = local.strftime("%d-%m-%Y")
    hora_str = local.strftime("%H.%M")

    # Que se sube: el MP4 principal (mismo criterio que YouTube) + toda transcripcion VTT.
    objetivos = []
    if any(f.get("file_type") == "MP4" for f in recording_files):
        objetivos.append((elegir_archivo_mp4(recording_files), "video/mp4", "grabacion", "mp4"))
    transcripciones = [f for f in recording_files if f.get("file_type") == "TRANSCRIPT"]
    for i, f in enumerate(transcripciones):
        etiqueta = "transcripcion" if len(transcripciones) == 1 else f"transcripcion-{i + 1}"
        objetivos.append((f, "text/vtt", etiqueta, "vtt"))

    if not objetivos:
        print(f"[SKIP] NOVA '{topic}': el payload no trae MP4 ni TRANSCRIPT todavia")
        return 0

    drive = construir_drive_client(yt_vals)
    subcarpeta_id = asegurar_subcarpeta_nova(drive, fecha_str)
    carpeta_url = f"https://drive.google.com/drive/folders/{subcarpeta_id}"
    existentes = nombres_en_carpeta(drive, subcarpeta_id)

    base = f"{topic} {fecha_str} {hora_str}"
    pendientes = [(a, m, f"{base} - {et}.{ext}") for a, m, et, ext in objetivos
                  if f"{base} - {et}.{ext}" not in existentes]

    if not pendientes:
        print(f"[OK] NOVA: todos los archivos ya estaban en {carpeta_url} (no se resube)")
        return 0

    if dry_run:
        for _, _, nombre in pendientes:
            print(f"[DRY-RUN] Subiria: {nombre}")
        return 0

    access_token = None
    if not download_token:
        access_token = obtener_token_zoom(_parse_env_file(ZOOM_ENV))

    subidos = []
    for archivo, mimetype, nombre in pendientes:
        ext = os.path.splitext(nombre)[1]
        print(f"Descargando {archivo.get('recording_type') or archivo.get('file_type')} "
              f"({archivo.get('file_size', 0) // 1_000_000} MB)...")
        ruta_local = descargar_mp4(archivo, access_token, download_token, suffix=ext)
        try:
            subir_a_drive(drive, subcarpeta_id, ruta_local, nombre, mimetype)
            subidos.append(nombre)
            print(f"  Subido: {nombre}")
        finally:
            try:
                os.remove(ruta_local)
            except OSError:
                pass

    gc = conectar_sheets()
    ws = asegurar_tab_log(gc, NOVA_LOG_TAB, NOVA_LOG_HEADERS)
    ws.append_row([start_time, topic, duracion, meeting_uuid, ", ".join(subidos), carpeta_url])

    print(f"[OK] NOVA: {len(subidos)} archivo(s) subidos a {carpeta_url}")
    return 0


def procesar(meeting_obj: dict, download_token: str, dry_run: bool,
             event: str = "recording.completed") -> int:
    topic = meeting_obj.get("topic", "")
    meeting_uuid = meeting_obj.get("uuid", "")
    duracion = meeting_obj.get("duration", "")
    start_time = meeting_obj.get("start_time", "")
    recording_files = meeting_obj.get("recording_files", [])

    if es_nova(topic):
        return procesar_nova(meeting_obj, download_token, dry_run)

    # Todo lo demas va a YouTube (decision 2026-07-16); MR_KEYWORDS solo etiqueta el programa.
    if event == "recording.transcript_completed":
        print(f"[SKIP] '{topic}': la transcripcion no se usa (YouTube solo recibe el MP4)")
        return 0

    etiqueta = "Mujeres ROFE" if es_clase_mr(topic) else "Jovenes creaTIvos"
    print(f"Grabacion para YouTube ({etiqueta}): {topic} ({meeting_uuid})")

    zoom_vals = _parse_env_file(ZOOM_ENV)
    yt_vals = _parse_env_file(YT_ENV)

    if "YT_REFRESH_TOKEN" not in yt_vals:
        print("[ERROR] Falta YT_REFRESH_TOKEN en scripts/zoom-youtube/.env "
              "(correr obtener_refresh_token.py primero)")
        return 1

    gc = conectar_sheets()
    ws = asegurar_tab_log(gc)
    if ya_subido(ws, meeting_uuid):
        print(f"[SKIP] Meeting {meeting_uuid} ya esta en el log (no se resube)")
        return 0

    access_token = obtener_token_zoom(zoom_vals)
    archivo = elegir_archivo_mp4(recording_files)
    print(f"Archivo elegido: {archivo.get('recording_type')} ({archivo.get('file_size', 0) // 1_000_000} MB)")

    if dry_run:
        print("[DRY-RUN] No se descarga ni se sube. Fin.")
        return 0

    ruta_local = descargar_mp4(archivo, access_token, download_token)
    print(f"Descargado a {ruta_local}")

    try:
        youtube = construir_youtube_client(yt_vals)
        resultado = subir_video(youtube, ruta_local, topic, start_time, etiqueta)
        video_id = resultado["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # "Carpetas": playlist por curso (topic sin sufijo de sala). Si falla, el video
        # ya esta subido -> advertir sin marcar error.
        playlist = normalizar_curso(topic)
        if playlist:
            try:
                agregar_a_playlist(youtube, asegurar_playlist(youtube, playlist), video_id)
                print(f"Agregado a playlist: {playlist}")
            except Exception as e:
                print(f"[WARN] Video subido pero fallo la playlist '{playlist}': {e}")

        registrar_log(ws, start_time, topic, duracion, meeting_uuid, video_url, video_id,
                      etiqueta, playlist)
        print(f"[OK] Subido ({etiqueta}): {video_url}")
        return 0
    finally:
        try:
            os.remove(ruta_local)
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description="Zoom recording.completed -> YouTube (MR)")
    parser.add_argument("--payload-b64", help="Body del webhook de Zoom, JSON codificado en base64")
    parser.add_argument("--payload-file", help="Ruta a un JSON con el payload del webhook de Zoom")
    parser.add_argument("--meeting-uuid", help="Backfill: UUID de la reunion (sin payload de webhook)")
    parser.add_argument("--host", default="comunicaciones@tocaunavida.org", help="Host para backfill")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        if args.payload_b64:
            payload = json.loads(base64.b64decode(args.payload_b64).decode("utf-8"))
            meeting_obj = payload["payload"]["object"]
            download_token = payload.get("download_token")
            return procesar(meeting_obj, download_token, args.dry_run,
                            payload.get("event", "recording.completed"))

        elif args.payload_file:
            with open(args.payload_file, encoding="utf-8") as f:
                payload = json.load(f)
            meeting_obj = payload["payload"]["object"]
            download_token = payload.get("download_token")
            return procesar(meeting_obj, download_token, args.dry_run,
                            payload.get("event", "recording.completed"))

        elif args.meeting_uuid:
            zoom_vals = _parse_env_file(ZOOM_ENV)
            access_token = obtener_token_zoom(zoom_vals)
            meeting_obj = obtener_grabacion_por_uuid(access_token, args.meeting_uuid)
            return procesar(meeting_obj, None, args.dry_run)

        else:
            parser.error("Se requiere --payload-file o --meeting-uuid")

    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
