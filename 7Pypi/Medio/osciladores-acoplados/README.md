# osciladores-acoplados

Librería didáctica en Python para resolver **sistemas de osciladores armónicos acoplados en 1D**:
N masas unidas por N+1 resortes, con extremos fijos o libres.

```
|--k0--[m1]--k1--[m2]-- … --[mN]--kN--|
```

Ecuación de movimiento: **M ẍ = −K x**. Los modos normales se obtienen de **K v = ω² M v**.

## Instalación

```bash
pip install osciladores-acoplados          # sólo la lógica (depende de numpy)
pip install "osciladores-acoplados[gui]"   # + matplotlib para la interfaz gráfica
```

## Uso

```python
from osciladores_acoplados import SistemaOsciladores, Simulador, RungeKutta4, VelocityVerlet

sistema = SistemaOsciladores(masas=[1, 1, 1], constantes=[10, 10, 10, 10])
print(sistema.frecuencias_hz())              # frecuencias normales (Hz)

sim = Simulador(sistema, RungeKutta4())      # patrón Strategy
res = sim.ejecutar(x0=[0.5, 0, 0], v0=[0, 0, 0], t_final=20, dt=0.01)
print(res.x.shape, res.error_energia_relativo.max())

sim.estrategia = VelocityVerlet()            # se cambia el método sin tocar nada más
```

Métodos disponibles (`FabricaIntegradores.disponibles()`):

| Estrategia | Tipo | Energía |
|---|---|---|
| `ModosNormales` | exacta (analítica) | se conserva a precisión de máquina |
| `EulerExplicito` | numérica, orden 1 | crece sin control (ejemplo de lo que NO hacer) |
| `VelocityVerlet` | numérica, orden 2, simplética | oscila acotada |
| `RungeKutta4` | numérica, orden 4 | deriva muy pequeña |

## Arquitectura

* `core.py` — toda la lógica, sólo con NumPy (sin interfaz gráfica).
  * **Strategy**: `Integrador` (abstracta) → `ModosNormales`, `EulerExplicito`, `VelocityVerlet`, `RungeKutta4`; `Simulador` es el contexto.
  * **Template Method**: `IntegradorNumerico.resolver` contiene el bucle; las subclases sólo implementan `paso`.
  * **Fábrica con registro**: `FabricaIntegradores` crea estrategias por nombre.
  * **Observador** (ligero): `Simulador.suscribir(funcion)` avisa cuando hay un nuevo `Resultado`.
* `GUI.py` — interfaz tkinter + matplotlib que sólo usa la API pública.

## Desarrollo

Una sola vez, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[gui,dev]"
```

* `.venv` es un Python propio del proyecto, aislado de los demás.
* `-e` (editable) enlaza la librería a `src/`: los cambios en `core.py` se ven al instante.
* `[gui,dev]` instala además matplotlib (interfaz) y pytest, build y twine (desarrollo).

Si PowerShell bloquea `Activate.ps1`, ejecute una vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

En cada terminal nueva basta con activar el entorno y ejecutar:

```powershell
python GUI.py
python ejemplo_consola.py
```

> Si aparece `ModuleNotFoundError: No module named 'osciladores_acoplados'`, la librería
> no está instalada en el Python que se está usando: active el entorno e instálela.

## Pruebas

```bash
pytest -v
```

## Licencia

MIT
