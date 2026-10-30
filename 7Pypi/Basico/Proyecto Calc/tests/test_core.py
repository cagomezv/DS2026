from Calculadora import Calculadora

def test_suma():
    calc = Calculadora()
    calc.introducir_digito(5)
    calc.introducir_operador('+')
    calc.introducir_digito(7)
    calc.calcular()
    assert calc.valor_actual() == 12.0

def test_signo():
    calc = Calculadora()
    calc.introducir_digito(9)
    calc.introducir_operador('s')
    assert calc.valor_actual() == -9.0
