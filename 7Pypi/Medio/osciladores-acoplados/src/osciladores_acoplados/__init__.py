"""osciladores_acoplados — simulación de osciladores armónicos acoplados en 1D.

Uso rápido:

    from osciladores_acoplados import SistemaOsciladores, Simulador, RungeKutta4

    sistema = SistemaOsciladores(masas=[1, 1], constantes=[10, 5, 10])
    print(sistema.frecuencias_hz())
    res = Simulador(sistema, RungeKutta4()).ejecutar([0.1, 0], [0, 0], 20, 0.01)
"""

from .core import (
    EulerExplicito,
    FabricaIntegradores,
    Integrador,
    IntegradorNumerico,
    ModosNormales,
    Resultado,
    RungeKutta4,
    Simulador,
    SistemaOsciladores,
    VelocityVerlet,
)

__version__ = "0.1.0"

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
    "__version__",
]
