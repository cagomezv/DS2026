# circuitos-cuanticos

Simulador didáctico de **circuitos cuánticos** en Python, basado en el vector de estado y escrito sólo con NumPy.
Incluye los ejemplos típicos: **estado de Bell**, **GHZ**, **teleportación cuántica** y **algoritmo de Grover**.

Convención: el qubit 0 es el de la izquierda en el ket, `|q0 q1 q2⟩`.

## Instalación

```bash
pip install circuitos-cuanticos          # sólo la lógica (depende de numpy)
pip install "circuitos-cuanticos[gui]"   # + matplotlib para la interfaz gráfica
```

## Uso

```python
from circuitos_cuanticos import Circuito, H, CNOT, CatalogoCircuitos

bell = Circuito(2).agregar(H(0)).agregar(CNOT(0, 1))
print(bell.ejecutar().ket())             # 0.707|00⟩ + 0.707|11⟩
print(bell.estado.medir(1000))           # {'00': ~500, '11': ~500}

bell.deshacer()                          # patrón Command: vuelve un paso atrás
print(bell.estado.ket())                 # 0.707|00⟩ + 0.707|10⟩

grover = CatalogoCircuitos.grover(n=3, marcado=0b101)
print(grover.ejecutar().probabilidades())   # '101' con probabilidad ≈ 0.945
```

## Arquitectura

* `core.py` — toda la lógica, sólo con NumPy (sin interfaz gráfica).
  * **Command**: `Puerta` (comando abstracto con `aplicar` y `deshacer`) → `H`, `X`, `CNOT`, `Oraculo`, `Difusion`, `Medir`, …;
    `EstadoCuantico` es el receptor y `Circuito` el invocador (historial, paso a paso, deshacer).
  * Las puertas unitarias se deshacen con U†; `Medir` guarda una copia del estado (Memento) para poder deshacerse.
  * `FabricaPuertas` crea puertas por nombre; `CatalogoCircuitos` construye los ejemplos clásicos.
  * `Circuito.suscribir(funcion)` avisa después de cada paso (observador ligero).
* `GUI.py` — interfaz tkinter + matplotlib que sólo usa la API pública.

## Desarrollo

Una sola vez, desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[gui,dev]"
```

Si PowerShell bloquea `Activate.ps1`, ejecute una vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

En cada terminal nueva basta con activar el entorno y ejecutar:

```powershell
python GUI.py
python ejemplo_consola.py
pytest -v
```

> Si aparece `ModuleNotFoundError: No module named 'circuitos_cuanticos'`, la librería
> no está instalada en el Python que se está usando: active el entorno e instálela.

## Licencia

MIT
