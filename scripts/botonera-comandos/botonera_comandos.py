# -*- coding: utf-8 -*-
"""
botonera_comandos.py — Botonera de escritorio para los comandos del bot de Telegram.

Cada botón ejecuta LOCALMENTE, en esta misma PC, el mismo comando que dispara el bot
de Telegram del proyecto (`/actualizar <algo>`). La fuente de verdad de qué corre cada
comando es el workflow n8n `n8n-workflows/q10-consolidacion.json`, nodo "Parsear Comando"
(mapa PROCESOS) + la cadena del comando `q10`. Si algún comando cambia allí, actualizar
la lista COMANDOS de abajo.

Objetivo: no tener que recordar qué comandos existen, para qué sirve cada uno, ni por qué
importa correrlo. Se abre, se navega con la barra de arriba, se lee la justificación y se
hace clic. La salida de cada script se muestra en vivo abajo.

Nota: NO pasa por Telegram ni por n8n (el trigger de Telegram no se puede disparar con el
token del bot). Corre los scripts locales directamente — el resultado es el mismo que el
comando de Telegram, porque el bot no hace más que correr estos mismos scripts.

Fundación ROFÉ | Jóvenes creaTIvos
"""

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

DIR_SCRIPT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(DIR_SCRIPT, "..", ".."))  # .../admin-usable
LOCK_CLI = os.path.join(ROOT, "scripts", "common", "lock_cli.py")

Q10_DIR = os.path.join(ROOT, "scripts", "q10-consolidacion")
ORG_DIR = os.path.join(Q10_DIR, "organizador")

# ── Paleta ROFÉ (aprox., consistente con el resto de herramientas) ───────────
NAVY = "#070332"
ROSA = "#E6007E"
GRIS_BG = "#f4f4f7"
GRIS_CARD = "#ffffff"
GRIS_TXT = "#333333"
GRIS_SUAVE = "#6b6b80"
VERDE = "#2e7d32"
AMBAR = "#b26a00"
NAV_BG = "#12103d"
CONSOLA_BG = "#1e1e2e"
CONSOLA_FG = "#e6e6e6"


def _paso(cwd, *args):
    """Un paso = 'cd /d <cwd> && python <args>' (sintaxis cmd.exe, igual que n8n)."""
    return f'cd /d "{cwd}" && python ' + " ".join(args)


