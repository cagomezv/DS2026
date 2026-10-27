r"""
GUI.py — Interfaz gráfica (tkinter + matplotlib) del simulador de circuitos cuánticos.

La GUI sólo CONSUME la API pública de la librería `circuitos_cuanticos`.
La lógica no sabe que esta interfaz existe.

Preparación (una vez, desde la carpeta del proyecto):
    python -m venv .venv
    .venv\Scripts\Activate.ps1         (Linux/macOS: source .venv/bin/activate)
    python -m pip install -e ".[gui]"

Ejecutar:   python GUI.py
"""

import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:
    from circuitos_cuanticos import (CatalogoCircuitos, Circuito, CNOT, CZ,
                                     Difusion, FabricaPuertas, Medir, Oraculo,
                                     SWAP, Toffoli)
except ImportError:
    raise SystemExit(
        "No se encontró la librería 'circuitos_cuanticos'.\n"
        "Desde la carpeta del proyecto, con el entorno virtual activo, ejecute:\n"
        '    python -m pip install -e ".[gui]"'
    ) from None

AZUL, NARANJA, GRIS, TINTA = "#2F6FB3", "#D85A30", "#B8B2A6", "#14213D"


def leer_enteros(texto: str, nombre: str) -> list:
    try:
        return [int(s) for s in texto.replace(";", ",").split(",") if s.strip()]
    except ValueError:
        raise ValueError(f"«{nombre}» debe ser una lista de enteros separados por comas.") from None


def leer_numero(texto: str, nombre: str) -> float:
    try:
        return float(texto)
    except ValueError:
        raise ValueError(f"«{nombre}» debe ser un número.") from None


class PanelGrafica(ttk.Frame):
    """Figura de matplotlib incrustada en tkinter."""

    def __init__(self, padre):
        super().__init__(padre)
        self.figura = Figure(figsize=(7, 3.6), dpi=100, layout="constrained")
        self.eje = self.figura.add_subplot()
        self.lienzo = FigureCanvasTkAgg(self.figura, master=self)
        self.lienzo.get_tk_widget().pack(fill="both", expand=True)

    def dibujar(self):
        self.lienzo.draw_idle()


