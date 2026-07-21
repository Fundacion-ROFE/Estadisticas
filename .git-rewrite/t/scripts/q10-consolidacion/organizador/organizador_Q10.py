# ==============================================================================
# ADVERTENCIA CRÍTICA DE RED: Configuración obligatoria del Truststore Corporativo
# DEBE ejecutarse antes de importar gspread, requests o google-auth
# ==============================================================================
import truststore
truststore.inject_into_ssl()

import os
import sys
import threading
from datetime import datetime
import pandas as pd
import customtkinter as ctk
from tkinter import ttk, messagebox

import gspread
from google.oauth2.service_account import Credentials

# Configuración de CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Constantes de conexión a Google Sheets
SHEET_ORIGEN_ID = "1d3S41J9nlVI3qCy-WF_D3ZezTwRCW17vnL7u284XDG0"
SHEET_DESTINO_ID = "1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs"

# Definición de rutas relativas por entorno
CREDENTIALS_DEV = "../credenciales_service_account.json"  # Un nivel arriba en desarrollo
CREDENTIALS_EXE = "credenciales_service_account.json"     # En la raíz interna del .exe compilado

def obtener_ruta_credenciales():
    """
    Resuelve dinámicamente la ubicación del JSON de credenciales.
    Soporta entorno de desarrollo (../) y empaquetado PyInstaller.
    """
    if hasattr(sys, '_MEIPASS'):
        # Entorno de producción (.exe): PyInstaller extrae los archivos en una carpeta temporal
        ruta_bundle = os.path.join(sys._MEIPASS, CREDENTIALS_EXE)
        if os.path.exists(ruta_bundle):
            return ruta_bundle
    # Entorno de desarrollo: Busca el archivo un nivel arriba de la carpeta /organizador
    return CREDENTIALS_DEV


