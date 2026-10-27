r"""
GUI.py — Interfaz gráfica (tkinter + matplotlib) para osciladores acoplados.

La GUI sólo CONSUME la API pública de la librería `osciladores_acoplados`.
La lógica no sabe que esta interfaz existe: podría reemplazarse por una
aplicación web, un notebook o una línea de comandos sin tocar core.py.

Preparación (una vez, desde la carpeta del proyecto):
    python -m venv .venv
    .venv\Scripts\Activate.ps1         (Linux/macOS: source .venv/bin/activate)
    python -m pip install -e ".[gui]"

Ejecutar:   python GUI.py
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure

try:
    from osciladores_acoplados import (FabricaIntegradores, Simulador,
                                       SistemaOsciladores)
except ImportError:
    raise SystemExit(
        "No se encontró la librería 'osciladores_acoplados'.\n"
        "Desde la carpeta del proyecto, con el entorno virtual activo, ejecute:\n"
        '    python -m pip install -e ".[gui]"'
    ) from None

COLORES = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
           "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]


def leer_lista(texto: str, nombre: str) -> np.ndarray:
    """Convierte '1, 2.5, 3' en un arreglo. Error claro si no se puede."""
    try:
        valores = [float(s) for s in texto.replace(";", ",").split(",")
                   if s.strip()]
    except ValueError:
        raise ValueError(f"«{nombre}» debe ser una lista de números "
                         f"separados por comas.") from None
    if not valores:
        raise ValueError(f"«{nombre}» está vacío.")
    return np.array(valores)


def leer_numero(texto: str, nombre: str) -> float:
    try:
        return float(texto)
    except ValueError:
        raise ValueError(f"«{nombre}» debe ser un número.") from None


class PanelGrafica(ttk.Frame):
    """Una figura de matplotlib incrustada en tkinter, con barra de herramientas."""

    def __init__(self, padre, filas=1):
        super().__init__(padre)
        self.figura = Figure(figsize=(7, 5), dpi=100, layout="constrained")
        self.ejes = [self.figura.add_subplot(filas, 1, i + 1)
                     for i in range(filas)]
        self.lienzo = FigureCanvasTkAgg(self.figura, master=self)
        NavigationToolbar2Tk(self.lienzo, self).update()
        self.lienzo.get_tk_widget().pack(fill="both", expand=True)

    def limpiar(self):
        for eje in self.ejes:
            eje.clear()

    def dibujar(self):
        self.lienzo.draw_idle()


class AplicacionOsciladores(tk.Tk):
    """Ventana principal. Patrón: la vista lee datos, llama a la lógica y
    muestra el Resultado que recibe por medio de un observador."""

    def __init__(self):
        super().__init__()
        self.title("Osciladores armónicos acoplados")
        self.geometry("1200x760")
        self.minsize(950, 600)

        self.sistema = None
        self.resultado = None
        self.simulador = None
        self._id_animacion = None
        self._cuadro = 0

        self._crear_panel_entrada()
        self._crear_pestanas()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    # ------------------------------------------------------------------ UI --
    def _crear_panel_entrada(self):
        panel = ttk.LabelFrame(self, text="Parámetros", padding=10)
        panel.pack(side="left", fill="y", padx=8, pady=8)

        self.var = {
            "masas": tk.StringVar(value="1, 1, 1"),
            "constantes": tk.StringVar(value="10, 10, 10, 10"),
            "x0": tk.StringVar(value="0.5, 0, 0"),
            "v0": tk.StringVar(value="0, 0, 0"),
            "t_final": tk.StringVar(value="20"),
            "dt": tk.StringVar(value="0.01"),
        }
        etiquetas = {
            "masas": "Masas m_i (kg)  [N valores]",
            "constantes": "Constantes k_i (N/m)  [N+1 valores]\n"
                          "(pared–m1, m1–m2, …, mN–pared; 0 = libre)",
            "x0": "Posiciones iniciales x_i(0) (m)",
            "v0": "Velocidades iniciales v_i(0) (m/s)",
            "t_final": "Tiempo final (s)",
            "dt": "Paso de tiempo dt (s)",
        }
        for clave, texto in etiquetas.items():
            ttk.Label(panel, text=texto, justify="left").pack(anchor="w",
                                                              pady=(6, 0))
            ttk.Entry(panel, textvariable=self.var[clave], width=34).pack(
                fill="x")

        ttk.Label(panel, text="Método de solución (Strategy)").pack(
            anchor="w", pady=(10, 0))
        self.var_metodo = tk.StringVar(
            value=FabricaIntegradores.disponibles()[0])
        ttk.Combobox(panel, textvariable=self.var_metodo, state="readonly",
                     values=FabricaIntegradores.disponibles()).pack(fill="x")

        ttk.Button(panel, text="▶  Simular", command=self.simular).pack(
            fill="x", pady=(14, 4))
        ttk.Button(panel, text="Comparar energía de todos los métodos",
                   command=self.comparar_metodos).pack(fill="x", pady=4)

        marco_modo = ttk.Frame(panel)
        marco_modo.pack(fill="x", pady=4)
        ttk.Label(marco_modo, text="Excitar modo #").pack(side="left")
        self.var_modo = tk.IntVar(value=1)
        ttk.Spinbox(marco_modo, from_=1, to=50, width=4,
                    textvariable=self.var_modo).pack(side="left", padx=4)
        ttk.Button(marco_modo, text="Aplicar a x(0)",
                   command=self.excitar_modo).pack(side="left", fill="x",
                                                   expand=True)

        ttk.Button(panel, text="Guardar resultado en CSV",
                   command=self.guardar_csv).pack(fill="x", pady=4)

        self.var_estado = tk.StringVar(value="Listo.")
        ttk.Label(panel, textvariable=self.var_estado, wraplength=260,
                  foreground="#555").pack(anchor="w", pady=(12, 0))

    def _crear_pestanas(self):
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(side="right", fill="both", expand=True,
                           padx=8, pady=8)

        self.graf_pos = PanelGrafica(self.pestanas)
        self.graf_energia = PanelGrafica(self.pestanas)
        self.graf_modos = PanelGrafica(self.pestanas)

        marco_anim = ttk.Frame(self.pestanas)
        self.lienzo_anim = tk.Canvas(marco_anim, background="white",
                                     highlightthickness=0)
        self.lienzo_anim.pack(fill="both", expand=True)
        controles = ttk.Frame(marco_anim)
        controles.pack(fill="x", pady=4)
        ttk.Button(controles, text="▶ Animar",
                   command=self.iniciar_animacion).pack(side="left", padx=4)
        ttk.Button(controles, text="■ Detener",
                   command=self.detener_animacion).pack(side="left")
        ttk.Label(controles, text="  Velocidad:").pack(side="left")
        self.var_velocidad = tk.DoubleVar(value=1.0)
        ttk.Scale(controles, from_=0.1, to=4, variable=self.var_velocidad,
                  orient="horizontal", length=180).pack(side="left")

        self.pestanas.add(self.graf_pos, text="Posiciones x_i(t)")
        self.pestanas.add(self.graf_energia, text="Energía")
        self.pestanas.add(marco_anim, text="Animación")
        self.pestanas.add(self.graf_modos, text="Modos normales")

    # -------------------------------------------------------- lectura datos --
    def _leer_sistema(self) -> SistemaOsciladores:
        masas = leer_lista(self.var["masas"].get(), "Masas")
        ks = leer_lista(self.var["constantes"].get(), "Constantes")
        return SistemaOsciladores(masas, ks)  # la lógica valida coherencia

    def _leer_condiciones(self):
        x0 = leer_lista(self.var["x0"].get(), "x(0)")
        v0 = leer_lista(self.var["v0"].get(), "v(0)")
        t_final = leer_numero(self.var["t_final"].get(), "Tiempo final")
        dt = leer_numero(self.var["dt"].get(), "dt")
        if t_final / max(dt, 1e-12) > 2_000_000:
            raise ValueError("Demasiados pasos: aumente dt o reduzca t_final.")
        return x0, v0, t_final, dt

    # ------------------------------------------------------------ acciones --
    def simular(self):
        self.detener_animacion()
        try:
            self.sistema = self._leer_sistema()
            x0, v0, t_final, dt = self._leer_condiciones()
            estrategia = FabricaIntegradores.crear(self.var_metodo.get())
            self.simulador = Simulador(self.sistema, estrategia)
            self.simulador.suscribir(self._al_recibir_resultado)  # observador
            self.simulador.ejecutar(x0, v0, t_final, dt)
        except (ValueError, IndexError) as error:
            messagebox.showerror("Datos inválidos", str(error))

    def _al_recibir_resultado(self, resultado):
        """Callback que la lógica invoca al terminar (patrón Observador)."""
        self.resultado = resultado
        self._graficar_posiciones()
        self._graficar_energia([resultado])
        self._graficar_modos()
        self._dibujar_cuadro(0)
        err = np.max(np.abs(resultado.error_energia_relativo))
        self.var_estado.set(f"{resultado.metodo}: {resultado.t.size} instantes."
                            f"\nMáx. |ΔE/E₀| = {err:.2e}")

    def comparar_metodos(self):
        try:
            sistema = self._leer_sistema()
            x0, v0, t_final, dt = self._leer_condiciones()
            simulador = Simulador(sistema)
            resultados = []
            for nombre in FabricaIntegradores.disponibles():
                simulador.estrategia = FabricaIntegradores.crear(nombre)
                resultados.append(simulador.ejecutar(x0, v0, t_final, dt))
        except (ValueError, IndexError) as error:
            messagebox.showerror("Datos inválidos", str(error))
            return
        self._graficar_energia(resultados)
        self.pestanas.select(self.graf_energia)
        self.var_estado.set("Comparación: mismo sistema, misma condición "
                            "inicial, distinta estrategia.")

    def excitar_modo(self):
        try:
            sistema = self._leer_sistema()
            j = int(self.var_modo.get()) - 1
            amp = np.max(np.abs(leer_lista(self.var["x0"].get(), "x(0)")))
            x0 = sistema.condicion_modo(j, amplitud=amp if amp > 0 else 0.5)
        except (ValueError, IndexError, tk.TclError) as error:
            messagebox.showerror("Modo inválido", str(error))
            return
        self.var["x0"].set(", ".join(f"{v:.4g}" for v in x0))
        self.var["v0"].set(", ".join("0" for _ in x0))
        self.simular()

    def guardar_csv(self):
        if self.resultado is None:
            messagebox.showinfo("Sin datos", "Primero ejecute una simulación.")
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if ruta:
            self.resultado.a_csv(ruta)
            self.var_estado.set(f"Guardado en {ruta}")

    # ------------------------------------------------------------ gráficas --
    def _graficar_posiciones(self):
        r = self.resultado
        self.graf_pos.limpiar()
        eje = self.graf_pos.ejes[0]
        for i in range(r.x.shape[1]):
            eje.plot(r.t, r.x[:, i], color=COLORES[i % 10],
                     label=f"x{i + 1}")
        eje.set_xlabel("t (s)")
        eje.set_ylabel("desplazamiento (m)")
        eje.set_title(f"Posiciones — {r.metodo}")
        eje.grid(alpha=0.3)
        eje.legend(loc="upper right", ncol=min(5, r.x.shape[1]))
        self.graf_pos.dibujar()

    def _graficar_energia(self, resultados):
        self.graf_energia.limpiar()
        eje = self.graf_energia.ejes[0]
        for k, r in enumerate(resultados):
            eje.plot(r.t, r.error_energia_relativo, color=COLORES[k % 10],
                     label=r.metodo)
        eje.set_xlabel("t (s)")
        eje.set_ylabel("(E − E₀) / E₀")
        eje.set_title("Conservación de la energía")
        eje.grid(alpha=0.3)
        eje.legend()
        if len(resultados) > 1:
            eje.set_yscale("symlog", linthresh=1e-8)
        self.graf_energia.dibujar()

    def _graficar_modos(self):
        w, phi = self.sistema.modos_normales()
        self.graf_modos.limpiar()
        eje = self.graf_modos.ejes[0]
        indices = np.arange(1, self.sistema.n + 1)
        for j in range(self.sistema.n):
            forma = phi[:, j] / np.max(np.abs(phi[:, j]))
            eje.plot(indices, forma, "o-", color=COLORES[j % 10],
                     label=f"Modo {j + 1}: ω = {w[j]:.3f} rad/s, "
                           f"f = {w[j] / (2 * np.pi):.3f} Hz")
        eje.axhline(0, color="#999", lw=0.8)
        eje.set_xticks(indices)
        eje.set_xlabel("masa i")
        eje.set_ylabel("amplitud relativa")
        eje.set_title("Formas de los modos normales")
        eje.grid(alpha=0.3)
        eje.legend(fontsize=8)
        self.graf_modos.dibujar()

    # ----------------------------------------------------------- animación --
    def iniciar_animacion(self):
        if self.resultado is None:
            messagebox.showinfo("Sin datos", "Primero ejecute una simulación.")
            return
        self.detener_animacion()
        self._cuadro = 0
        self._animar()

    def detener_animacion(self):
        if self._id_animacion is not None:
            self.after_cancel(self._id_animacion)
            self._id_animacion = None

    def _animar(self):
        r = self.resultado
        intervalo_ms = 30
        dt = r.t[1] - r.t[0]
        salto = max(1, int(round(self.var_velocidad.get()
                                 * intervalo_ms / 1000 / dt)))
        self._dibujar_cuadro(self._cuadro)
        self._cuadro = (self._cuadro + salto) % r.t.size
        self._id_animacion = self.after(intervalo_ms, self._animar)

    @staticmethod
    def _resorte(x1, x2, y, vueltas=8, ancho=10):
        """Puntos de una línea en zigzag entre x1 y x2."""
        xs = np.linspace(x1, x2, 2 * vueltas + 3)
        ys = np.full_like(xs, y)
        ys[1:-1:2] += ancho
        ys[2:-1:2] -= ancho
        ys[-2] = y
        return [c for par in zip(xs, ys) for c in par]

    def _dibujar_cuadro(self, i):
        c = self.lienzo_anim
        c.delete("all")
        r, sis = self.resultado, self.sistema
        if r is None:
            return
        ancho = max(c.winfo_width(), 400)
        alto = max(c.winfo_height(), 200)
        n = sis.n
        margen, y = 40, alto / 2
        separacion = (ancho - 2 * margen) / (n + 1)
        escala = 0.35 * separacion / max(np.max(np.abs(r.x)), 1e-12)
        lado = min(50, 0.45 * separacion)
        k = sis.constantes

        pos = margen + separacion * np.arange(1, n + 1) + escala * r.x[i]
        # paredes
        for xp in (margen, ancho - margen):
            c.create_line(xp, y - 60, xp, y + 60, width=4, fill="#333")
        # resortes (k = 0 no se dibuja)
        bordes = [margen] + list(pos) + [ancho - margen]
        for j in range(n + 1):
            if k[j] == 0:
                continue
            x1 = bordes[j] + (lado / 2 if j > 0 else 0)
            x2 = bordes[j + 1] - (lado / 2 if j < n else 0)
            c.create_line(*self._resorte(x1, x2, y), fill="#666", width=2)
        # masas: el tamaño crece con la masa
        m_rel = np.sqrt(sis.masas / sis.masas.max())
        for j in range(n):
            h = lado * (0.6 + 0.4 * m_rel[j])
            c.create_rectangle(pos[j] - h / 2, y - h / 2, pos[j] + h / 2,
                               y + h / 2, fill=COLORES[j % 10], outline="")
            c.create_text(pos[j], y + h / 2 + 14, text=f"m{j + 1}")
        c.create_text(10, 14, anchor="w", font=("TkDefaultFont", 11),
                      text=f"t = {r.t[i]:.2f} s   ({r.metodo})")

    def _cerrar(self):
        self.detener_animacion()
        self.destroy()


if __name__ == "__main__":
    AplicacionOsciladores().mainloop()
