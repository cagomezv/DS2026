"""Uso de la librería SIN interfaz gráfica: prueba de que la lógica es independiente."""

try:
    from osciladores_acoplados import (FabricaIntegradores, Simulador,
                                       SistemaOsciladores)
except ImportError:
    raise SystemExit(
        "No se encontró la librería 'osciladores_acoplados'.\n"
        "Desde la carpeta del proyecto, con el entorno virtual activo, ejecute:\n"
        '    python -m pip install -e ".[gui]"'
    ) from None

# Tres masas iguales entre dos paredes
sistema = SistemaOsciladores(masas=[1, 1, 1], constantes=[10, 10, 10, 10])

w, phi = sistema.modos_normales()
print("Frecuencias normales:")
for j, (wj, fj) in enumerate(zip(w, sistema.frecuencias_hz()), start=1):
    print(f"  modo {j}: ω = {wj:.4f} rad/s   f = {fj:.4f} Hz   forma = {phi[:, j-1].round(3)}")

# Misma física, distintas estrategias (patrón Strategy)
simulador = Simulador(sistema)
print("\nError máximo de energía tras 20 s con dt = 0.01 s:")
for nombre in FabricaIntegradores.disponibles():
    simulador.estrategia = FabricaIntegradores.crear(nombre)
    r = simulador.ejecutar(x0=[0.5, 0, 0], v0=[0, 0, 0], t_final=20, dt=0.01)
    print(f"  {nombre:<25} {abs(r.error_energia_relativo).max():.2e}")
