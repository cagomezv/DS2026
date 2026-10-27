"""Pruebas de la lógica cuántica. Ejecutar con:  pytest -v"""

import numpy as np
import pytest

from circuitos_cuanticos import (CNOT, CZ, RY, RZ, SWAP, CatalogoCircuitos,
                                 Circuito, EstadoCuantico, FabricaPuertas, H,
                                 Medir, Toffoli, X, Z)


def test_estado_inicial_es_cero():
    assert EstadoCuantico(3).probabilidades() == {"000": 1.0}


def test_convencion_qubit_cero_a_la_izquierda():
    c = Circuito(3).agregar(X(0))
    assert c.ejecutar().probabilidades() == {"100": 1.0}


def test_hadamard_crea_superposicion():
    p = Circuito(1).agregar(H(0)).ejecutar().probabilidades()
    assert p == pytest.approx({"0": 0.5, "1": 0.5})


def test_bell_solo_00_y_11():
    p = CatalogoCircuitos.bell().ejecutar().probabilidades()
    assert p == pytest.approx({"00": 0.5, "11": 0.5})


def test_bell_qubit_entrelazado_tiene_bloch_nulo():
    e = CatalogoCircuitos.bell().ejecutar()
    assert np.allclose(e.bloch(0), 0, atol=1e-12)


def test_ghz():
    p = CatalogoCircuitos.ghz(4).ejecutar().probabilidades()
    assert p == pytest.approx({"0000": 0.5, "1111": 0.5})


@pytest.mark.parametrize("theta, phi", [(0.3, 0.0), (1.0, 0.5), (2.5, -1.2), (np.pi, 2.0)])
def test_teleportacion_transfiere_el_estado(theta, phi):
    original = EstadoCuantico(1)
    RY(0, theta).aplicar(original)
    RZ(0, phi).aplicar(original)
    final = CatalogoCircuitos.teleportacion(theta, phi).ejecutar()
    assert np.allclose(final.bloch(2), original.bloch(0), atol=1e-10)


@pytest.mark.parametrize("n, marcado", [(2, 3), (3, 5), (4, 9), (5, 17)])
def test_grover_encuentra_el_marcado(n, marcado):
    e = CatalogoCircuitos.grover(n, marcado).ejecutar()
    assert np.argmax(e.vector_probabilidades()) == marcado
    assert e.vector_probabilidades()[marcado] > 0.9


def test_deshacer_vuelve_al_estado_inicial():
    c = CatalogoCircuitos.teleportacion(0.7, 0.2).agregar(SWAP(0, 2)).agregar(Toffoli(0, 1, 2))
    c.ejecutar()
    while c.deshacer():
        pass
    assert np.allclose(c.estado.amplitudes, EstadoCuantico(3).amplitudes)


def test_atajos_de_grover_coinciden_con_la_matriz():
    from circuitos_cuanticos import Difusion, Oraculo
    rng = np.random.default_rng(0)
    v = rng.normal(size=8) + 1j * rng.normal(size=8)
    for puerta in (Oraculo(3, 5), Difusion(3)):
        rapido, lento = EstadoCuantico(3, v), EstadoCuantico(3, v)
        puerta.aplicar(rapido)
        lento.aplicar_matriz(puerta.matriz(), puerta.qubits)
        assert np.allclose(rapido.amplitudes, lento.amplitudes)


def test_grover_con_muchos_qubits_es_rapido():
    e = CatalogoCircuitos.grover(12, marcado=1234).ejecutar()
    assert e.vector_probabilidades()[1234] > 0.99


def test_puertas_son_unitarias():
    for p in [H(0), X(0), Z(0), RY(0, 0.4), CNOT(0, 1), CZ(0, 1), SWAP(0, 1), Toffoli(0, 1, 2)]:
        U = p.matriz()
        assert np.allclose(U.conj().T @ U, np.eye(U.shape[0]))


def test_medir_colapsa_y_deshacer_restaura():
    c = CatalogoCircuitos.bell().agregar(Medir(0, semilla=1))
    c.ejecutar()
    p = c.estado.probabilidades()
    assert p in ({"00": pytest.approx(1.0)}, {"11": pytest.approx(1.0)})
    c.deshacer()
    assert c.estado.probabilidades() == pytest.approx({"00": 0.5, "11": 0.5})


def test_medir_muchas_veces_respeta_born():
    e = CatalogoCircuitos.bell().ejecutar()
    conteo = e.medir(10000, semilla=0)
    assert set(conteo) == {"00", "11"}
    assert abs(conteo["00"] / 10000 - 0.5) < 0.03


def test_fabrica_y_observador():
    pasos = []
    c = Circuito(2)
    c.suscribir(lambda circ: pasos.append(circ.posicion))
    c.agregar(FabricaPuertas.crear("H", 0)).agregar(FabricaPuertas.crear("CNOT", 0, 1))
    c.paso(); c.paso(); c.deshacer()
    assert pasos == [1, 2, 1]


@pytest.mark.parametrize("accion", [
    lambda: Circuito(2).agregar(H(2)),
    lambda: CNOT(1, 1),
    lambda: FabricaPuertas.crear("CNOT", 0),
    lambda: FabricaPuertas.crear("Magia", 0),
    lambda: EstadoCuantico(2, [0, 0, 0, 0]),
])
def test_validaciones(accion):
    with pytest.raises((ValueError, IndexError)):
        accion()
