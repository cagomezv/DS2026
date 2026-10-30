"""Uso de la librería SIN interfaz gráfica: la lógica es independiente."""

try:
    import numpy as np
    from circuitos_cuanticos import (CNOT, CatalogoCircuitos, Circuito,
                                     EstadoCuantico, H, RY, RZ)
except ImportError:
    raise SystemExit(
        "No se encontró la librería 'circuitos_cuanticos'.\n"
        "Desde la carpeta del proyecto, con el entorno virtual activo, ejecute:\n"
        '    python -m pip install -e ".[gui]"'
    ) from None

# 1. Estado de Bell, construido a mano con el patrón Command
bell = Circuito(2, "Bell").agregar(H(0)).agregar(CNOT(0, 1))
print("Bell:          ", bell.ejecutar().ket())
print("1000 medidas:  ", bell.estado.medir(1000, semilla=7))

# 2. Paso a paso y deshacer
bell.deshacer()
print("Sin la CNOT:   ", bell.estado.ket())

# 3. Teleportación: el qubit 2 termina con el estado que tenía el qubit 0
theta, phi = 1.0, 0.5
original = EstadoCuantico(1)
RY(0, theta).aplicar(original)
RZ(0, phi).aplicar(original)
final = CatalogoCircuitos.teleportacion(theta, phi).ejecutar()
print("\nBloch original (q0 antes):", np.round(original.bloch(0), 3))
print("Bloch del qubit 2 después:", np.round(final.bloch(2), 3))

# 4. Grover: buscar |101⟩ entre 8 estados
print("\nGrover con 3 qubits, buscando 101:")
for k in range(5):
    p = CatalogoCircuitos.grover(3, marcado=5, iteraciones=k).ejecutar().vector_probabilidades()[5]
    print(f"  {k} iteraciones → P(101) = {p:.3f}")
