# Publicar la librería en PyPI — paso a paso

Sólo se publica la **lógica** (`src/circuitos_cuanticos/`). `GUI.py`, `ejemplo_consola.py` y `tests/` quedan fuera del paquete porque `pyproject.toml` busca paquetes únicamente dentro de `src/`.

## 0. Estructura que debe tener el proyecto

```
circuitos-cuanticos/
├── pyproject.toml          ← metadatos y configuración de empaquetado
├── README.md               ← se muestra como página del proyecto en PyPI
├── LICENSE
├── src/
│   └── circuitos_cuanticos/
│       ├── __init__.py     ← API pública y __version__
│       └── core.py         ← la lógica
├── tests/test_core.py
├── GUI.py                  ← NO se publica
└── ejemplo_consola.py      ← NO se publica
```

> El *layout* `src/` obliga a instalar el paquete para probarlo, así se detectan errores de empaquetado antes de publicar.

## 1. Entorno virtual y herramientas

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1           # Linux/macOS: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[gui,dev]"   # tu paquete en modo editable + matplotlib, pytest, build, twine
```

Si PowerShell bloquea `Activate.ps1`: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (una sola vez).

El prompt mostrará `(.venv)` mientras el entorno esté activo. Toda instalación y ejecución debe hacerse así.

## 2. Verificar que todo funciona

```bash
pytest -v
python ejemplo_consola.py
python GUI.py
```

## 3. Elegir un nombre único y la versión

1. Busca el nombre en <https://pypi.org/search/>. Si `circuitos-cuanticos` ya existe, usa por ejemplo `circuitos-cuanticos-tunombre`.
2. Edita en `pyproject.toml`: `name`, `authors`, `[project.urls]`.
3. La versión sigue *versionado semántico* `MAYOR.MENOR.PARCHE`. Debe coincidir en `pyproject.toml` y en `__init__.py` (`__version__`).
4. **PyPI no permite subir dos veces la misma versión**, ni siquiera borrándola. Cada publicación necesita un número nuevo.

> Nombre del proyecto (con guion) ≠ nombre del módulo (con guion bajo):
> se instala con `pip install circuitos-cuanticos` y se importa con `import circuitos_cuanticos`.

## 4. Construir los distribuibles

```bash
python -m build
```

Se crean dos archivos en `dist/`:

* `circuitos_cuanticos-0.1.0.tar.gz` — distribución de código fuente (*sdist*)
* `circuitos_cuanticos-0.1.0-py3-none-any.whl` — rueda (*wheel*), lo que `pip` instala

Comprueba los metadatos:

```bash
python -m twine check dist/*
```

## 5. Crear las cuentas y los tokens

1. Cuenta en **TestPyPI** (ensayo): <https://test.pypi.org/account/register/>
2. Cuenta en **PyPI** (real): <https://pypi.org/account/register/>
   Son cuentas independientes. Ambas exigen activar autenticación de dos factores (2FA).
3. En cada sitio: *Account settings → API tokens → Add API token*. Copia el token (empieza por `pypi-`); sólo se muestra una vez.

Opcional: guarda los tokens en `~/.pypirc` (en Windows `C:\Users\TU_USUARIO\.pypirc`) para no escribirlos cada vez. **Nunca subas este archivo a GitHub.**

```ini
[pypi]
  username = __token__
  password = pypi-AgEIcHlwaS5vcmc...

[testpypi]
  username = __token__
  password = pypi-AgENdGVzdC5weXBp...
```

## 6. Ensayo en TestPyPI

```bash
python -m twine upload --repository testpypi dist/*
```

Si no configuraste `.pypirc`, el usuario es literalmente `__token__` y la contraseña es el token.

Prueba la instalación en un entorno limpio:

```bash
python -m venv /tmp/prueba && source /tmp/prueba/bin/activate     # (Windows: otra carpeta y Scripts\activate)
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            circuitos-cuanticos
python -c "import circuitos_cuanticos as cc; print(cc.__version__, cc.CatalogoCircuitos.disponibles())"
```

`--extra-index-url` es necesario porque `numpy` no está en TestPyPI.

## 7. Publicación real en PyPI

```bash
python -m twine upload dist/*
```

Desde ese momento cualquiera puede hacer:

```bash
pip install circuitos-cuanticos
```

## 8. Publicar una versión nueva

1. Haz los cambios y corre `pytest`.
2. Sube la versión en `pyproject.toml` y `__init__.py` (p. ej. `0.1.0 → 0.2.0`).
3. Borra la carpeta `dist/` vieja.
4. `python -m build` → `python -m twine check dist/*` → `python -m twine upload dist/*`.

## Resumen: secuencia completa en consola (Windows PowerShell)

Requisitos previos: nombre único y versión en `pyproject.toml` y `__init__.py`, y los dos tokens guardados en `C:\Users\SU_USUARIO\.pypirc` (secciones `[testpypi]` y `[pypi]`).

```powershell
# 0. Ubicarse en el proyecto y activar el entorno
cd C:\Users\Usuario\proyectos\circuitos-cuanticos
.\.venv\Scripts\Activate.ps1

# 1. Borrar construcciones anteriores
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

# 2. Construir  (crea dist\*.tar.gz y dist\*.whl)
python -m build

# 3. Revisar  (debe decir PASSED dos veces)
python -m twine check dist/*

# 4. Subir a TestPyPI  (usa la sección [testpypi] de .pypirc)
python -m twine upload --repository testpypi dist/*

# 5. Probar en un entorno limpio
python -m venv C:\temp\prueba
C:\temp\prueba\Scripts\Activate.ps1
python -m pip install `
    --index-url https://test.pypi.org/simple/ `
    --extra-index-url https://pypi.org/simple/ `
    circuitos-cuanticos-sunombre
python -c "import circuitos_cuanticos as cc; print(cc.__version__)"

# 6. Volver al proyecto y subir LOS MISMOS archivos a PyPI  (sección [pypi])
deactivate
cd C:\Users\Usuario\proyectos\circuitos-cuanticos
.\.venv\Scripts\Activate.ps1
python -m twine upload dist/*
```

En PowerShell, el acento grave `` ` `` al final de una línea continúa el comando en la línea siguiente.

## 9. (Avanzado) Publicación automática con GitHub Actions

PyPI admite *Trusted Publishing*: se vincula el repositorio de GitHub al proyecto en PyPI (*Your projects → Manage → Publishing*) y un flujo de trabajo publica sin guardar tokens. Archivo `.github/workflows/publicar.yml`:

```yaml
name: Publicar en PyPI
on:
  release:
    types: [published]
jobs:
  publicar:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build && python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Cada vez que crees un *Release* en GitHub, la versión se publica sola.

## Errores frecuentes

| Mensaje | Causa | Solución |
|---|---|---|
| `403 Forbidden` / *not allowed to upload* | El nombre ya pertenece a otra persona | Cambia `name` en `pyproject.toml` |
| `400 File already exists` | Esa versión ya se subió | Incrementa la versión y reconstruye |
| `ModuleNotFoundError` tras instalar | El paquete no está en `src/` o falta `__init__.py` | Revisa la estructura |
| `InvalidDistribution` en `twine check` | README o metadatos mal formados | Corrige `pyproject.toml` / `README.md` |
| `No module named tkinter` (Linux) | tkinter no viene con algunos Python del sistema | `sudo apt install python3-tk` |