class AplicacionCuantica(tk.Tk):
    """Ventana principal: construye circuitos, los ejecuta paso a paso y muestra el estado."""

    def __init__(self):
        super().__init__()
        self.title("Simulador de circuitos cuánticos")
        self.geometry("1280x820")
        self.minsize(1000, 650)
        self.circuito = None
        self.ultimo_conteo = None
        self._crear_panel()
        self._crear_area_derecha()
        self.construir()

    # ------------------------------------------------------------------ UI --
    def _crear_panel(self):
        p = ttk.Frame(self, padding=10)
        p.pack(side="left", fill="y")

        caja = ttk.LabelFrame(p, text="1. Elegir un ejemplo", padding=8)
        caja.pack(fill="x")
        self.var_ejemplo = tk.StringVar(value="Estado de Bell")
        combo = ttk.Combobox(caja, textvariable=self.var_ejemplo, state="readonly",
                             values=CatalogoCircuitos.disponibles() + ["Circuito vacío"])
        combo.pack(fill="x")
        combo.bind("<<ComboboxSelected>>", lambda e: self._mostrar_parametros())

        self.marco_param = ttk.Frame(caja)
        self.marco_param.pack(fill="x", pady=6)
        self.var_n = tk.IntVar(value=3)
        self.var_marcado = tk.StringVar(value="101")
        self.var_iter = tk.StringVar(value="")
        self.var_theta = tk.StringVar(value="1.0")
        self.var_phi = tk.StringVar(value="0.5")
        self._mostrar_parametros()
        ttk.Button(caja, text="Construir circuito", command=self.construir).pack(fill="x")

        caja = ttk.LabelFrame(p, text="2. Agregar una puerta", padding=8)
        caja.pack(fill="x", pady=8)
        self.var_puerta = tk.StringVar(value="H")
        ttk.Combobox(caja, textvariable=self.var_puerta, state="readonly", width=10,
                     values=FabricaPuertas.disponibles()).grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(caja, text="qubits (ej. 0, 1)").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.var_qubits = tk.StringVar(value="0")
        ttk.Entry(caja, textvariable=self.var_qubits, width=10).grid(row=1, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(caja, text="ángulo (rad)").grid(row=2, column=0, sticky="w")
        self.var_angulo = tk.StringVar(value="0.785")
        ttk.Entry(caja, textvariable=self.var_angulo, width=10).grid(row=2, column=1, sticky="ew")
        ttk.Button(caja, text="Agregar al final", command=self.agregar_puerta).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        caja.columnconfigure(1, weight=1)

        caja = ttk.LabelFrame(p, text="3. Ejecutar (patrón Command)", padding=8)
        caja.pack(fill="x")
        fila = ttk.Frame(caja)
        fila.pack(fill="x")
        for texto, accion in [("⏮", self.reiniciar), ("◀ Deshacer", self.deshacer),
                              ("Paso ▶", self.paso), ("Todo ▶▶", self.ejecutar)]:
            ttk.Button(fila, text=texto, command=accion).pack(side="left", expand=True, fill="x")

        caja = ttk.LabelFrame(p, text="4. Medir el registro", padding=8)
        caja.pack(fill="x", pady=8)
        self.var_disparos = tk.IntVar(value=1000)
        ttk.Spinbox(caja, from_=1, to=100000, increment=100, width=8,
                    textvariable=self.var_disparos).pack(side="left")
        ttk.Button(caja, text="Medir N veces", command=self.medir).pack(side="left", fill="x", expand=True, padx=(6, 0))

        self.var_estado = tk.StringVar(value="")
        ttk.Label(p, textvariable=self.var_estado, wraplength=290, foreground="#555",
                  justify="left").pack(anchor="w", pady=(8, 0))

    def _mostrar_parametros(self):
        for w in self.marco_param.winfo_children():
            w.destroy()
        ej = self.var_ejemplo.get()

        def campo(texto, var, fila):
            ttk.Label(self.marco_param, text=texto).grid(row=fila, column=0, sticky="w")
            ttk.Entry(self.marco_param, textvariable=var, width=10).grid(row=fila, column=1, sticky="ew")

        if ej in ("GHZ", "Grover", "Circuito vacío"):
            ttk.Label(self.marco_param, text="número de qubits").grid(row=0, column=0, sticky="w")
            ttk.Spinbox(self.marco_param, from_=1, to=8, width=8,
                        textvariable=self.var_n).grid(row=0, column=1, sticky="ew")
        if ej == "Grover":
            campo("estado buscado (bits)", self.var_marcado, 1)
            campo("iteraciones (vacío = óptimo)", self.var_iter, 2)
        if ej == "Teleportación":
            campo("θ del estado a enviar", self.var_theta, 0)
            campo("φ del estado a enviar", self.var_phi, 1)
        self.marco_param.columnconfigure(1, weight=1)

    def _crear_area_derecha(self):
        d = ttk.Frame(self, padding=(0, 10, 10, 10))
        d.pack(side="right", fill="both", expand=True)
        marco = ttk.LabelFrame(d, text="Circuito (gris = puertas pendientes)", padding=4)
        marco.pack(fill="x")
        self.lienzo = tk.Canvas(marco, height=260, background="white", highlightthickness=0)
        barra = ttk.Scrollbar(marco, orient="horizontal", command=self.lienzo.xview)
        self.lienzo.configure(xscrollcommand=barra.set)
        self.lienzo.pack(fill="x")
        barra.pack(fill="x")

        self.pestanas = ttk.Notebook(d)
        self.pestanas.pack(fill="both", expand=True, pady=(8, 0))
        self.graf_prob = PanelGrafica(self.pestanas)
        self.graf_medidas = PanelGrafica(self.pestanas)
        marco_texto = ttk.Frame(self.pestanas, padding=8)
        self.texto = tk.Text(marco_texto, font=("Consolas", 12), wrap="word", height=12)
        self.texto.pack(fill="both", expand=True)
        self.pestanas.add(self.graf_prob, text="Probabilidades |a_k|²")
        self.pestanas.add(self.graf_medidas, text="Mediciones")
        self.pestanas.add(marco_texto, text="Estado: ket y Bloch")

    # ------------------------------------------------------------ acciones --
    def construir(self):
        try:
            ej = self.var_ejemplo.get()
            if ej == "Estado de Bell":
                c = CatalogoCircuitos.bell()
            elif ej == "GHZ":
                c = CatalogoCircuitos.ghz(int(self.var_n.get()))
            elif ej == "Teleportación":
                c = CatalogoCircuitos.teleportacion(leer_numero(self.var_theta.get(), "θ"),
                                                    leer_numero(self.var_phi.get(), "φ"))
            elif ej == "Grover":
                n = int(self.var_n.get())
                bits = self.var_marcado.get().strip()
                if len(bits) != n or set(bits) - {"0", "1"}:
                    raise ValueError(f"El estado buscado debe tener {n} bits, por ejemplo {'1' * n}.")
                it = self.var_iter.get().strip()
                c = CatalogoCircuitos.grover(n, int(bits, 2), int(it) if it else None)
            else:
                c = Circuito(int(self.var_n.get()), "Circuito vacío")
        except (ValueError, IndexError, tk.TclError) as error:
            messagebox.showerror("Datos inválidos", str(error))
            return
        self.circuito = c
        self.circuito.suscribir(self._al_cambiar)        # patrón Observador
        self.ultimo_conteo = None
        self._al_cambiar(c)

    def agregar_puerta(self):
        if self.circuito is None:
            return
        try:
            qubits = leer_enteros(self.var_qubits.get(), "qubits")
            puerta = FabricaPuertas.crear(self.var_puerta.get(), *qubits,
                                          angulo=leer_numero(self.var_angulo.get(), "ángulo"))
            self.circuito.agregar(puerta)
        except (ValueError, IndexError, TypeError) as error:
            messagebox.showerror("Puerta inválida", str(error))
            return
        self._al_cambiar(self.circuito)

    def paso(self):
        if self.circuito and not self.circuito.paso():
            self.var_estado.set("No quedan puertas por aplicar.")

    def deshacer(self):
        if self.circuito and not self.circuito.deshacer():
            self.var_estado.set("Ya está en el estado inicial |0…0⟩.")

    def ejecutar(self):
        if self.circuito:
            self.circuito.ejecutar()

    def reiniciar(self):
        if self.circuito:
            self.ultimo_conteo = None
            self.circuito.reiniciar()

    def medir(self):
        if not self.circuito:
            return
        try:
            n = int(self.var_disparos.get())
            self.ultimo_conteo = self.circuito.estado.medir(n)
        except (ValueError, tk.TclError) as error:
            messagebox.showerror("Dato inválido", str(error))
            return
        self._graficar_mediciones()
        self.pestanas.select(self.graf_medidas)

    # ---------------------------------------------------------- observador --
    def _al_cambiar(self, circuito):
        """La lógica llama a esta función después de cada paso."""
        self._dibujar_circuito()
        self._graficar_probabilidades()
        self._mostrar_estado()
        if self.ultimo_conteo is None:
            self._graficar_mediciones()
        c = circuito
        ultima = f"Última: {c.puertas[c.posicion - 1]!r}" if c.posicion else "Estado inicial |0…0⟩"
        self.var_estado.set(f"{c.nombre}\nPaso {c.posicion} de {len(c)}. {ultima}")

    # -------------------------------------------------------------- dibujo --
    def _dibujar_circuito(self):
        cv, c = self.lienzo, self.circuito
        cv.delete("all")
        n, dx, dy, x0, y0 = c.n, 64, min(54, 220 // max(c.n, 1)), 60, 24
        y = lambda q: y0 + q * dy
        ancho = x0 + dx * (len(c) + 1)
        cv.configure(scrollregion=(0, 0, max(ancho, cv.winfo_width()), y(n - 1) + 30))
        for q in range(n):
            cv.create_text(20, y(q), text=f"q{q}", font=("Consolas", 11))
            cv.create_line(x0 - 20, y(q), ancho, y(q), fill="#888")
        for i, p in enumerate(c.puertas):
            x = x0 + dx * i + dx / 2
            col = AZUL if i < c.posicion else GRIS
            self._dibujar_puerta(cv, p, x, y, col)
        xm = x0 + dx * c.posicion
        cv.create_line(xm, y0 - 18, xm, y(n - 1) + 18, fill=NARANJA, width=3)

    def _dibujar_puerta(self, cv, p, x, y, col):
        caja = lambda q1, q2, texto: (
            cv.create_rectangle(x - 20, y(q1) - 17, x + 20, y(q2) + 17, fill=col, outline=""),
            cv.create_text(x, (y(q1) + y(q2)) / 2, text=texto, fill="white",
                           font=("Segoe UI", 11, "bold")))
        punto = lambda q: cv.create_oval(x - 6, y(q) - 6, x + 6, y(q) + 6, fill=col, outline="")
        if isinstance(p, (Oraculo, Difusion)):
            caja(min(p.qubits), max(p.qubits), p.simbolo)
        elif isinstance(p, (CNOT, Toffoli)):
            *controles, obj = p.qubits
            cv.create_line(x, y(min(p.qubits)), x, y(max(p.qubits)), fill=col, width=2)
            for q in controles:
                punto(q)
            cv.create_oval(x - 13, y(obj) - 13, x + 13, y(obj) + 13, outline=col, width=2, fill="white")
            cv.create_line(x - 13, y(obj), x + 13, y(obj), fill=col, width=2)
            cv.create_line(x, y(obj) - 13, x, y(obj) + 13, fill=col, width=2)
        elif isinstance(p, CZ):
            cv.create_line(x, y(min(p.qubits)), x, y(max(p.qubits)), fill=col, width=2)
            for q in p.qubits:
                punto(q)
        elif isinstance(p, SWAP):
            cv.create_line(x, y(min(p.qubits)), x, y(max(p.qubits)), fill=col, width=2)
            for q in p.qubits:
                cv.create_text(x, y(q), text="✕", fill=col, font=("Segoe UI", 14, "bold"))
        else:
            caja(p.qubits[0], p.qubits[0], p.simbolo)
            if isinstance(p, Medir) and p.resultado is not None:
                cv.create_text(x, y(p.qubits[0]) - 26, text=f"→{p.resultado}", fill=NARANJA)

    def _graficar_probabilidades(self):
        e = self.circuito.estado
        prob = e.vector_probabilidades()
        indices = np.arange(prob.size)
        if prob.size > 32:                       # con muchos qubits, sólo las 32 mayores
            indices = np.sort(np.argsort(prob)[-32:])
        ax = self.graf_prob.eje
        ax.clear()
        ax.bar(range(indices.size), prob[indices], color=AZUL)
        ax.set_xticks(range(indices.size), [e.etiqueta(k) for k in indices],
                      rotation=90 if e.n > 4 else 0, fontsize=9)
        ax.set_ylim(0, 1)
        ax.set_ylabel("probabilidad")
        ax.set_title("Probabilidad de cada resultado (regla de Born)")
        ax.grid(axis="y", alpha=0.3)
        self.graf_prob.dibujar()

    def _graficar_mediciones(self):
        ax = self.graf_medidas.eje
        ax.clear()
        if not self.ultimo_conteo:
            ax.text(0.5, 0.5, "Pulse «Medir N veces»", ha="center", va="center",
                    transform=ax.transAxes, color="#777")
        else:
            claves = sorted(self.ultimo_conteo)
            ax.bar(claves, [self.ultimo_conteo[k] for k in claves], color=NARANJA)
            ax.set_ylabel("número de veces")
            ax.set_title(f"{sum(self.ultimo_conteo.values())} mediciones simuladas")
            ax.tick_params(axis="x", rotation=90 if len(claves) > 8 else 0)
            ax.grid(axis="y", alpha=0.3)
        self.graf_medidas.dibujar()

    def _mostrar_estado(self):
        e = self.circuito.estado
        lineas = ["|ψ⟩ = " + e.ket(), "", "Qubit   P(1)    Bloch (x, y, z)        |r|"]
        for q in range(e.n):
            b = np.array(e.bloch(q))
            lineas.append(f"q{q:<5} {e.probabilidad_uno(q):6.3f}   "
                          f"({b[0]:+.3f}, {b[1]:+.3f}, {b[2]:+.3f})   {np.linalg.norm(b):.3f}")
        lineas += ["", "|r| = 1: el qubit tiene un estado propio (puro).",
                   "|r| < 1: el qubit está entrelazado con otros."]
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", "\n".join(lineas))


if __name__ == "__main__":
    AplicacionCuantica().mainloop()