# ── Los comandos (espejo de PROCESOS en q10-consolidacion.json) ──────────────
# steps: lista de comandos shell que se corren en orden; se detiene al primer fallo.
# lock:  nombres de lock (lock_cli.py) para los pesados, para no chocar con el bot.
# justificacion: por qué importa correrlo y cuándo — no solo "qué hace".
COMANDOS = [
    {
        "clave": "q10",
        "corto": "Q10",
        "telegram": "/actualizar q10",
        "nombre": "Q10 → Sheets + Dashboard",
        "desc": ("Pipeline completo de Q10: extrae de Q10, corre el organizador y actualiza el "
                 "dashboard público de GitHub Pages (stats, avance, retirados, aprobación)."),
        "justificacion": ("El dashboard público es lo que ve el equipo (y cualquier externo con el "
                           "link) para seguir el avance de Q10. Sin esta corrida, esas cifras se "
                           "quedan con el dato de la última vez que corrió el bot programado o esta "
                           "misma botonera. Úsalo cuando necesites cifras frescas AHORA — antes de "
                           "una reunión, por ejemplo — sin esperar al próximo ciclo automático."),
        "pesado": True,
        "efecto": "Descarga de Q10 + empuja datos al dashboard público (GitHub Pages). Tarda varios minutos y usa bastante RAM.",
        "lock": ["q10-actualizar-grupos", "heavy-pipeline"],
        "steps": [
            _paso(Q10_DIR, "q10_to_sheets.py", "--grupo", "h1test"),
            _paso(ORG_DIR, "organizador_headless.py"),
            _paso(Q10_DIR, "export_stats.py"),
            _paso(Q10_DIR, "export_avance.py"),
            _paso(Q10_DIR, "q10_to_sheets.py", "--grupo", "retirados"),
            _paso(ORG_DIR, "retirados_headless.py"),
            _paso(Q10_DIR, "export_retirados.py"),
            _paso(Q10_DIR, "export_aprobacion.py"),
            _paso(ROOT, "tools\\exportar_sin_completar.py"),
        ],
    },
    {
        "clave": "panel",
        "corto": "Panel",
        "telegram": "/actualizar panel",
        "nombre": "Pipeline Panel de Datos → Supabase",
        "desc": ("Normaliza Q10 → carga a Supabase → aprobación → Emoflow → exporta JSON → Sheets. "
                 "Actualiza el panel de datos (Supabase / Vercel)."),
        "justificacion": ("El panel de datos es lo que usa el equipo para el análisis del día a día, "
                           "y lo que ve cualquiera con el link del panel. Sin esta corrida, el panel "
                           "solo se actualiza con el ciclo automático de n8n (diario 9:45 + sync cada "
                           "2-4h). Úsalo si necesitas reflejar un cambio reciente (una matrícula, un "
                           "retiro) antes de la próxima corrida automática — por ejemplo, para mostrarle "
                           "algo actualizado a Samuel/Lina en el momento."),
        "pesado": True,
        "efecto": "Escribe en Supabase y en Google Sheets. Consume egress de Supabase.",
        "lock": None,
        "steps": [
            _paso(os.path.join(ROOT, "scripts", "panel-datos"),
                  "normalize_q10_data.py", "&&", "python", "cargar_supabase.py",
                  "&&", "python", "sync_aprobacion_supabase.py",
                  "&&", "python", "sync_emoflow_api.py",
                  "&&", "python", "export_supabase_json.py",
                  "&&", "python", "sync_supabase_to_sheets.py"),
        ],
    },
    {
        "clave": "asistencia",
        "corto": "Asistencia",
        "telegram": "/actualizar asistencia",
        "nombre": "Asistencia Zoom → Supabase",
        "desc": "Sincroniza la asistencia validada de Zoom y recalcula el promedio por estudiante en Supabase.",
        "justificacion": ("El % de asistencia que se ve en el panel de riesgo y en el Panel de Control "
                           "JC/MR depende de esta sincronización. Sin ella, queda con el dato de la "
                           "última corrida (el sync automático es diario a las 17:45). Úsalo justo "
                           "después de dictar una clase si quieres ver la asistencia reflejada de "
                           "inmediato, en vez de esperar al ciclo de la tarde."),
        "pesado": False,
        "efecto": "Escribe la asistencia en Supabase.",
        "lock": None,
        "steps": [
            _paso(ROOT, "scripts/panel-datos/sync_asistencia_supabase.py",
                  "&&", "python", "scripts/panel-datos/calcular_asistencia_promedio.py"),
        ],
    },
    {
        "clave": "mr",
        "corto": "MR",
        "telegram": "/actualizar mr",
        "nombre": "Form MR2024 → BD Mujeres ROFÉ",
        "desc": "Pasa las respuestas del formulario MR2024 a la pestaña General de la BD-Mujeres ROFÉ (cruce por cédula).",
        "justificacion": ("La BD-Mujeres ROFÉ es la fuente de los datos sociodemográficos y de "
                           "seguimiento de Mujeres ROFÉ; el resto del pipeline (panel, correos) lee de "
                           "ahí. Sin esta corrida, las respuestas nuevas del formulario quedan sin "
                           "reflejarse — invisibles para todo lo demás. El sync automático es diario "
                           "9:30 am; úsalo si sabes que llegaron respuestas nuevas y no quieres esperar "
                           "hasta el otro día."),
        "pesado": False,
        "efecto": "Escribe en la BD-Mujeres ROFÉ (Google Sheets).",
        "lock": None,
        "steps": [_paso(os.path.join(ROOT, "scripts", "mr-actualizacion-datos"), "actualizar_bd_mr.py")],
    },
    {
        "clave": "rebotes",
        "corto": "Rebotes",
        "telegram": "/actualizar rebotes",
        "nombre": "Captura rebotes de correo",
        "desc": "Revisa la bandeja y marca los correos rebotados (hard/soft) de las campañas de Mujeres ROFÉ.",
        "justificacion": ("Sin depurar los rebotes, las campañas siguen intentando enviar a direcciones "
                           "que ya rebotaron (hard) o acumulan fallos silenciosos (soft) — eso puede "
                           "dañar la reputación de la cuenta de envío con el tiempo. Úsalo después de "
                           "cada campaña masiva, o si acabas de corregir una dirección y quieres "
                           "liberarla para el próximo envío."),
        "pesado": False,
        "efecto": "Lee la bandeja de correo y actualiza el estado de rebotes.",
        "lock": None,
        "steps": [_paso(ROOT, "scripts/mujeres-rofe-correos/capturar_rebotes.py")],
    },
    {
        "clave": "alerta",
        "corto": "Alerta",
        "telegram": "/actualizar alerta",
        "nombre": "Alerta de deserción",
        "desc": "Recalcula la lista de estudiantes en riesgo (JC) desde Supabase y genera el CSV / alerta.",
        "justificacion": ("Esta lista es la que usa el equipo para decidir a quién contactar por riesgo "
                           "de deserción. Si no se recalcula, puede no reflejar avances o retiros "
                           "recientes — contactarías a alguien que ya se puso al día, o te perderías a "
                           "alguien nuevo en riesgo. El workflow automático corre los lunes 7:00 am; "
                           "úsalo antes de una ronda de seguimiento para trabajar con la lista más "
                           "actual posible."),
        "pesado": False,
        "efecto": "Lee de Supabase y genera el reporte de deserción.",
        "lock": None,
        "steps": [_paso(ROOT, "scripts/panel-datos/alerta_desercion.py", "--csv")],
    },
    {
        "clave": "backfill",
        "corto": "Backfill",
        "telegram": "/actualizar backfill",
        "nombre": "Grabaciones Zoom → YouTube/Drive",
        "desc": "Sube las grabaciones recientes de Zoom (últimos 2 días) a YouTube (MR) / Drive (NOVA).",
        "justificacion": ("Normalmente el webhook de Zoom sube la grabación sola al terminar la clase. "
                           "Esta corrida es la red de seguridad para cuando ese proceso automático "
                           "falla o la clase no disparó el evento esperado. Úsalo si notas que falta "
                           "una grabación reciente en YouTube o Drive."),
        "pesado": False,
        "efecto": "SUBE videos a YouTube / Google Drive (público según el canal). Puede tardar por el peso de los videos.",
        "lock": None,
        "steps": [_paso(ROOT, "scripts\\zoom-youtube\\backfill_grabaciones.py", "--dias", "2")],
    },
]


