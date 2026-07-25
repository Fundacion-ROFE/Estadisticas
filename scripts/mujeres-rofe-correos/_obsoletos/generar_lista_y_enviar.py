#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generar lista de postulantes_mr Bogotá y enviar campaña."""
import os, sys, json, re, urllib.request, subprocess
from pathlib import Path

# Cargar .env.local
for line in open(Path('../../.env.local').resolve(), encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

# Conectar Supabase
class Supa:
    def __init__(self, url, key):
        self.base = url.rstrip('/') + '/rest/v1'
        self.key = key
    def get_todo(self, ruta, page=1000):
        filas, offset = [], 0
        sep = '&' if '?' in ruta else '?'
        while True:
            headers = {'apikey': self.key, 'Authorization': f'Bearer {self.key}'}
            req = urllib.request.Request(f'{self.base}{ruta}{sep}limit={page}&offset={offset}', headers=headers)
            try:
                lote = json.loads(urllib.request.urlopen(req, timeout=120).read())
            except urllib.error.HTTPError as e:
                raise RuntimeError(f'HTTP {e.code}')
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
supa = Supa(url, key)

# PASO 1: Extraer postulantes_mr (TODOS)
print('[PASO 1] Extrayendo postulantes_mr...')
todos = supa.get_todo("/postulantes_mr")
print(f'  Total en tabla: {len(todos)}')

# Filtrar Bogotá en memoria
postulantes = []
for p in todos:
    ciudad = (p.get('ciudad') or '').strip().upper()
    if 'BOGOTA' in ciudad:
        postulantes.append(p)

print(f'  ✓ Encontrados Bogotá: {len(postulantes)}')

# Filtrar correos válidos
mapa = {}
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
for p in postulantes:
    correo = (p.get('email') or '').strip().lower()  # ← email, NO correo
    nombre = (p.get('nombre') or '').strip()
    if correo and EMAIL_RE.match(correo):
        if correo not in mapa:
            mapa[correo] = nombre

print(f'  ✓ Correos válidos: {len(mapa)}')

# PASO 2: Excluir hard bounces
print('[PASO 2] Consultando hard bounces...')
try:
    bounces = supa.get_todo('/email_bounces?select=email&tipo=eq.hard')
    hard_set = {(b.get('email') or '').strip().lower() for b in bounces}
    antes = len(mapa)
    mapa = {c: d for c, d in mapa.items() if c not in hard_set}
    excluidos = antes - len(mapa)
    print(f'  ✓ Excluidos: {excluidos}')
except Exception as e:
    print(f'  ⚠ Sin exclusiones: {e}')
    excluidos = 0

# PASO 3: Guardar CSV
print('[PASO 3] Guardando lista...')
os.makedirs('../../tools/mujeres-rofe-correos/data', exist_ok=True)
ruta_csv = '../../tools/mujeres-rofe-correos/data/lista_postulantes_mr_bogota_2026_jul24.csv'
with open(ruta_csv, 'w', encoding='utf-8') as f:
    f.write('nombre,correo,cohorte\n')
    for correo in sorted(mapa.keys()):
        nombre = (mapa[correo] or '').replace('"', '""')
        f.write(f'"{nombre}",{correo},\n')

print(f'  ✓ {len(mapa)} correos guardados')
print(f'\n[RESULTADO] {len(mapa)} personas de Bogotá listas para envío\n')

# PASO 4: ENVIAR
print('=' * 80)
print('PASO 4: ENVIANDO CAMPAÑA...')
print('=' * 80)

if len(mapa) == 0:
    print('[ERROR] No hay correos para enviar')
    sys.exit(1)

# Cargar credenciales SMTP
for line in open(Path('../../.env.local').resolve(), encoding='utf-8'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

# Actualizar ID de campaña
json_campana = 'campanas/encuentro_bogota_postulantes_mr_2026_jul24.json'
lista_csv = '../../tools/mujeres-rofe-correos/data/lista_postulantes_mr_bogota_2026_jul24.csv'

# Actualizar ID en JSON
with open(json_campana, 'r', encoding='utf-8') as f:
    config = json.load(f)
config['ID'] = 'encuentro_bogota_postulantes_mr_2026_jul24'
with open(json_campana, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

# Ejecutar envío
cmd = [sys.executable, 'enviar_campana.py', json_campana, '--enviar']
result = subprocess.run(cmd, input=f'ENVIAR {len(mapa)}\n', text=True)

print(f'\n[FINAL] Envío completado. Status: {result.returncode}')
