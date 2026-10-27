from math import sqrt
from abc import ABC, abstractmethod

suma = lambda x, y: x + y
resta = lambda x, y: x - y
multiplicacion = lambda x, y: x * y
division = lambda x, y: x / y
cambio_de_signo = lambda x: -x
raiz = lambda x: sqrt(x)

binarios = {
    '+': suma,
    '-': resta,
    '*': multiplicacion,
    '/': division
}

unarios = {
    's': cambio_de_signo,
    'r': raiz
}

class Calculadora:

    def __init__(self):
        self.reset()

    def reset(self):
        self._estado = EstadoInicial(self, 0)

    def introducir_digito(self, digito):
        self._estado.introducir_digito(digito)

    def introducir_operador(self, operador):
        try:
            self._estado.introducir_operador(operador)
        except:
            self.cambiar_estado(EstadoError(self))

    def calcular(self):
        try:
            self._estado.calcular()
        except:
            self.cambiar_estado(EstadoError(self))

    def valor_actual(self):
        return self._estado.valor_actual()

    def cambiar_estado(self, estado):
        self._estado = estado

class EstadoCalculadora(ABC):

    def __init__(self, calculadora):
        self._calculadora = calculadora

    def introducir_digito(self, digito):
        pass

    def introducir_operador(self, operador):
        pass

    def calcular(self):
        pass

    @abstractmethod
    def valor_actual(self):
        pass

    def cambiar_estado(self, nuevo_estado):
        self._calculadora.cambiar_estado(nuevo_estado)

class EstadoInicial(EstadoCalculadora):

    def __init__(self, calculadora, numero):
        super().__init__(calculadora)
        self._numero = numero

    def introducir_digito(self, digito):
        self.cambiar_estado(EstadoIntroducirPrimerOperando(self._calculadora, digito))

    def introducir_operador(self, operador):
        if operador in unarios:
            self._numero = unarios[operador](self._numero)
        elif operador in binarios:
            self.cambiar_estado(EstadoResultadoParcial(self._calculadora, self._numero, self._numero, operador))
        else:
            raise ValueError(f'No existe el operador "{operador}".')

    def valor_actual(self):
        return self._numero
    
class EstadoIntroducirPrimerOperando(EstadoCalculadora):

    def __init__(self, calculadora, digito):
        super().__init__(calculadora)
        self._digitos = []
        self.introducir_digito(digito)

    def introducir_digito(self, digito):
        digito = str(digito)
        if digito == '.':
            if '.' not in self._digitos:
                if len(self._digitos) == 0:
                    self._digitos.append('0')
                self._digitos.append(digito)
        else:
            if len(self._digitos) == 1 and self._digitos[0] == '0':
                self._digitos.clear()
            self._digitos.append(digito)

    def introducir_operador(self, operador):
        if operador in unarios:
            numero = self._get_numero()
            numero = unarios[operador](numero)
            self.cambiar_estado(EstadoInicial(self._calculadora, numero))
        elif operador in binarios:
            numero = self._get_numero()
            self.cambiar_estado(EstadoResultadoParcial(self._calculadora, numero, numero, operador))
        else:
            raise ValueError(f'No existe el operador "{operador}".')

    def _get_numero(self):
        return float(''.join(self._digitos))

    def valor_actual(self):
        return ''.join(self._digitos)

class EstadoResultadoParcial(EstadoCalculadora):

    def __init__(self, calculadora, primer_operando, numero, operador):
        super().__init__(calculadora)
        self._primer_operando = primer_operando
        self._numero = numero
        self._operador = operador

    def introducir_digito(self, digito):
        self.cambiar_estado(EstadoIntroducirSegundoOperando(self._calculadora, self._primer_operando, self._operador, digito))

    def introducir_operador(self, operador):
        if operador in unarios:
            self._numero = unarios[operador](self._numero)
        elif operador in binarios:
            self._operador = operador
        else:
            raise ValueError(f'No existe el operador "{operador}".')

    def calcular(self):
        resultado = binarios[self._operador](self._primer_operando, self._numero)
        self.cambiar_estado(EstadoInicial(self._calculadora, resultado))

    def valor_actual(self):
        return self._numero

class EstadoIntroducirSegundoOperando(EstadoIntroducirPrimerOperando):

    def __init__(self, calculadora, primer_operando, operador, digito):
        super().__init__(calculadora, digito)
        self._primer_operando = primer_operando
        self._operador = operador

    def introducir_operador(self, operador):
        if operador in unarios:
            resultado = unarios[operador](self._get_numero())
            self.cambiar_estado(EstadoResultadoParcial(self._calculadora, self._primer_operando, resultado, self._operador))
        elif operador in binarios:
            resultado = binarios[self._operador](self._primer_operando, self._get_numero())
            self.cambiar_estado(EstadoResultadoParcial(self._calculadora, resultado, resultado, operador))
        else:
            raise ValueError(f'No existe el operador "{operador}".')

    def calcular(self):
        resultado = binarios[self._operador](self._primer_operando, self._get_numero())
        self.cambiar_estado(EstadoInicial(self._calculadora, resultado))

class EstadoError(EstadoCalculadora):

    def __init__(self, calculadora):
        super().__init__(calculadora)

    def valor_actual(self):
        return '- Error -'