# -*- coding: utf-8 -*-
"""
Crea la tabla asistencia_promedio en Supabase.
Ejecutar UNA SOLA VEZ.
"""
print("\n" + "="*80)
print("CREAR TABLA: asistencia_promedio")
print("="*80 + "\n")

sql = """
CREATE TABLE IF NOT EXISTS asistencia_promedio (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    promedio_general FLOAT,
    n_registros INTEGER DEFAULT 0,
    cursos JSONB DEFAULT '{}'::jsonb,
    actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asistencia_email ON asistencia_promedio(email);
CREATE INDEX IF NOT EXISTS idx_asistencia_actualizado ON asistencia_promedio(actualizado_en);
"""

print("SQL a ejecutar:")
print(sql)
print("\nEjecuta en Supabase SQL Editor (dashboard).\n")

print("Después, ejecuta:")
print("  python scripts/panel-datos/calcular_asistencia_promedio.py\n")
