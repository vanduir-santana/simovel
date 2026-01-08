#!/usr/bin/env python
# coding: utf-8
"""Simulador de Crédito Imobiliário Santander
"""

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.2'

from simovel.sims.base import Banco, SimuladorBase, SimulacaoResultadoBase
from simovel.sims.base import SimuladorBaseL
from simovel.util import Decimal2


TITULO = 'Resultado Simulação Santander'

class SimuladorSantanderL(SimuladorBaseL):
    """Implementação simulador de crédito imobiliário Santander baseado na API
    do sistema L.
    """    
    def __init__(self, nome: str, email: str, 
            valor_imovel: str | Decimal2, valor_entrada: str | Decimal2,
            data_nascimento: str, prazo: int, 
            renda_familiar: str | Decimal2) -> None:
        super().__init__(
            Banco.SANTANDER, nome, email, valor_imovel, valor_entrada,
            data_nascimento, prazo, renda_familiar
        )
        
    def simular(self) -> SimulacaoResultadoBase:
        resultados: list = self._extrair_simulacao()
        res_san: dict = resultados[0]['simulation']
        return SimulacaoResultadoBase.a_partir_de_valores_l(
            self,
            TITULO,
            res_san
        )


def test2() -> bool:
    nome: str = 'Blase Pascal'
    email: str = 'blasep318@gmail.com'
    valor_imovel: str = '200000'
    valor_entrada: str = '40000'
    data_nascimento: str = '08/10/1999'
    prazo: int = 30
    renda_familiar: str = '6422'

    sim_itau = SimuladorSantanderL(
        nome, email, valor_imovel, valor_entrada,
        data_nascimento, prazo, renda_familiar
    )
    sim_resultado: SimulacaoResultadoBase = sim_itau.simular()

    print()
    print(sim_resultado)
    return True


if __name__ == '__main__':
    import locale
    locale.setlocale(locale.LC_MONETARY, 'pt_BR.utf8')

    #test1()
    test2()
