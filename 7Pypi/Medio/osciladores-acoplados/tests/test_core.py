"""Pruebas de la lógica. Ejecutar con:  pytest -v"""

import numpy as np
import pytest

from osciladores_acoplados import (
    EulerExplicito, FabricaIntegradores, ModosNormales, RungeKutta4,
    Simulador, SistemaOsciladores, VelocityVerlet,
)


def test_frecuencias_dos_masas_tres_resortes():
    # Resultado de libro: ω1 = sqrt(k/m), ω2 = sqrt(3k/m)
    m, k = 2.0, 8.0
    sis = SistemaOsciladores([m, m], [k, k, k])
    w, _ = sis.modos_normales()
    assert np.allclose(w, [np.sqrt(k / m), np.sqrt(3 * k / m)])


def test_cadena_uniforme_formula_analitica():
    # ω_j = 2 sqrt(k/m) sin(jπ / (2(N+1)))
    n, m, k = 5, 1.0, 4.0
    sis = SistemaOsciladores.uniforme(n, m, k)
    j = np.arange(1, n + 1)
    esperado = 2 * np.sqrt(k / m) * np.sin(j * np.pi / (2 * (n + 1)))
    assert np.allclose(sis.modos_normales()[0], esperado)


def test_modos_ortonormales_respecto_a_la_masa():
    sis = SistemaOsciladores([1, 2, 3], [5, 1, 2, 7])
    _, phi = sis.modos_normales()
    assert np.allclose(phi.T @ sis.matriz_masa @ phi, np.eye(3))


def test_sistema_libre_tiene_modo_de_frecuencia_cero():
    sis = SistemaOsciladores.uniforme(3, extremos_fijos=False)
    assert np.isclose(sis.modos_normales()[0][0], 0.0)


@pytest.mark.parametrize("estrategia", [RungeKutta4(), VelocityVerlet()])
def test_numericos_coinciden_con_exacto(estrategia):
    sis = SistemaOsciladores([1, 1.5, 1], [10, 4, 4, 10])
    x0, v0 = [0.2, 0, -0.1], [0, 0.3, 0]
    exacto = ModosNormales().resolver(sis, x0, v0, 10, 0.001)
    numerico = estrategia.resolver(sis, x0, v0, 10, 0.001)
    assert np.allclose(exacto.x, numerico.x, atol=1e-4)


def test_verlet_conserva_energia_y_euler_no():
    sis = SistemaOsciladores.uniforme(3, 1, 10)
    x0, v0 = [0.1, 0, 0], [0, 0, 0]
    ver = VelocityVerlet().resolver(sis, x0, v0, 50, 0.01)
    eul = EulerExplicito().resolver(sis, x0, v0, 50, 0.01)
    assert np.max(np.abs(ver.error_energia_relativo)) < 1e-2
    assert eul.error_energia_relativo[-1] > 0.5


def test_condicion_modo_excita_un_solo_modo():
    sis = SistemaOsciladores.uniforme(4, 1, 1)
    x0 = sis.condicion_modo(2)
    _, phi = sis.modos_normales()
    q = phi.T @ sis.matriz_masa @ x0
    assert np.count_nonzero(np.abs(q) > 1e-10) == 1


def test_fabrica_y_simulador_con_observador():
    recibidos = []
    sim = Simulador(SistemaOsciladores.uniforme(2))
    sim.suscribir(recibidos.append)
    for nombre in FabricaIntegradores.disponibles():
        sim.estrategia = FabricaIntegradores.crear(nombre)
        sim.ejecutar([0.1, 0], [0, 0], 1, 0.01)
    assert [r.metodo for r in recibidos] == FabricaIntegradores.disponibles()


@pytest.mark.parametrize("masas, constantes", [
    ([], [1]), ([1, -1], [1, 1, 1]), ([1, 1], [1, 1]), ([1], [1, -2]),
])
def test_validaciones(masas, constantes):
    with pytest.raises(ValueError):
        SistemaOsciladores(masas, constantes)


def test_metodo_desconocido():
    with pytest.raises(ValueError):
        FabricaIntegradores.crear("Magia")