class Botonera(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Botonera de Comandos — ROFÉ / Jóvenes creaTIvos")
        self.geometry("1000x820")
        self.minsize(760, 560)
        self.configure(bg=GRIS_BG)
        self.corriendo = False
        self._cola = queue.Queue()
        self._botones = []
        self._tarjetas = {}  # clave -> frame (para la barra navegable)

        self._construir_header()
        self._construir_nav()
        self._construir_area_scroll()
        for cmd in COMANDOS:
            self._agregar_tarjeta(cmd)
        self._construir_consola()
        self.after(100, self._pump)

    # ── UI ───────────────────────────────────────────────────────────────
    def _construir_header(self):
        top = tk.Frame(self, bg=NAVY)
        top.pack(fill="x")
        tk.Label(top, text="Botonera de Comandos", bg=NAVY, fg="white",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
        tk.Label(top, text="Los mismos comandos del bot de Telegram, con un clic. "
                           "Corren en esta PC.", bg=NAVY, fg="#c9c7e0",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(0, 12))

    def _construir_nav(self):
        """Barra navegable: un botón corto por comando que salta a su tarjeta."""
        nav = tk.Frame(self, bg=NAV_BG)
        nav.pack(fill="x")
        tk.Label(nav, text="Ir a:", bg=NAV_BG, fg="#9d9ac0",
                 font=("Segoe UI", 9)).pack(side="left", padx=(14, 6), pady=8)
        for cmd in COMANDOS:
            etiqueta = cmd["corto"] + (" ⚠" if cmd["pesado"] else "")
            b = tk.Button(nav, text=etiqueta, bg=NAV_BG, fg="white",
                          activebackground=ROSA, activeforeground="white",
                          font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                          bd=0, padx=10, pady=4,
                          command=lambda c=cmd["clave"]: self._ir_a(c))
            b.pack(side="left", padx=3, pady=6)

    def _construir_area_scroll(self):
        """Canvas + scrollbar: la lista de tarjetas es desplazable (rueda del mouse
        y barra lateral), para que crecer a más comandos no rompa la ventana."""
        outer = tk.Frame(self, bg=GRIS_BG)
        outer.pack(fill="both", expand=True, padx=0, pady=(6, 0))

        self.canvas = tk.Canvas(outer, bg=GRIS_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(12, 0))
        scrollbar.pack(side="right", fill="y")

        self.inner = tk.Frame(self.canvas, bg=GRIS_BG)
        self._inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._inner_id, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._rueda)

    def _rueda(self, evento):
        self.canvas.yview_scroll(int(-evento.delta / 40), "units")

    def _ir_a(self, clave):
        self.update_idletasks()
        card = self._tarjetas[clave]
        total = max(self.inner.winfo_height(), 1)
        frac = card.winfo_y() / total
        self.canvas.yview_moveto(max(0.0, frac - 0.01))

    def _agregar_tarjeta(self, cmd):
        card = tk.Frame(self.inner, bg=GRIS_CARD, bd=1, relief="solid",
                        highlightbackground="#e0e0ea", highlightthickness=1)
        card.pack(fill="x", padx=10, pady=6)
        self._tarjetas[cmd["clave"]] = card

        cab = tk.Frame(card, bg=GRIS_CARD)
        cab.pack(fill="x", padx=14, pady=(12, 2))
        tk.Label(cab, text=cmd["nombre"], bg=GRIS_CARD, fg=NAVY,
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(side="left")
        if cmd["pesado"]:
            tk.Label(cab, text=" PESADO ", bg=AMBAR, fg="white",
                     font=("Segoe UI", 8, "bold")).pack(side="right")

        tk.Label(card, text=cmd["telegram"], bg=GRIS_CARD, fg=ROSA,
                 font=("Consolas", 10, "bold"), anchor="w").pack(fill="x", padx=14)

        tk.Label(card, text="Qué hace", bg=GRIS_CARD, fg=GRIS_SUAVE,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=14, pady=(8, 0))
        tk.Label(card, text=cmd["desc"], bg=GRIS_CARD, fg=GRIS_TXT,
                 font=("Segoe UI", 9), anchor="w", justify="left",
                 wraplength=860).pack(fill="x", padx=14)

        tk.Label(card, text="Por qué importa / cuándo usarlo", bg=GRIS_CARD, fg=GRIS_SUAVE,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=14, pady=(8, 0))
        tk.Label(card, text=cmd["justificacion"], bg=GRIS_CARD, fg=GRIS_TXT,
                 font=("Segoe UI", 9), anchor="w", justify="left",
                 wraplength=860).pack(fill="x", padx=14, pady=(0, 4))

        btn = tk.Button(card, text="Ejecutar  ▶", bg=NAVY, fg="white",
                        activebackground=ROSA, activeforeground="white",
                        font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
                        command=lambda c=cmd: self._on_ejecutar(c))
        btn.pack(anchor="e", padx=14, pady=(4, 14))
        self._botones.append(btn)

    def _construir_consola(self):
        barra = tk.Frame(self, bg=GRIS_BG)
        barra.pack(fill="x", padx=16, pady=(4, 0))
        tk.Label(barra, text="Salida", bg=GRIS_BG, fg=NAVY,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(barra, text="Limpiar", command=self._limpiar, relief="flat",
                  bg="#e0e0ea", cursor="hand2").pack(side="right")
        self.estado = tk.Label(barra, text="Listo.", bg=GRIS_BG, fg=GRIS_SUAVE,
                               font=("Segoe UI", 9))
        self.estado.pack(side="right", padx=10)

        self.consola = scrolledtext.ScrolledText(
            self, height=12, bg=CONSOLA_BG, fg=CONSOLA_FG, insertbackground=CONSOLA_FG,
            font=("Consolas", 9), relief="flat", wrap="word", state="disabled")
        self.consola.pack(fill="both", expand=False, padx=16, pady=(2, 14))

    # ── Ejecución ────────────────────────────────────────────────────────
    def _on_ejecutar(self, cmd):
        if self.corriendo:
            messagebox.showinfo("En curso", "Ya hay un comando corriendo. Espera a que termine.")
            return
        if not messagebox.askyesno(
            "Confirmar", f"¿Ejecutar «{cmd['nombre']}»?\n\n{cmd['efecto']}"):
            return
        self.corriendo = True
        for b in self._botones:
            b.config(state="disabled")
        self.estado.config(text=f"Ejecutando: {cmd['nombre']}…", fg=AMBAR)
        self._log(f"\n{'='*70}\n▶ {cmd['nombre']}  ({cmd['telegram']})\n{'='*70}")
        threading.Thread(target=self._worker, args=(cmd,), daemon=True).start()

    def _worker(self, cmd):
        ok = True
        adquirido = False
        try:
            if cmd["lock"]:
                self._cola.put(("log", f"🔒 Pidiendo lock: {', '.join(cmd['lock'])}…"))
                r = subprocess.run(
                    [sys.executable, LOCK_CLI, "acquire", *cmd["lock"],
                     "--execution-id", "", "--workflow-id", "gui-botonera"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
                data = {}
                try:
                    data = json.loads((r.stdout or "").strip().splitlines()[-1])
                except Exception:
                    pass
                if not data.get("acquired"):
                    self._cola.put(("log", "⚠️ No se pudo iniciar: hay otro pipeline pesado en curso "
                                           f"(bloqueado por «{data.get('blocked_by', '?')}»). Intenta en unos minutos."))
                    self._cola.put(("fin", (cmd, False)))
                    return
                adquirido = True

            for step in cmd["steps"]:
                self._cola.put(("log", f"\n$ {step}"))
                proc = subprocess.Popen(
                    step, shell=True, cwd=ROOT, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                    errors="replace", bufsize=1,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                for linea in proc.stdout:
                    self._cola.put(("log", linea.rstrip("\n")))
                proc.wait()
                if proc.returncode != 0:
                    self._cola.put(("log", f"⚠️ Falló (exit {proc.returncode}). Se detiene la cadena."))
                    ok = False
                    break
        except Exception as e:  # noqa: BLE001
            self._cola.put(("log", f"⚠️ Error inesperado: {e}"))
            ok = False
        finally:
            if adquirido:
                subprocess.run(
                    [sys.executable, LOCK_CLI, "release", *cmd["lock"], "--execution-id", ""],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
                self._cola.put(("log", "🔓 Lock liberado."))
            self._cola.put(("log", "\n✅ Completado." if ok else "\n⚠️ Terminó con errores."))
            self._cola.put(("fin", (cmd, ok)))

    # ── Puente hilo → UI ─────────────────────────────────────────────────
    def _pump(self):
        try:
            while True:
                tipo, dato = self._cola.get_nowait()
                if tipo == "log":
                    self._log(dato)
                elif tipo == "fin":
                    cmd, ok = dato
                    self.corriendo = False
                    for b in self._botones:
                        b.config(state="normal")
                    self.estado.config(
                        text=(f"✔ {cmd['nombre']} — completado" if ok
                              else f"✖ {cmd['nombre']} — con errores"),
                        fg=(VERDE if ok else "#c62828"))
        except queue.Empty:
            pass
        self.after(100, self._pump)

    def _log(self, texto):
        self.consola.config(state="normal")
        self.consola.insert("end", texto + "\n")
        self.consola.see("end")
        self.consola.config(state="disabled")

    def _limpiar(self):
        self.consola.config(state="normal")
        self.consola.delete("1.0", "end")
        self.consola.config(state="disabled")


if __name__ == "__main__":
    Botonera().mainloop()