class AppOrganizador(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de la Ventana Principal
        self.title("Fundación ROFÉ / Jóvenes creaTIvos - Organizador Q10")
        self.geometry("1250x750")
        self.minsize(1200, 700)

        # Variables de control de datos
        self.df_original = None      
        self.df_trabajo = None       
        self.cursos_detectados = []
        self.cambios_sin_guardar = False

        # Configuración del Grid Principal
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Construcción de la UI estática
        self._crear_cabecera()
        self._crear_barra_estado()
        
        # Contenedor dinámico central (Carga/Datos)
        self.contenedor_principal = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor_principal.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.contenedor_principal.grid_rowconfigure(0, weight=1)
        self.contenedor_principal.grid_columnconfigure(0, weight=1)

        # Iniciar la carga inicial de datos en un hilo separado
        self.ejecutar_en_hilo(self.cargar_datos_desde_sheets, "Conectando con Google Sheets y descargando datos...")

    def _crear_cabecera(self):
        """Crea el panel superior con los botones de acción global."""
        self.frame_top = ctk.CTkFrame(self, height=60)
        self.frame_top.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.frame_top.grid_columnconfigure(2, weight=1)

        self.btn_recargar = ctk.CTkButton(
            self.frame_top, text="🔄 Actualizar desde Sheets", 
            fg_color="#2196F3", hover_color="#1E88E5",
            command=self.confirmar_y_recargar
        )
        self.btn_recargar.grid(row=0, column=0, padx=10, pady=10)

        self.btn_subir = ctk.CTkButton(
            self.frame_top, text="☁️ Subir a h2test",
            fg_color="#4CAF50", hover_color="#43A047",
            command=self.subir_datos_a_sheets
        )
        self.btn_subir.grid(row=0, column=1, padx=10, pady=10)

        self.lbl_titulo = ctk.CTkLabel(
            self.frame_top, text="Consolidado de Estudiantes Q10", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_titulo.grid(row=0, column=2, padx=20, pady=10, sticky="e")

    def _crear_barra_estado(self):
        """Crea la barra inferior de log de operaciones."""
        self.frame_status = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.frame_status.grid(row=2, column=0, sticky="ew")
        self.frame_status.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            self.frame_status, text="Inicializando aplicación...", 
            font=ctk.CTkFont(size=12), anchor="w"
        )
        self.lbl_status.grid(row=0, column=0, padx=15, pady=3, sticky="ew")

    def actualizar_status(self, mensaje):
        self.lbl_status.configure(text=mensaje)

    def mostrar_pantalla_carga(self, mensaje="Procesando..."):
        for widget in self.contenedor_principal.winfo_children():
            widget.destroy()

        frame_loading = ctk.CTkFrame(self.contenedor_principal, fg_color="transparent")
        frame_loading.place(relx=0.5, rely=0.5, anchor="center")

        spinner = ctk.CTkProgressBar(frame_loading, mode="indeterminate", width=300, progress_color="#4CAF50")
        spinner.pack(pady=15)
        spinner.start()

        # CORREGIDO: weight="bold" para total compatibilidad con Tcl/Tk en Python 3.14+
        lbl_loading = ctk.CTkLabel(frame_loading, text=mensaje, font=ctk.CTkFont(size=14, weight="bold"))
        lbl_loading.pack()
        
        self.btn_recargar.configure(state="disabled")
        self.btn_subir.configure(state="disabled")

    def ejecutar_en_hilo(self, target_func, mensaje_carga=None):
        if mensaje_carga:
            self.mostrar_pantalla_carga(mensaje_carga)
            self.actualizar_status(mensaje_carga)

        def worker():
            try:
                target_func()
            except Exception as e:
                self.after(0, self.manejar_error, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def manejar_error(self, error_msg):
        self.actualizar_status(f"Error crítico: {error_msg}")
        messagebox.showerror(
            "Error de Conexión / Operación", 
            f"Ocurrió un problema interactuando con la API o procesando datos:\n\n{error_msg}\n\n"
            "Verifique el proxy corporativo, la presencia de las credenciales y los IDs de los Sheets."
        )
        self.btn_recargar.configure(state="normal")
        self.btn_subir.configure(state="normal")
        for widget in self.contenedor_principal.winfo_children():
            widget.destroy()

    # ==============================================================================
    # LÓGICA DE NEGOCIO Y CONEXIÓN CON GOOGLE SHEETS
    # ==============================================================================
    def cargar_datos_desde_sheets(self):
        ruta_json = obtener_ruta_credenciales()
        if not os.path.exists(ruta_json):
            raise FileNotFoundError(f"No se encontró el archivo de credenciales en la ruta calculada: {os.path.abspath(ruta_json)}")

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(ruta_json, scopes=scopes)
        cliente = gspread.authorize(creds)

        sheet_origen = cliente.open_by_key(SHEET_ORIGEN_ID)
        worksheet = sheet_origen.worksheet("H1Test")
        
        datos_raw = worksheet.get_all_records(default_blank="")
        
        if not datos_raw:
            raise ValueError("La pestaña H1Test de origen está vacía o carece de encabezados.")

        df = pd.DataFrame(datos_raw)

        columnas_esperadas = ["Identificacion", "Nombre", "Celular", "Email", "Curso", "Avance"]
        for col in columnas_esperadas:
            if col not in df.columns:
                match_flexible = [c for c in df.columns if c.lower() == col.lower()]
                if match_flexible:
                    df.rename(columns={match_flexible[0]: col}, inplace=True)
                else:
                    raise KeyError(f"La columna requerida '{col}' no se encuentra en el Sheet de origen.")

        df['Identificacion'] = df['Identificacion'].astype(str).str.strip()
        df['Nombre'] = df['Nombre'].astype(str).str.strip()
        df['Celular'] = df['Celular'].astype(str).str.strip()
        df['Email'] = df['Email'].astype(str).str.strip()
        df['Curso'] = df['Curso'].astype(str).str.strip()
        df['Avance'] = df['Avance'].astype(str).str.replace('%', '', regex=False).str.strip()

        self.df_original = df.copy()
        self.df_trabajo = df.copy()
        self.cambios_sin_guardar = False

        cursos_unicos = df[df['Curso'] != ""]['Curso'].unique()
        self.cursos_detectados = sorted(list(cursos_unicos))

        self.after(0, self.construir_pestañas_datos)

    def confirmar_y_recargar(self):
        if self.cambios_sin_guardar:
            confirmar = messagebox.askyesno(
                "Cambios sin guardar", 
                "Tiene modificaciones locales en memoria que no se han subido a h2test.\n"
                "¿Está seguro de que desea recargar desde Sheets? Perderá los cambios actuales."
            )
            if not confirmar:
                return
        self.ejecutar_en_hilo(self.cargar_datos_desde_sheets, "Recargando datos desde Google Sheets...")

    # ==============================================================================
    # RENDERIZADO DINÁMICO DE PESTAÑAS Y CONTROLES DE TABLA
    # ==============================================================================
    def construir_pestañas_datos(self):
        self.btn_recargar.configure(state="normal")
        self.btn_subir.configure(state="normal")
        for widget in self.contenedor_principal.winfo_children():
            widget.destroy()

        self.tab_control = ctk.CTkTabview(self.contenedor_principal)
        self.tab_control.grid(row=0, column=0, sticky="nsew")

        estilo = ttk.Style()
        estilo.theme_use("default")
        estilo.configure("Treeview", 
                         background="#2A2A2A", 
                         foreground="white", 
                         rowheight=26, 
                         fieldbackground="#2A2A2A",
                         font=("monospace", 10))
        estilo.configure("Treeview.Heading", 
                         background="#1F1F1F", 
                         foreground="white", 
                         font=("monospace", 10, "bold"))
        estilo.map("Treeview", background=[('selected', '#107C41')]) 
        estilo.map("Treeview.Heading", background=[('active', '#333333')])

        self.tablas_referencia = {}

        for curso in self.cursos_detectados:
            self.tab_control.add(curso)
            self.tab_control.tab(curso).grid_columnconfigure(0, weight=1)
            self.tab_control.tab(curso).grid_rowconfigure(1, weight=1)
            
            df_curso = self.df_trabajo[self.df_trabajo['Curso'] == curso].sort_values(by='Nombre')
            self._construir_modulo_tabla(curso, df_curso, incluye_avance=True)

        nombre_sin_curso = "Sin curso"
        self.tab_control.add(nombre_sin_curso)
        self.tab_control.tab(nombre_sin_curso).grid_columnconfigure(0, weight=1)
        self.tab_control.tab(nombre_sin_curso).grid_rowconfigure(1, weight=1)
        
        df_sin_curso = self.df_trabajo[self.df_trabajo['Curso'] == ""].sort_values(by='Nombre')
        self._construir_modulo_tabla(nombre_sin_curso, df_sin_curso, incluye_avance=False)
        self.tab_control._segmented_button._buttons_dict[nombre_sin_curso].configure(text_color="#9E9E9E")

        nombre_obs = "⚠️ Observaciones"
        self.tab_control.add(nombre_obs)
        self.tab_control.tab(nombre_obs).grid_columnconfigure(0, weight=1)
        self.tab_control.tab(nombre_obs).grid_rowconfigure(1, weight=1)
        self._construir_pestaña_observaciones(nombre_obs)
        
        self.tab_control._segmented_button._buttons_dict[nombre_obs].configure(
            text_color="#FFC107",
            selected_color="#FFC107",
            selected_text_color="#000000"
        )

        nombre_stats = "📊 Estadísticas"
        self.tab_control.add(nombre_stats)
        self.tab_control.tab(nombre_stats).grid_columnconfigure(0, weight=1)
        self.tab_control.tab(nombre_stats).grid_rowconfigure(2, weight=1)
        self._construir_pestaña_estadisticas(nombre_stats)
        self.tab_control._segmented_button._buttons_dict[nombre_stats].configure(
            text_color="#00BCD4",
            selected_color="#00BCD4",
            selected_text_color="#000000"
        )

        self.tab_control.set(self.cursos_detectados[0] if self.cursos_detectados else nombre_sin_curso)
        self.actualizar_status(f"Datos renderizados con éxito. Cursos mapeados: {len(self.cursos_detectados)}")

    def _construir_modulo_tabla(self, nombre_pestaña, dataframe_filtrado, incluye_avance=True):
        tab_obj = self.tab_control.tab(nombre_pestaña)

        total_estudiantes = len(dataframe_filtrado)
        if incluye_avance:
            serie_numerica = pd.to_numeric(dataframe_filtrado['Avance'], errors='coerce').dropna()
            promedio = serie_numerica.mean() if not serie_numerica.empty else 0.0
            texto_header = f"Total: {total_estudiantes} estudiantes | Promedio avance: {promedio:.1f}%"
        else:
            texto_header = f"Total: {total_estudiantes} estudiantes"

        lbl_info = ctk.CTkLabel(tab_obj, text=texto_header, font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        lbl_info.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        cols = ["Identificacion", "Nombre", "Celular", "Email", "Avance"] if incluye_avance else ["Identificacion", "Nombre", "Celular", "Email"]
        
        table_frame = ctk.CTkFrame(tab_obj)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        
        for col in cols:
            tree.heading(col, text=col, anchor="w")
            if col in ["Nombre", "Email"]:
                tree.column(col, width=280, minwidth=150, anchor="w")
            else:
                tree.column(col, width=120, minwidth=80, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        for index, fila in dataframe_filtrado.iterrows():
            valores_fila = [fila[c] for c in cols]
            tree.insert("", "end", iid=str(index), values=valores_fila)

        tree.bind("<Double-1>", lambda event: self.abrir_editor_celda(event, tree, cols))
        self.tablas_referencia[nombre_pestaña] = tree

    # ==============================================================================
    # DETECCIÓN AUTOMÁTICA DE CASOS
    # ==============================================================================
    def _calcular_observaciones(self) -> pd.DataFrame:
        """Detecta casos anómalos en df_trabajo y devuelve tabla plana de observaciones."""
        df = self.df_trabajo
        filas = []

        for _, fila in df.iterrows():
            email     = fila['Email']
            curso     = fila['Curso']
            avance_str = fila['Avance']
            celular   = fila.get('Celular', '')

            try:
                avance_num = float(avance_str) if avance_str != "" else None
            except ValueError:
                avance_num = None

            base = {
                "Identificacion": fila['Identificacion'],
                "Nombre":         fila['Nombre'],
                "Celular":        celular,
                "Email":          email,
                "Curso":          curso,
                "Avance":         avance_str,
            }

            # Caso: EMAIL SIN MATCH (está en Estudiantes pero no en Consolidado)
            if curso == "" and avance_str == "" and email != "":
                filas.append({**base, "Categoria": "SIN MATCH", "Curso": "[N/A]",
                               "Observacion": "Email no encontrado en reporte de cursos"})
                continue

            # Caso: SIN CURSO
            if curso == "":
                filas.append({**base, "Categoria": "SIN CURSO",
                               "Observacion": "Sin curso asignado en Q10"})

            # Caso: AVANCE 0%
            if curso != "" and avance_str in ("0", "0.0", "0%"):
                filas.append({**base, "Categoria": "AVANCE 0%",
                               "Observacion": "Matriculado pero sin actividad registrada"})

            # Caso: AVANCE IRREGULAR
            if avance_num is not None and avance_num > 100.0:
                filas.append({**base, "Categoria": "AVANCE IRREGULAR",
                               "Observacion": "Avance superior al 100% — revisar en Q10"})

        cols = ["Categoria", "Identificacion", "Nombre", "Celular", "Email", "Curso", "Avance", "Observacion"]
        if not filas:
            return pd.DataFrame(columns=cols)
        return pd.DataFrame(filas)[cols]

    def _calcular_estadisticas(self) -> dict:
        df = self.df_trabajo
        total_registros = len(df)
        emails_validos = df['Email'].replace("", pd.NA).dropna()
        total_estudiantes = emails_validos.nunique()

        avance_num = pd.to_numeric(df['Avance'], errors='coerce')
        avance_valido = avance_num.dropna()
        promedio_general = round(avance_valido.mean(), 1) if not avance_valido.empty else 0.0

        df_con_curso = df[df['Curso'] != ""].copy()
        df_con_curso['_av'] = pd.to_numeric(df_con_curso['Avance'], errors='coerce')

        stats_por_curso = []
        for curso in sorted(df_con_curso['Curso'].unique()):
            df_c = df_con_curso[df_con_curso['Curso'] == curso]
            av_c = df_c['_av'].dropna()
            stats_por_curso.append({
                'Curso':       curso,
                'Estudiantes': len(df_c),
                'Promedio':    round(av_c.mean(), 1) if not av_c.empty else 0.0,
                'Min':         round(av_c.min(), 1)  if not av_c.empty else 0.0,
                'Max':         round(av_c.max(), 1)  if not av_c.empty else 0.0,
            })

        df_obs = self._calcular_observaciones()
        anomalias = {
            'SIN CURSO':        int((df_obs['Categoria'] == 'SIN CURSO').sum()),
            'AVANCE 0%':        int((df_obs['Categoria'] == 'AVANCE 0%').sum()),
            'SIN MATCH':        int((df_obs['Categoria'] == 'SIN MATCH').sum()),
            'AVANCE IRREGULAR': int((df_obs['Categoria'] == 'AVANCE IRREGULAR').sum()),
        }

        return {
            'total_registros':   total_registros,
            'total_estudiantes': total_estudiantes,
            'promedio_general':  promedio_general,
            'stats_por_curso':   stats_por_curso,
            'anomalias':         anomalias,
            'timestamp':         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _construir_pestaña_observaciones(self, nombre_pestaña):
        tab_obj = self.tab_control.tab(nombre_pestaña)

        df_obs = self._calcular_observaciones()
        c_sin_curso  = (df_obs['Categoria'] == "SIN CURSO").sum()
        c_avance_0   = (df_obs['Categoria'] == "AVANCE 0%").sum()
        c_sin_match  = (df_obs['Categoria'] == "SIN MATCH").sum()
        c_irregular  = (df_obs['Categoria'] == "AVANCE IRREGULAR").sum()

        timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        texto_resumen = f"SIN CURSO: {c_sin_curso} | AVANCE 0%: {c_avance_0} | SIN MATCH: {c_sin_match} | IRREGULAR: {c_irregular}    [Última carga: {timestamp_actual}]"
        
        lbl_resumen = ctk.CTkLabel(tab_obj, text=texto_resumen, font=ctk.CTkFont(size=12, weight="bold", family="monospace"), anchor="w", text_color="#FFC107")
        lbl_resumen.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        cols_obs = ["Categoria", "Identificacion", "Nombre", "Celular", "Email", "Curso", "Avance", "Observacion"]
        
        table_frame = ctk.CTkFrame(tab_obj)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        tree_obs = ttk.Treeview(table_frame, columns=cols_obs, show="headings", selectmode="none")
        
        for col in cols_obs:
            tree_obs.heading(col, text=col, anchor="w")
            if col in ["Nombre", "Curso", "Observacion"]:
                tree_obs.column(col, width=220, anchor="w")
            elif col == "Email":
                tree_obs.column(col, width=180, anchor="w")
            elif col == "Celular":
                tree_obs.column(col, width=120, anchor="w")
            else:
                tree_obs.column(col, width=110, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree_obs.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree_obs.xview)
        tree_obs.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree_obs.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        if not df_obs.empty:
            for _, fila in df_obs.iterrows():
                tree_obs.insert("", "end", values=[fila[c] for c in cols_obs])

    def _construir_pestaña_estadisticas(self, nombre_pestaña):
        tab_obj = self.tab_control.tab(nombre_pestaña)
        stats = self._calcular_estadisticas()

        frame_cards = ctk.CTkFrame(tab_obj, fg_color="transparent")
        frame_cards.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))

        card_data = [
            ("Registros totales",  str(stats['total_registros']),     "#2196F3"),
            ("Estudiantes únicos", str(stats['total_estudiantes']),    "#4CAF50"),
            ("Promedio de avance", f"{stats['promedio_general']}%",    "#FF9800"),
            ("Cursos activos",     str(len(stats['stats_por_curso'])), "#9C27B0"),
        ]
        for i, (label, valor, color) in enumerate(card_data):
            frame_cards.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(frame_cards, fg_color=color, corner_radius=8)
            card.grid(row=0, column=i, padx=8, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=valor, font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(10, 2))
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11)).pack(pady=(0, 10))

        anom = stats['anomalias']
        texto_anom = (
            f"Anomalías  →  SIN CURSO: {anom['SIN CURSO']}  |  "
            f"AVANCE 0%: {anom['AVANCE 0%']}  |  "
            f"SIN MATCH: {anom['SIN MATCH']}  |  "
            f"IRREGULAR: {anom['AVANCE IRREGULAR']}"
            f"    [Generado: {stats['timestamp']}]"
        )
        ctk.CTkLabel(
            tab_obj, text=texto_anom,
            font=ctk.CTkFont(size=11, family="monospace"),
            anchor="w", text_color="#90CAF9"
        ).grid(row=1, column=0, padx=10, pady=(0, 4), sticky="ew")

        cols_stats = ["Curso", "Estudiantes", "Promedio %", "Mín %", "Máx %"]
        table_frame = ctk.CTkFrame(tab_obj)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(table_frame, columns=cols_stats, show="headings", selectmode="none")
        for col in cols_stats:
            tree.heading(col, text=col, anchor="w")
            tree.column(col, width=350 if col == "Curso" else 120, minwidth=80,
                        anchor="w" if col == "Curso" else "center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        for s in stats['stats_por_curso']:
            tree.insert("", "end", values=[
                s['Curso'], s['Estudiantes'],
                f"{s['Promedio']}%", f"{s['Min']}%", f"{s['Max']}%",
            ])

    # ==============================================================================
    # EDICIÓN DE CELDAS EN INTERFAZ (EN MEMORIA)
    # ==============================================================================
    def abrir_editor_celda(self, event, tree, columnas):
        region = tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column_id = tree.identify_column(event.x)
        row_id = tree.identify_row(event.y) 
        
        col_index = int(column_id.replace("#", "")) - 1
        col_nombre = columnas[col_index]

        bbox = tree.bbox(row_id, column_id)
        if not bbox:
            return
        x, y, w, h = bbox

        valor_actual = str(tree.item(row_id, "values")[col_index])

        entry_edit = ctk.CTkEntry(tree, width=w, height=h, font=("monospace", 10), corner_radius=0)
        entry_edit.insert(0, valor_actual)
        entry_edit.select_range(0, 'end')
        entry_edit.focus_set()
        entry_edit.place(x=x, y=y, width=w, height=h)

        def guardar_edicion(event_trigger=None):
            nuevo_valor = entry_edit.get().strip()
            entry_edit.destroy()

            if nuevo_valor != valor_actual:
                valores_lista = list(tree.item(row_id, "values"))
                valores_lista[col_index] = nuevo_valor
                tree.item(row_id, values=valores_lista)

                idx_pandas = int(row_id)
                self.df_trabajo.at[idx_pandas, col_nombre] = nuevo_valor
                self.cambios_sin_guardar = True
                self.actualizar_status(f"Cambio guardado en memoria. Fila ID: {idx_pandas} ({col_nombre}).")

        def cancelar_edicion(event_trigger=None):
            entry_edit.destroy()

        entry_edit.bind("<Return>", guardar_edicion)
        entry_edit.bind("<FocusOut>", guardar_edicion)
        entry_edit.bind("<Escape>", cancelar_edicion)

    # ==============================================================================
    # ESCRITURA EN H2TEST (GOOGLE SHEETS)
    # ==============================================================================
    def subir_datos_a_sheets(self):
        confirmar = messagebox.askyesno(
            "Confirmación de subida", 
            "¿Está seguro de que desea sobreescribir la pestaña h2test con los datos actuales?"
        )
        if not confirmar:
            return

        self.ejecutar_en_hilo(self._ejecutar_escritura_h2test, "Formateando secciones and escribiendo en h2test...")

    def _ejecutar_escritura_h2test(self):
        ruta_json = obtener_ruta_credenciales()
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(ruta_json, scopes=scopes)
        cliente = gspread.authorize(creds)

        sheet_destino = cliente.open_by_key(SHEET_DESTINO_ID)
        
        # 1. Intentar abrir la hoja. Si no existe, la creamos de inmediato de forma segura.
        try:
            worksheet_destino = sheet_destino.worksheet("h2test")
        except gspread.exceptions.WorksheetNotFound:
            try:
                worksheet_destino = sheet_destino.add_worksheet(title="h2test", rows="1000", cols="20")
            except Exception as e:
                # Si dio error de duplicado por concurrencia, la abrimos normalmente
                worksheet_destino = sheet_destino.worksheet("h2test")

        # 2. Limpieza de datos robusta directamente usando el ID de la hoja sin el método .clear() tradicional
        try:
            sheet_destino.values_clear(f"'h2test'!A1:Z1000")
        except Exception:
            # Fallback clásico si values_clear no es soportado por el rol de la cuenta
            try:
                worksheet_destino.clear()
            except Exception:
                pass

        bloques = []
        conteo_metricas_alertas = []

        # Construir bloque por cada curso
        for curso in self.cursos_detectados:
            df_c = self.df_trabajo[self.df_trabajo['Curso'] == curso].sort_values(by='Nombre')
            cant_filas = len(df_c)
            conteo_metricas_alertas.append(f"• {curso}: {cant_filas} estudiantes")

            bloque = []
            bloque.append([curso.upper(), "", "", "", ""])
            bloque.append(["Identificacion", "Nombre", "Celular", "Email", "Avance"])
            for _, fila in df_c.iterrows():
                bloque.append([
                    str(fila['Identificacion']),
                    str(fila['Nombre']),
                    str(fila['Celular']),
                    str(fila['Email']),
                    str(fila['Avance'])
                ])
            bloques.append(bloque)

        # Construir bloque de sin curso
        df_sc = self.df_trabajo[self.df_trabajo['Curso'] == ""].sort_values(by='Nombre')
        cant_sc = len(df_sc)
        conteo_metricas_alertas.append(f"• Sin curso asignado: {cant_sc} estudiantes")

        bloque_sc = []
        bloque_sc.append(["SIN CURSO ASIGNADO", "", "", "", ""])
        bloque_sc.append(["Identificacion", "Nombre", "Celular", "Email", ""])
        for _, fila in df_sc.iterrows():
            bloque_sc.append([
                str(fila['Identificacion']),
                str(fila['Nombre']),
                str(fila['Celular']),
                str(fila['Email']),
                ""
            ])
        bloques.append(bloque_sc)

        # Combinar bloques en horizontal: cada bloque ocupa 5 cols + 2 cols de separación
        COLS_BLOQUE = 5
        SEPARADOR = ["", ""]
        alto_max = max(len(b) for b in bloques) if bloques else 0

        matriz_salida = []
        for fila_idx in range(alto_max):
            fila_combinada = []
            for b_idx, bloque in enumerate(bloques):
                if b_idx > 0:
                    fila_combinada.extend(SEPARADOR)
                if fila_idx < len(bloque):
                    fila_combinada.extend(bloque[fila_idx])
                else:
                    fila_combinada.extend([""] * COLS_BLOQUE)
            matriz_salida.append(fila_combinada)

        # 3. Escritura atómica usando el formato estándar de gspread v6+
        if matriz_salida:
            worksheet_destino.update(values=matriz_salida, range_name="A1")

        # 4. Escribir tabla de Observaciones en pestaña separada (para soporte y Power BI)
        try:
            ws_obs = sheet_destino.worksheet("Observaciones")
        except gspread.exceptions.WorksheetNotFound:
            try:
                ws_obs = sheet_destino.add_worksheet(title="Observaciones", rows="2000", cols="10")
            except Exception:
                ws_obs = sheet_destino.worksheet("Observaciones")

        try:
            sheet_destino.values_clear("'Observaciones'!A1:J2000")
        except Exception:
            try:
                ws_obs.clear()
            except Exception:
                pass

        df_obs = self._calcular_observaciones()
        cols_obs = ["Categoria", "Identificacion", "Nombre", "Celular", "Email", "Curso", "Avance", "Observacion"]
        filas_obs = [cols_obs]
        for _, fila in df_obs.iterrows():
            filas_obs.append([str(fila[c]) for c in cols_obs])

        if len(filas_obs) > 1:
            ws_obs.update(values=filas_obs, range_name="A1")
            conteo_metricas_alertas.append(f"\n⚠️ Observaciones escritas: {len(filas_obs) - 1} casos")
        else:
            ws_obs.update(values=[cols_obs], range_name="A1")
            conteo_metricas_alertas.append("\n✅ Sin observaciones")

        # 5. Escribir pestaña de Estadísticas
        try:
            ws_stats = sheet_destino.worksheet("Estadisticas")
        except gspread.exceptions.WorksheetNotFound:
            try:
                ws_stats = sheet_destino.add_worksheet(title="Estadisticas", rows="200", cols="10")
            except Exception:
                ws_stats = sheet_destino.worksheet("Estadisticas")

        try:
            sheet_destino.values_clear("'Estadisticas'!A1:J200")
        except Exception:
            try:
                ws_stats.clear()
            except Exception:
                pass

        stats = self._calcular_estadisticas()
        filas_stats = [
            ["RESUMEN GENERAL", ""],
            ["Métrica", "Valor"],
            ["Total registros",         stats['total_registros']],
            ["Estudiantes únicos",      stats['total_estudiantes']],
            ["Promedio avance general", f"{stats['promedio_general']}%"],
            ["Fecha actualización",     stats['timestamp']],
            ["", ""],
            ["POR CURSO", "", "", "", ""],
            ["Curso", "Estudiantes", "Promedio %", "Mín %", "Máx %"],
        ]
        for s in stats['stats_por_curso']:
            filas_stats.append([s['Curso'], s['Estudiantes'], f"{s['Promedio']}%", f"{s['Min']}%", f"{s['Max']}%"])
        filas_stats.append(["", "", "", "", ""])
        filas_stats.append(["ANOMALÍAS", ""])
        filas_stats.append(["Categoría", "Cantidad"])
        for cat, cant in stats['anomalias'].items():
            filas_stats.append([cat, cant])

        ws_stats.update(values=filas_stats, range_name="A1")
        conteo_metricas_alertas.append("📊 Estadísticas escritas en pestaña 'Estadisticas'")

        self.df_original = self.df_trabajo.copy()
        self.cambios_sin_guardar = False

        self.after(0, lambda: self.finalizar_subida_exitosa(conteo_metricas_alertas))

    def finalizar_subida_exitosa(self, logs_conteo):
        self.construir_pestañas_datos()
        self.actualizar_status("Datos sincronizados en h2test correctamente.")
        mensaje_desglose = "La hoja h2test se ha actualizado con éxito.\n\nResumen de filas procesadas:\n" + "\n".join(logs_conteo)
        messagebox.showinfo("Sincronización Exitosa", mensaje_desglose)


if __name__ == "__main__":
    app = AppOrganizador()
    app.mainloop()