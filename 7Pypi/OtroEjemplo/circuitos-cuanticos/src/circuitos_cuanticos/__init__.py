"""circuitos_cuanticos — simulador didáctico de circuitos cuánticos (vector de estado).

Uso rápido:

    from circuitos_cuanticos import Circuito, H, CNOT

    bell = Circuito(2).agregar(H(0)).agregar(CNOT(0, 1))
    print(bell.ejecutar().ket())          # 0.707|00⟩ + 0.707|11⟩
    print(bell.estado.medir(1000))        # {'00': ~500, '11': ~500}
"""

from .core import (CNOT, CZ, RX, RY, RZ, SWAP, CatalogoCircuitos, Circuito,
                   Difusion, EstadoCuantico, FabricaPuertas, H, Medir, Oraculo,
                   Puerta, PuertaMatricial, S, T, Toffoli, X, Y, Z)

__version__ = "0.1.0"

__all__ = [
    "EstadoCuantico", "Puerta", "PuertaMatricial",
    "H", "X", "Y", "Z", "S", "T", "RX", "RY", "RZ",
    "CNOT", "CZ", "SWAP", "Toffoli", "Oraculo", "Difusion", "Medir",
    "Circuito", "FabricaPuertas", "CatalogoCircuitos", "__version__",
]
