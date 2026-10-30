"""
core.py — Lógica de un sistema de osciladores armónicos acoplados en 1D.

Modelo físico
-------------
N masas m_1 … m_N alineadas, unidas por N+1 resortes:

    |--k_0--[m_1]--k_1--[m_2]-- … --[m_N]--k_N--|
   pared                                      pared

Un resorte con constante 0 equivale a "no hay resorte" (extremo libre).
Con x_i el desplazamiento de la masa i respecto al equilibrio:

    M x'' = -K x

    M = diag(m_1, …, m_N)                     (matriz de masas)
    K_ii = k_{i-1} + k_i,  K_{i,i+1} = -k_i   (matriz de rigidez, tridiagonal)

Los modos normales salen del problema de autovalores generalizado
K v = ω² M v.

Diseño de software
------------------
Patrón principal: **Strategy**.
    - `Integrador` es la estrategia abstracta (interfaz común `resolver`).
    - `ModosNormales`, `EulerExplicito`, `VelocityVerlet`, `RungeKutta4`
      son estrategias concretas intercambiables.
    - `Simulador` es el *contexto*: usa una estrategia sin conocer sus detalles.

Apoyos:
    - `IntegradorNumerico` aplica *Template Method*: el bucle temporal es común
      y cada subclase sólo define `paso`.
    - `FabricaIntegradores` es una *fábrica simple con registro*: crea
      estrategias a partir de un nombre (útil para una GUI o una CLI).

Este módulo NO depende de ninguna interfaz gráfica: sólo usa NumPy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict, Sequence, Tuple, Type

import numpy as np

__all__ = [
    "SistemaOsciladores",
    "Resultado",
    "Integrador",
    "IntegradorNumerico",
    "ModosNormales",
    "EulerExplicito",
    "VelocityVerlet",
    "RungeKutta4",
    "FabricaIntegradores",
    "Simulador",
]


# ---------------------------------------------------------------------------
# 1. El sistema físico (el "modelo")
# ---------------------------------------------------------------------------
class SistemaOsciladores:
    """Cadena 1D de N masas acopladas por N+1 resortes.

    Parameters
    ----------
    masas : secuencia de N números > 0
    constantes : secuencia de N+1 números >= 0
        constantes[0]  -> resorte pared izquierda — masa 1
        constantes[i]  -> resorte masa i — masa i+1
        constantes[N]  -> resorte masa N — pared derecha
        Un valor 0 significa que ese resorte no existe.
    """

    def __init__(self, masas: Sequence[float], constantes: Sequence[float]):
        m = np.asarray(masas, dtype=float).ravel()
        k = np.asarray(constantes, dtype=float).ravel()

        if m.size == 0:
            raise ValueError("Debe haber al menos una masa.")
        if np.any(m <= 0):
            raise ValueError("Todas las masas deben ser positivas.")
        if k.size != m.size + 1:
            raise ValueError(
                f"Con {m.size} masas se necesitan {m.size + 1} constantes "
                f"(se recibieron {k.size})."
            )
        if np.any(k < 0):
            raise ValueError("Las constantes elásticas no pueden ser negativas.")

        self._m = m
        self._k = k
        self._M = np.diag(m)
        self._K = self._construir_rigidez(k)
        self._modos_cache: Tuple[np.ndarray, np.ndarray] | None = None

    # -- Constructores alternativos -----------------------------------------
    @classmethod
    def uniforme(cls, n: int, masa: float = 1.0, k: float = 1.0,
                 extremos_fijos: bool = True) -> "SistemaOsciladores":
        """N masas iguales y resortes iguales (extremos fijos o libres)."""
        constantes = np.full(n + 1, float(k))
        if not extremos_fijos:
            constantes[0] = constantes[-1] = 0.0
        return cls(np.full(n, float(masa)), constantes)

    # -- Propiedades ----------------------------------------------------------
    @property
    def n(self) -> int:
        """Número de grados de libertad (masas)."""
        return self._m.size

    @property
    def masas(self) -> np.ndarray:
        return self._m.copy()

    @property
    def constantes(self) -> np.ndarray:
        return self._k.copy()

    @property
    def matriz_masa(self) -> np.ndarray:
        return self._M.copy()

    @property
    def matriz_rigidez(self) -> np.ndarray:
        return self._K.copy()

    # -- Física ---------------------------------------------------------------
    @staticmethod
    def _construir_rigidez(k: np.ndarray) -> np.ndarray:
        n = k.size - 1
        K = np.zeros((n, n))
        for i in range(n):
            K[i, i] = k[i] + k[i + 1]
            if i < n - 1:
                K[i, i + 1] = K[i + 1, i] = -k[i + 1]
        return K

    def aceleracion(self, x: np.ndarray) -> np.ndarray:
        """a = -M⁻¹ K x  (vale para un vector o para un arreglo de vectores)."""
        return -(np.asarray(x) @ self._K.T) / self._m

    def energia(self, x: np.ndarray, v: np.ndarray) -> np.ndarray:
        """Energía mecánica total ½ vᵀMv + ½ xᵀKx.

        Acepta un estado (forma (N,)) o una trayectoria (forma (T, N)).
        """
        x = np.asarray(x, dtype=float)
        v = np.asarray(v, dtype=float)
        cinetica = 0.5 * np.sum(self._m * v**2, axis=-1)
        potencial = 0.5 * np.sum((x @ self._K) * x, axis=-1)
        return cinetica + potencial

    def modos_normales(self) -> Tuple[np.ndarray, np.ndarray]:
        """Frecuencias angulares ω_j (rad/s) y modos Φ (columnas).

        Los modos quedan normalizados respecto a la masa: Φᵀ M Φ = I.
        Se resuelve K v = ω² M v transformándolo a un problema simétrico
        estándar con M^(-1/2), así sólo se necesita NumPy.
        """
        if self._modos_cache is None:
            m_inv_raiz = 1.0 / np.sqrt(self._m)
            A = (m_inv_raiz[:, None] * self._K) * m_inv_raiz[None, :]
            w2, U = np.linalg.eigh(A)
            w2 = np.clip(w2, 0.0, None)  # elimina -1e-16 numéricos
            phi = m_inv_raiz[:, None] * U
            # Convención de signo: primera componente no nula positiva
            for j in range(phi.shape[1]):
                idx = np.flatnonzero(np.abs(phi[:, j]) > 1e-12)
                if idx.size and phi[idx[0], j] < 0:
                    phi[:, j] *= -1
            self._modos_cache = (np.sqrt(w2), phi)
        w, phi = self._modos_cache
        return w.copy(), phi.copy()

    def frecuencias_hz(self) -> np.ndarray:
        """Frecuencias normales f_j = ω_j / 2π en Hz."""
        return self.modos_normales()[0] / (2 * np.pi)

    def condicion_modo(self, j: int, amplitud: float = 1.0) -> np.ndarray:
        """Desplazamiento inicial que excita SOLO el modo j (0-indexado)."""
        if not 0 <= j < self.n:
            raise IndexError(f"El modo debe estar entre 0 y {self.n - 1}.")
        _, phi = self.modos_normales()
        v = phi[:, j] / np.max(np.abs(phi[:, j]))
        v[np.abs(v) < 1e-12] = 0.0          # limpia ceros numéricos
        return amplitud * v

    def validar_estado(self, x0, v0) -> Tuple[np.ndarray, np.ndarray]:
        x0 = np.asarray(x0, dtype=float).ravel()
        v0 = np.asarray(v0, dtype=float).ravel()
        if x0.size != self.n or v0.size != self.n:
            raise ValueError(
                f"x0 y v0 deben tener {self.n} componentes "
                f"(recibidos {x0.size} y {v0.size})."
            )
        return x0, v0

    def __repr__(self) -> str:
        return (f"SistemaOsciladores(masas={self._m.tolist()}, "
                f"constantes={self._k.tolist()})")


# ---------------------------------------------------------------------------
# 2. El resultado de una simulación (objeto de datos inmutable)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Resultado:
    """Trayectoria calculada.

    t : (T,)      tiempos
    x : (T, N)    posiciones
    v : (T, N)    velocidades
    energia : (T,) energía total
    metodo : nombre de la estrategia usada
    """

    t: np.ndarray
    x: np.ndarray
    v: np.ndarray
    energia: np.ndarray
    metodo: str

    @property
    def error_energia_relativo(self) -> np.ndarray:
        """(E(t) - E(0)) / E(0). Mide qué tan bien se conserva la energía."""
        e0 = self.energia[0]
        if e0 == 0:
            return np.zeros_like(self.energia)
        return (self.energia - e0) / e0

    def a_csv(self, ruta: str) -> None:
        """Guarda t, x_i, v_i y E en un archivo CSV."""
        n = self.x.shape[1]
        cab = (["t"] + [f"x{i+1}" for i in range(n)]
               + [f"v{i+1}" for i in range(n)] + ["E"])
        datos = np.column_stack([self.t, self.x, self.v, self.energia])
        np.savetxt(ruta, datos, delimiter=",", header=",".join(cab),
                   comments="")


# ---------------------------------------------------------------------------
# 3. Patrón Strategy: la interfaz común de los "solucionadores"
# ---------------------------------------------------------------------------
class Integrador(ABC):
    """Estrategia abstracta: toda forma de resolver el sistema cumple esto."""

    nombre: str = "abstracto"

    @abstractmethod
    def resolver(self, sistema: SistemaOsciladores, x0, v0,
                 t_final: float, dt: float) -> Resultado:
        """Devuelve la evolución temporal entre 0 y t_final con paso dt."""

    @staticmethod
    def _malla_temporal(t_final: float, dt: float) -> np.ndarray:
        if dt <= 0 or t_final <= 0:
            raise ValueError("t_final y dt deben ser positivos.")
        n_pasos = int(round(t_final / dt))
        if n_pasos < 1:
            raise ValueError("dt es mayor que t_final.")
        return np.arange(n_pasos + 1) * dt

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


# --- Estrategia concreta 1: solución analítica por modos normales ----------
class ModosNormales(Integrador):
    """Solución EXACTA superponiendo modos normales.

    x(t) = Σ_j φ_j [ q_j(0) cos ω_j t + q̇_j(0)/ω_j sin ω_j t ]
    con q(0) = Φᵀ M x0 y q̇(0) = Φᵀ M v0.
    Si ω_j = 0 (sistema libre, traslación rígida): q_j = q_j(0) + q̇_j(0) t.
    """

    nombre = "Modos normales (exacto)"

    def resolver(self, sistema, x0, v0, t_final, dt):
        x0, v0 = sistema.validar_estado(x0, v0)
        t = self._malla_temporal(t_final, dt)
        w, phi = sistema.modos_normales()
        M = sistema.matriz_masa
        q0 = phi.T @ M @ x0
        p0 = phi.T @ M @ v0

        wt = np.outer(t, w)                        # (T, N)
        libre = w < 1e-12
        w_seguro = np.where(libre, 1.0, w)
        q = q0 * np.cos(wt) + np.where(libre, p0 * t[:, None],
                                       p0 / w_seguro * np.sin(wt))
        qd = np.where(libre, p0 + 0 * wt,
                      -q0 * w * np.sin(wt) + p0 * np.cos(wt))

        x = q @ phi.T
        v = qd @ phi.T
        return Resultado(t, x, v, sistema.energia(x, v), self.nombre)


# --- Template Method para los métodos paso a paso ---------------------------
class IntegradorNumerico(Integrador):
    """Base de los integradores numéricos: el bucle es siempre el mismo,
    cada subclase sólo implementa `paso` (patrón Template Method)."""

    def resolver(self, sistema, x0, v0, t_final, dt):
        x0, v0 = sistema.validar_estado(x0, v0)
        t = self._malla_temporal(t_final, dt)
        X = np.empty((t.size, sistema.n))
        V = np.empty_like(X)
        X[0], V[0] = x0, v0
        for i in range(t.size - 1):
            X[i + 1], V[i + 1] = self.paso(sistema, X[i], V[i], dt)
        return Resultado(t, X, V, sistema.energia(X, V), self.nombre)

    @abstractmethod
    def paso(self, sistema: SistemaOsciladores, x: np.ndarray,
             v: np.ndarray, dt: float) -> Tuple[np.ndarray, np.ndarray]:
        """Avanza el estado (x, v) un intervalo dt."""


# --- Estrategia concreta 2 ---------------------------------------------------
class EulerExplicito(IntegradorNumerico):
    """Euler explícito (orden 1). NO conserva la energía: crece con el tiempo.
    Se incluye a propósito para comparar."""

    nombre = "Euler explícito"

    def paso(self, sistema, x, v, dt):
        a = sistema.aceleracion(x)
        return x + v * dt, v + a * dt


# --- Estrategia concreta 3 ---------------------------------------------------
class VelocityVerlet(IntegradorNumerico):
    """Velocity Verlet (orden 2, simplético): la energía oscila pero no deriva."""

    nombre = "Velocity Verlet"

    def paso(self, sistema, x, v, dt):
        a = sistema.aceleracion(x)
        x_nuevo = x + v * dt + 0.5 * a * dt**2
        a_nuevo = sistema.aceleracion(x_nuevo)
        return x_nuevo, v + 0.5 * (a + a_nuevo) * dt


# --- Estrategia concreta 4 ---------------------------------------------------
class RungeKutta4(IntegradorNumerico):
    """Runge-Kutta clásico de orden 4: muy preciso, deriva de energía pequeña."""

    nombre = "Runge-Kutta 4"

    def paso(self, sistema, x, v, dt):
        acc = sistema.aceleracion
        k1x, k1v = v, acc(x)
        k2x, k2v = v + 0.5 * dt * k1v, acc(x + 0.5 * dt * k1x)
        k3x, k3v = v + 0.5 * dt * k2v, acc(x + 0.5 * dt * k2x)
        k4x, k4v = v + dt * k3v, acc(x + dt * k3x)
        x_nuevo = x + dt / 6 * (k1x + 2 * k2x + 2 * k3x + k4x)
        v_nuevo = v + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        return x_nuevo, v_nuevo


# ---------------------------------------------------------------------------
# 4. Fábrica con registro: crear estrategias a partir de un nombre
# ---------------------------------------------------------------------------
class FabricaIntegradores:
    """Registro de estrategias disponibles.

    >>> FabricaIntegradores.disponibles()
    ['Modos normales (exacto)', 'Euler explícito', 'Velocity Verlet', 'Runge-Kutta 4']
    >>> FabricaIntegradores.crear("Runge-Kutta 4")
    RungeKutta4()

    Para añadir un método nuevo basta con decorar su clase con
    `@FabricaIntegradores.registrar` — no hay que tocar ni la GUI ni el Simulador.
    """

    _registro: Dict[str, Type[Integrador]] = {}

    @classmethod
    def registrar(cls, clase: Type[Integrador]) -> Type[Integrador]:
        cls._registro[clase.nombre] = clase
        return clase

    @classmethod
    def crear(cls, nombre: str) -> Integrador:
        try:
            return cls._registro[nombre]()
        except KeyError:
            raise ValueError(
                f"Método desconocido '{nombre}'. "
                f"Disponibles: {cls.disponibles()}"
            ) from None

    @classmethod
    def disponibles(cls) -> list:
        return list(cls._registro)


for _clase in (ModosNormales, EulerExplicito, VelocityVerlet, RungeKutta4):
    FabricaIntegradores.registrar(_clase)


# ---------------------------------------------------------------------------
# 5. Contexto del patrón Strategy
# ---------------------------------------------------------------------------
class Simulador:
    """Contexto: combina un sistema con una estrategia de solución.

    >>> sis = SistemaOsciladores.uniforme(3, masa=1, k=10)
    >>> sim = Simulador(sis, VelocityVerlet())
    >>> res = sim.ejecutar([0.1, 0, 0], [0, 0, 0], t_final=10, dt=0.01)
    >>> sim.estrategia = RungeKutta4()      # se cambia en caliente
    """

    def __init__(self, sistema: SistemaOsciladores,
                 estrategia: Integrador | None = None):
        self.sistema = sistema
        self.estrategia = estrategia or ModosNormales()
        self._observadores: list[Callable[[Resultado], None]] = []

    @property
    def estrategia(self) -> Integrador:
        return self._estrategia

    @estrategia.setter
    def estrategia(self, nueva: Integrador) -> None:
        if not isinstance(nueva, Integrador):
            raise TypeError("La estrategia debe heredar de Integrador.")
        self._estrategia = nueva

    def suscribir(self, funcion: Callable[[Resultado], None]) -> None:
        """Registra una función que se llamará con cada nuevo Resultado.
        Así una GUI puede reaccionar sin que la lógica la conozca."""
        self._observadores.append(funcion)

    def ejecutar(self, x0, v0, t_final: float, dt: float) -> Resultado:
        resultado = self._estrategia.resolver(self.sistema, x0, v0,
                                              t_final, dt)
        for funcion in self._observadores:
            funcion(resultado)
        return resultado
