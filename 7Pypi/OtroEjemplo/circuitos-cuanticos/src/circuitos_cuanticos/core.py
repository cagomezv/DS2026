"""
core.py — Simulador de circuitos cuánticos por vector de estado.

Modelo físico
-------------
Un registro de n qubits se describe con un vector de 2**n amplitudes complejas

    |ψ⟩ = Σ_k  a_k |k⟩ ,   Σ_k |a_k|² = 1

Convención de orden: el qubit 0 es el de la IZQUIERDA en el ket.
Por ejemplo, con 3 qubits |q0 q1 q2⟩ = |110⟩ es el índice 6.

Una puerta es una matriz unitaria U (U†U = I) que actúa sobre algunos qubits.
Medir el registro da el resultado k con probabilidad |a_k|² (regla de Born).

Diseño de software
------------------
Patrón principal: **Command**.
    - `Puerta` es el comando abstracto: sabe `aplicar` y `deshacer`.
    - `H`, `X`, `CNOT`, `Oraculo`, `Difusion`, `Medir`, … son comandos concretos.
    - `EstadoCuantico` es el *receptor*: el objeto sobre el que actúan.
    - `Circuito` es el *invocador*: guarda la lista de comandos, los ejecuta
      paso a paso, recuerda el historial y puede deshacer.

Apoyos:
    - `FabricaPuertas` crea puertas a partir de un nombre (útil para la GUI).
    - `CatalogoCircuitos` construye los ejemplos típicos: Bell, GHZ,
      teleportación y Grover.
    - `Circuito.suscribir` avisa a quien escuche después de cada paso
      (observador ligero), sin que la lógica conozca la interfaz.

Este módulo NO depende de ninguna interfaz gráfica: sólo usa NumPy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "EstadoCuantico",
    "Puerta", "PuertaMatricial",
    "H", "X", "Y", "Z", "S", "T", "RX", "RY", "RZ",
    "CNOT", "CZ", "SWAP", "Toffoli",
    "Oraculo", "Difusion", "Medir",
    "Circuito", "FabricaPuertas", "CatalogoCircuitos",
]

_TOL = 1e-10


# ---------------------------------------------------------------------------
# 1. Receptor: el estado cuántico
# ---------------------------------------------------------------------------
class EstadoCuantico:
    """Vector de estado de n qubits.

    >>> e = EstadoCuantico(2)          # |00⟩
    >>> e.probabilidades()
    {'00': 1.0}
    """

    def __init__(self, n_qubits: int, amplitudes: Optional[Sequence[complex]] = None):
        if n_qubits < 1:
            raise ValueError("Se necesita al menos un qubit.")
        if n_qubits > 14:
            raise ValueError("Más de 14 qubits es demasiado para este simulador.")
        self.n = int(n_qubits)
        if amplitudes is None:
            self._psi = np.zeros(2 ** self.n, dtype=complex)
            self._psi[0] = 1.0
        else:
            psi = np.asarray(amplitudes, dtype=complex).ravel()
            if psi.size != 2 ** self.n:
                raise ValueError(f"Se esperaban {2 ** self.n} amplitudes.")
            norma = np.linalg.norm(psi)
            if norma < _TOL:
                raise ValueError("El vector de estado no puede ser nulo.")
            self._psi = psi / norma

    # -- Acceso -------------------------------------------------------------
    @property
    def amplitudes(self) -> np.ndarray:
        return self._psi.copy()

    def copia(self) -> "EstadoCuantico":
        return EstadoCuantico(self.n, self._psi)

    def etiqueta(self, k: int) -> str:
        """Índice k → cadena de bits, con el qubit 0 a la izquierda."""
        return format(k, f"0{self.n}b")

    # -- Evolución ------------------------------------------------------------
    def aplicar_matriz(self, U: np.ndarray, qubits: Sequence[int]) -> None:
        """Aplica una matriz 2^k × 2^k sobre los qubits indicados (en ese orden).

        Truco: se ve el vector como un tensor de forma (2, 2, …, 2), se llevan
        los ejes de los qubits elegidos al frente, se multiplica por U y se
        devuelven los ejes a su lugar. Así nunca se construye la matriz
        gigante de 2^n × 2^n.
        """
        qubits = list(qubits)
        k = len(qubits)
        psi = self._psi.reshape([2] * self.n)
        psi = np.moveaxis(psi, qubits, range(k))
        forma = psi.shape
        psi = (U @ psi.reshape(2 ** k, -1)).reshape(forma)
        psi = np.moveaxis(psi, range(k), qubits)
        self._psi = psi.reshape(-1)

    def _reemplazar(self, amplitudes: np.ndarray) -> None:
        self._psi = np.asarray(amplitudes, dtype=complex).copy()

    # -- Medición ---------------------------------------------------------------
    def probabilidades(self, minimo: float = 1e-12) -> Dict[str, float]:
        """Probabilidad de cada resultado (regla de Born), sin los casi nulos."""
        p = np.abs(self._psi) ** 2
        return {self.etiqueta(k): float(p[k]) for k in range(p.size) if p[k] > minimo}

    def vector_probabilidades(self) -> np.ndarray:
        return np.abs(self._psi) ** 2

    def medir(self, disparos: int = 1000, semilla: Optional[int] = None) -> Dict[str, int]:
        """Simula `disparos` mediciones del registro completo (no lo modifica)."""
        if disparos < 1:
            raise ValueError("El número de disparos debe ser positivo.")
        rng = np.random.default_rng(semilla)
        p = self.vector_probabilidades()
        resultados = rng.choice(p.size, size=disparos, p=p / p.sum())
        conteo = np.bincount(resultados, minlength=p.size)
        return {self.etiqueta(k): int(c) for k, c in enumerate(conteo) if c > 0}

    def probabilidad_uno(self, q: int) -> float:
        """Probabilidad de obtener 1 al medir sólo el qubit q."""
        self._validar_qubit(q)
        psi = np.moveaxis(self._psi.reshape([2] * self.n), q, 0)
        return float(np.sum(np.abs(psi[1]) ** 2))

    def bloch(self, q: int) -> Tuple[float, float, float]:
        """Vector de Bloch (x, y, z) del qubit q (traza parcial sobre los demás).

        Si el qubit está entrelazado, el vector queda DENTRO de la esfera
        (longitud < 1): el qubit solo no tiene un estado puro propio.
        """
        self._validar_qubit(q)
        psi = np.moveaxis(self._psi.reshape([2] * self.n), q, 0).reshape(2, -1)
        rho = psi @ psi.conj().T                       # matriz densidad reducida 2×2
        x = 2 * rho[0, 1].real
        y = -2 * rho[0, 1].imag
        z = (rho[0, 0] - rho[1, 1]).real
        return float(x), float(y), float(z)

    def ket(self, decimales: int = 3, maximo: int = 16) -> str:
        """Texto como 0.707|00⟩ + 0.707|11⟩."""
        terminos = []
        for k, a in enumerate(self._psi):
            if abs(a) < 10 ** (-decimales):
                continue
            re, im = round(a.real, decimales), round(a.imag, decimales)
            if abs(im) < 10 ** (-decimales):
                coef = f"{re:g}"
            elif abs(re) < 10 ** (-decimales):
                coef = f"{im:g}i"
            else:
                coef = f"({re:g}{im:+g}i)"
            terminos.append(f"{coef}|{self.etiqueta(k)}⟩")
        if len(terminos) > maximo:
            terminos = terminos[:maximo] + ["…"]
        return " + ".join(terminos).replace("+ -", "- ")

    def _validar_qubit(self, q: int) -> None:
        if not 0 <= q < self.n:
            raise IndexError(f"El qubit {q} no existe (hay {self.n}: 0 … {self.n - 1}).")

    def __repr__(self) -> str:
        return f"EstadoCuantico({self.n} qubits: {self.ket()})"


# ---------------------------------------------------------------------------
# 2. Patrón Command: el comando abstracto
# ---------------------------------------------------------------------------
class Puerta(ABC):
    """Comando abstracto: una operación que se puede aplicar y deshacer."""

    nombre: str = "?"
    simbolo: str = "?"          # texto corto para dibujar el circuito

    def __init__(self, *qubits: int):
        if len(set(qubits)) != len(qubits):
            raise ValueError(f"{self.nombre}: los qubits no pueden repetirse.")
        if any(q < 0 for q in qubits):
            raise ValueError(f"{self.nombre}: los índices de qubit no pueden ser negativos.")
        self.qubits: Tuple[int, ...] = tuple(qubits)

    def validar(self, estado: EstadoCuantico) -> None:
        for q in self.qubits:
            estado._validar_qubit(q)

    @abstractmethod
    def aplicar(self, estado: EstadoCuantico) -> None:
        """Ejecuta la operación sobre el estado."""

    @abstractmethod
    def deshacer(self, estado: EstadoCuantico) -> None:
        """Revierte exactamente lo que hizo `aplicar`."""

    def __repr__(self) -> str:
        return f"{self.nombre}({', '.join(map(str, self.qubits))})"


class PuertaMatricial(Puerta):
    """Puerta unitaria: aplicar = multiplicar por U, deshacer = por U†.

    Como U†U = I, deshacer no necesita guardar nada: la física cuántica
    (sin medir) es reversible y el patrón Command lo aprovecha.
    """

    @abstractmethod
    def matriz(self) -> np.ndarray:
        """Matriz unitaria 2^k × 2^k, con k = número de qubits de la puerta."""

    def aplicar(self, estado):
        self.validar(estado)
        estado.aplicar_matriz(self.matriz(), self.qubits)

    def deshacer(self, estado):
        self.validar(estado)
        estado.aplicar_matriz(self.matriz().conj().T, self.qubits)


# --- Puertas de un qubit ------------------------------------------------------
_R2 = 1 / np.sqrt(2)


class _UnQubit(PuertaMatricial):
    _U: np.ndarray = np.eye(2)

    def __init__(self, q: int):
        super().__init__(q)

    def matriz(self):
        return self._U


class H(_UnQubit):
    """Hadamard: |0⟩ → (|0⟩+|1⟩)/√2. Crea superposición."""
    nombre, simbolo = "H", "H"
    _U = _R2 * np.array([[1, 1], [1, -1]], dtype=complex)


class X(_UnQubit):
    """NOT cuántico: intercambia |0⟩ y |1⟩."""
    nombre, simbolo = "X", "X"
    _U = np.array([[0, 1], [1, 0]], dtype=complex)


class Y(_UnQubit):
    nombre, simbolo = "Y", "Y"
    _U = np.array([[0, -1j], [1j, 0]], dtype=complex)


class Z(_UnQubit):
    """Cambia el signo de |1⟩ (fase de π)."""
    nombre, simbolo = "Z", "Z"
    _U = np.array([[1, 0], [0, -1]], dtype=complex)


class S(_UnQubit):
    nombre, simbolo = "S", "S"
    _U = np.array([[1, 0], [0, 1j]], dtype=complex)


class T(_UnQubit):
    nombre, simbolo = "T", "T"
    _U = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)


class _Rotacion(PuertaMatricial):
    def __init__(self, q: int, angulo: float):
        super().__init__(q)
        self.angulo = float(angulo)

    def __repr__(self):
        return f"{self.nombre}({self.qubits[0]}, {self.angulo:.3f})"


class RX(_Rotacion):
    nombre, simbolo = "RX", "Rx"

    def matriz(self):
        c, s = np.cos(self.angulo / 2), np.sin(self.angulo / 2)
        return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)


class RY(_Rotacion):
    """Gira el vector de Bloch un ángulo θ alrededor del eje y."""
    nombre, simbolo = "RY", "Ry"

    def matriz(self):
        c, s = np.cos(self.angulo / 2), np.sin(self.angulo / 2)
        return np.array([[c, -s], [s, c]], dtype=complex)


class RZ(_Rotacion):
    nombre, simbolo = "RZ", "Rz"

    def matriz(self):
        f = np.exp(1j * self.angulo / 2)
        return np.array([[1 / f, 0], [0, f]], dtype=complex)


# --- Puertas de varios qubits -------------------------------------------------
class CNOT(PuertaMatricial):
    """X sobre el objetivo sólo si el control vale 1. Crea entrelazamiento."""
    nombre, simbolo = "CNOT", "⊕"

    def __init__(self, control: int, objetivo: int):
        super().__init__(control, objetivo)

    def matriz(self):
        return np.array([[1, 0, 0, 0], [0, 1, 0, 0],
                         [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex)


class CZ(PuertaMatricial):
    """Z sobre el objetivo si el control vale 1 (es simétrica)."""
    nombre, simbolo = "CZ", "Z"

    def __init__(self, control: int, objetivo: int):
        super().__init__(control, objetivo)

    def matriz(self):
        return np.diag([1, 1, 1, -1]).astype(complex)


class SWAP(PuertaMatricial):
    nombre, simbolo = "SWAP", "×"

    def __init__(self, a: int, b: int):
        super().__init__(a, b)

    def matriz(self):
        return np.array([[1, 0, 0, 0], [0, 0, 1, 0],
                         [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex)


class Toffoli(PuertaMatricial):
    """X sobre el objetivo si ambos controles valen 1."""
    nombre, simbolo = "Toffoli", "⊕"

    def __init__(self, c1: int, c2: int, objetivo: int):
        super().__init__(c1, c2, objetivo)

    def matriz(self):
        U = np.eye(8, dtype=complex)
        U[[6, 7]] = U[[7, 6]]
        return U


# --- Puertas del algoritmo de Grover ------------------------------------------
class Oraculo(PuertaMatricial):
    """Cambia el signo de la amplitud del estado buscado: |w⟩ → −|w⟩."""
    nombre, simbolo = "Oráculo", "O"

    def __init__(self, n_qubits: int, marcado: int):
        if not 0 <= marcado < 2 ** n_qubits:
            raise ValueError(f"El estado marcado debe estar entre 0 y {2 ** n_qubits - 1}.")
        super().__init__(*range(n_qubits))
        self.marcado = int(marcado)

    def matriz(self):
        d = np.ones(2 ** len(self.qubits), dtype=complex)
        d[self.marcado] = -1
        return np.diag(d)

    def aplicar(self, estado):
        """Atajo eficiente: basta con cambiar el signo de UNA amplitud."""
        self.validar(estado)
        if len(self.qubits) != estado.n:
            return super().aplicar(estado)
        psi = estado.amplitudes
        psi[self.marcado] *= -1
        estado._reemplazar(psi)

    deshacer = aplicar          # aplicar dos veces deja todo igual (O² = I)


class Difusion(PuertaMatricial):
    """Inversión respecto a la media: 2|s⟩⟨s| − I, con |s⟩ la superposición uniforme."""
    nombre, simbolo = "Difusión", "D"

    def __init__(self, n_qubits: int):
        super().__init__(*range(n_qubits))

    def matriz(self):
        N = 2 ** len(self.qubits)
        return np.full((N, N), 2 / N, dtype=complex) - np.eye(N)

    def aplicar(self, estado):
        """Atajo eficiente: a_k → 2·media − a_k, sin construir la matriz N × N."""
        self.validar(estado)
        if len(self.qubits) != estado.n:
            return super().aplicar(estado)
        psi = estado.amplitudes
        estado._reemplazar(2 * psi.mean() - psi)

    deshacer = aplicar          # también es su propia inversa (D² = I)


# --- Medición: un comando NO unitario -----------------------------------------
class Medir(Puerta):
    """Mide un qubit y colapsa el estado.

    No es reversible: para poder deshacerla, el comando guarda una copia del
    estado anterior (una "foto", patrón Memento) antes de colapsarlo.
    """
    nombre, simbolo = "Medir", "M"

    def __init__(self, q: int, semilla: Optional[int] = None):
        super().__init__(q)
        self._rng = np.random.default_rng(semilla)
        self._antes: Optional[np.ndarray] = None
        self.resultado: Optional[int] = None

    def aplicar(self, estado):
        self.validar(estado)
        self._antes = estado.amplitudes
        q = self.qubits[0]
        p1 = estado.probabilidad_uno(q)
        self.resultado = int(self._rng.random() < p1)
        psi = np.moveaxis(estado.amplitudes.reshape([2] * estado.n), q, 0)
        psi[1 - self.resultado] = 0                # elimina la rama no observada
        psi = np.moveaxis(psi, 0, q).reshape(-1)
        estado._reemplazar(psi / np.linalg.norm(psi))

    def deshacer(self, estado):
        if self._antes is None:
            raise RuntimeError("No se puede deshacer una medición que no se ha hecho.")
        estado._reemplazar(self._antes)
        self._antes, self.resultado = None, None


# ---------------------------------------------------------------------------
# 3. Invocador: el circuito
# ---------------------------------------------------------------------------
class Circuito:
    """Lista ordenada de puertas (comandos) que actúan sobre un estado.

    >>> c = Circuito(2).agregar(H(0)).agregar(CNOT(0, 1))
    >>> c.ejecutar().probabilidades()
    {'00': 0.5, '11': 0.5}
    >>> c.deshacer(); c.posicion          # vuelve un paso atrás
    1
    """

    def __init__(self, n_qubits: int, nombre: str = "Circuito"):
        self.n = int(n_qubits)
        self.nombre = nombre
        self.puertas: List[Puerta] = []
        self.estado = EstadoCuantico(self.n)
        self.posicion = 0                       # cuántas puertas se han aplicado
        self._observadores: List[Callable[["Circuito"], None]] = []

    # -- Construcción ---------------------------------------------------------
    def agregar(self, puerta: Puerta) -> "Circuito":
        """Añade una puerta al final. Devuelve self para encadenar llamadas."""
        if not isinstance(puerta, Puerta):
            raise TypeError("Sólo se pueden agregar objetos Puerta.")
        puerta.validar(self.estado)
        self.puertas.append(puerta)
        return self

    def __len__(self) -> int:
        return len(self.puertas)

    # -- Ejecución (invocador) ------------------------------------------------
    def paso(self) -> bool:
        """Aplica la siguiente puerta. Devuelve False si ya no quedan."""
        if self.posicion >= len(self.puertas):
            return False
        self.puertas[self.posicion].aplicar(self.estado)
        self.posicion += 1
        self._notificar()
        return True

    def deshacer(self) -> bool:
        """Revierte la última puerta aplicada. Devuelve False si no hay ninguna."""
        if self.posicion == 0:
            return False
        self.posicion -= 1
        self.puertas[self.posicion].deshacer(self.estado)
        self._notificar()
        return True

    def ejecutar(self) -> EstadoCuantico:
        """Aplica todas las puertas pendientes y devuelve el estado."""
        while self.posicion < len(self.puertas):
            self.puertas[self.posicion].aplicar(self.estado)
            self.posicion += 1
        self._notificar()
        return self.estado

    def reiniciar(self) -> None:
        """Vuelve a |00…0⟩ sin borrar las puertas."""
        self.estado = EstadoCuantico(self.n)
        self.posicion = 0
        for p in self.puertas:
            if isinstance(p, Medir):
                p._antes, p.resultado = None, None
        self._notificar()

    # -- Observador ligero ----------------------------------------------------
    def suscribir(self, funcion: Callable[["Circuito"], None]) -> None:
        self._observadores.append(funcion)

    def _notificar(self) -> None:
        for f in self._observadores:
            f(self)

    def __repr__(self) -> str:
        return f"Circuito('{self.nombre}', {self.n} qubits, {len(self)} puertas, posición {self.posicion})"


# ---------------------------------------------------------------------------
# 4. Fábrica de puertas: crear comandos a partir de un nombre
# ---------------------------------------------------------------------------
class FabricaPuertas:
    """Crea puertas por nombre.

    >>> FabricaPuertas.crear("CNOT", 0, 1)
    CNOT(0, 1)
    """

    _registro = {"H": H, "X": X, "Y": Y, "Z": Z, "S": S, "T": T,
                 "CNOT": CNOT, "CZ": CZ, "SWAP": SWAP, "Toffoli": Toffoli,
                 "Medir": Medir}
    _con_angulo = {"RX": RX, "RY": RY, "RZ": RZ}

    @classmethod
    def disponibles(cls) -> List[str]:
        return list(cls._registro) + list(cls._con_angulo)

    @classmethod
    def num_qubits(cls, nombre: str) -> int:
        return {"CNOT": 2, "CZ": 2, "SWAP": 2, "Toffoli": 3}.get(nombre, 1)

    @classmethod
    def crear(cls, nombre: str, *qubits: int, angulo: float = 0.0) -> Puerta:
        if nombre in cls._con_angulo:
            return cls._con_angulo[nombre](*qubits, angulo)
        if nombre not in cls._registro:
            raise ValueError(f"Puerta desconocida '{nombre}'. Disponibles: {cls.disponibles()}")
        esperado = cls.num_qubits(nombre)
        if len(qubits) != esperado:
            raise ValueError(f"{nombre} necesita {esperado} qubit(s).")
        return cls._registro[nombre](*qubits)


# ---------------------------------------------------------------------------
# 5. Catálogo de circuitos típicos
# ---------------------------------------------------------------------------
class CatalogoCircuitos:
    """Ejemplos clásicos de computación cuántica, listos para ejecutar."""

    @staticmethod
    def bell() -> Circuito:
        """(|00⟩ + |11⟩)/√2: los dos qubits quedan entrelazados."""
        return Circuito(2, "Estado de Bell").agregar(H(0)).agregar(CNOT(0, 1))

    @staticmethod
    def ghz(n: int = 3) -> Circuito:
        """(|00…0⟩ + |11…1⟩)/√2: entrelazamiento de n qubits."""
        c = Circuito(n, f"GHZ de {n} qubits").agregar(H(0))
        for q in range(n - 1):
            c.agregar(CNOT(q, q + 1))
        return c

    @staticmethod
    def teleportacion(theta: float = 1.0, phi: float = 0.5) -> Circuito:
        """Teleporta el estado del qubit 0 al qubit 2.

        q0: estado a enviar, preparado con RY(θ) y RZ(φ).
        q1, q2: par de Bell compartido entre emisor y receptor.
        Las correcciones clásicas se hacen con CNOT y CZ controladas
        (principio de medición diferida): el resultado es el mismo que medir
        y corregir, pero el circuito queda determinista y verificable.
        """
        return (Circuito(3, "Teleportación")
                .agregar(RY(0, theta)).agregar(RZ(0, phi))      # estado a enviar
                .agregar(H(1)).agregar(CNOT(1, 2))              # par de Bell
                .agregar(CNOT(0, 1)).agregar(H(0))              # medición de Bell
                .agregar(CNOT(1, 2)).agregar(CZ(0, 2)))         # correcciones

    @staticmethod
    def iteraciones_optimas_grover(n: int) -> int:
        return max(1, int(np.floor(np.pi / 4 * np.sqrt(2 ** n))))

    @classmethod
    def grover(cls, n: int = 3, marcado: int = 5,
               iteraciones: Optional[int] = None) -> Circuito:
        """Busca el estado `marcado` entre 2**n con ≈ (π/4)√N consultas."""
        k = cls.iteraciones_optimas_grover(n) if iteraciones is None else iteraciones
        c = Circuito(n, f"Grover: buscar {format(marcado, f'0{n}b')}")
        for q in range(n):
            c.agregar(H(q))
        for _ in range(k):
            c.agregar(Oraculo(n, marcado)).agregar(Difusion(n))
        return c

    @staticmethod
    def disponibles() -> List[str]:
        return ["Estado de Bell", "GHZ", "Teleportación", "Grover"]
