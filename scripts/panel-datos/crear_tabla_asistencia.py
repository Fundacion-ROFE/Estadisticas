# -*- coding: utf-8 -*-
"""
Crea tabla asistencia_zoom en Supabase via PostgreSQL directo.

Uso: python scripts/panel-datos/crear_tabla_asistencia.py
     Requiere: export SUPABASE_DB_PASSWORD='...'
     (obtener de Supabase Dashboard -> Settings -> Database)
"""
import os
import sys
import io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def main():
    print("\n" + "="*80)
    print("CREAR TABLA: asistencia_zoom en Supabase PostgreSQL")
    print("="*80 + "\n")

    # Credenciales PostgreSQL Supabase
    db_host = "kbxptoowtnteflhrfwid.supabase.co"
    db_port = 5432
    db_user = "postgres"
    db_name = "postgres"
    db_password = os.environ.get("SUPABASE_DB_PASSWORD", "")

    if not db_password:
        print("[ERROR] SUPABASE_DB_PASSWORD no configurada")
        print("  1. Ve a Supabase Dashboard -> Settings -> Database")
        print("  2. Copia el database password")
        print("  3. Ejecuta: export SUPABASE_DB_PASSWORD='...'")
        print("  4. Re-ejecuta este script")
        return 1

    try:
        import psycopg2
    except ImportError:
        print("[ERROR] psycopg2 no instalado")
        print("  Instala con: pip install psycopg2-binary")
        return 1

    sql_stmts = [
        """CREATE TABLE IF NOT EXISTS public.asistencia_zoom (
            id BIGSERIAL PRIMARY KEY,
            email TEXT NOT NULL,
            curso TEXT NOT NULL,
            fecha DATE NOT NULL,
            nombre TEXT,
            apellido TEXT,
            correo_electronico TEXT,
            instancias TEXT,
            porcentaje_asistencia TEXT,
            created_at TIMESTAMP DEFAULT now(),
            UNIQUE (email, curso, fecha)
        )""",

        "CREATE INDEX IF NOT EXISTS idx_asistencia_email ON public.asistencia_zoom(email)",
        "CREATE INDEX IF NOT EXISTS idx_asistencia_curso ON public.asistencia_zoom(curso)",
        "CREATE INDEX IF NOT EXISTS idx_asistencia_fecha ON public.asistencia_zoom(fecha)",

        "ALTER TABLE public.asistencia_zoom ENABLE ROW LEVEL SECURITY",

        "DROP POLICY IF EXISTS asistencia_select_own ON public.asistencia_zoom",
        """CREATE POLICY asistencia_select_own ON public.asistencia_zoom
            FOR SELECT
            USING (auth.email() = email OR auth.jwt() ->> 'role' = 'service_role')""",

        "DROP POLICY IF EXISTS asistencia_insert_admin ON public.asistencia_zoom",
        """CREATE POLICY asistencia_insert_admin ON public.asistencia_zoom
            FOR INSERT
            WITH CHECK (auth.jwt() ->> 'role' = 'service_role')""",

        "DROP POLICY IF EXISTS asistencia_update_admin ON public.asistencia_zoom",
        """CREATE POLICY asistencia_update_admin ON public.asistencia_zoom
            FOR UPDATE
            WITH CHECK (auth.jwt() ->> 'role' = 'service_role')""",
    ]

    print(f"Conectando a PostgreSQL Supabase...")
    print(f"  Host: {db_host}")
    print(f"  User: {db_user}\n")

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            sslmode="require",
        )
        cursor = conn.cursor()

        for i, stmt in enumerate(sql_stmts, 1):
            print(f"  [{i}/{len(sql_stmts)}] Ejecutando...")
            cursor.execute(stmt)

        conn.commit()
        cursor.close()
        conn.close()

        print("\n[OK] Tabla asistencia_zoom creada exitosamente")
        print(f"\nTabla lista para datos:")
        print(f"  - Email, Curso, Fecha (UNIQUE)")
        print(f"  - Indices: email, curso, fecha")
        print(f"  - RLS activo: solo service_role puede insertar/actualizar")
        print(f"\nProximo paso: python scripts/panel-datos/sync_asistencia_supabase.py")
        return 0

    except psycopg2.Error as e:
        print(f"[ERROR] PostgreSQL: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
