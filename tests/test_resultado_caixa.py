#!/usr/bin/env python

from bs4 import BeautifulSoup
from sims.base import SimulacaoResultadoBase
from sims.caixa import SimuladorCaixa
from util import Decimal2
from config.layout import TXT_SISTEMA_AMORTIZACAO_INI, SIMULACAO_RESULTADO_CAIXA_CAMPOS


class SimulacaoResultadoCaixa(SimulacaoResultadoBase):
    _prazo_max: int = 0
    _cota_max: int = 0
    _valor_entrada: Decimal2 = Decimal2('0')
    _subsidio_casa_verde_amarela: Decimal2 = Decimal2('0')

    def __init__(self, obj_simulador: SimuladorCaixa, html: str):
        super().__init__()
        self.obj_simulador = obj_simulador
        
        self._extrair_dados(html)

    @property
    def prazo_max(self) -> str:
        return f'{self._prazo_max} meses'
    
    @prazo_max.setter
    def prazo_max(self, v: int | str):
        if type(v) is str:
            if ' ' in v:
                v = v.split(' ')[0]
            v = int(v)
        if type(v) is not int:
            raise TypeError('Tipo prazo_max precisa ser inteiro.')
        
        self._prazo_max = v

    @property
    def cota_max(self) -> str:
        return f'{self._cota_max}%'
    
    @cota_max.setter
    def cota_max(self, v: int | str):
        if type(v) is str and '%' in v:
            v = int(v.split('%')[0])
        if type(v) is not int:
            raise TypeError('cota_max de financiamento precisa ser inteiro.')

        self._cota_max = v

    @property
    def valor_entrada(self) -> str:
        return self._valor_entrada.formatar_moeda()

    @valor_entrada.setter
    def valor_entrada(self, v: str | Decimal2):
        self._valor_entrada = self._validar_decimal(v)

    @property
    def subsidio_casa_verde_amarela(self) -> str:
        return self._subsidio_casa_verde_amarela.formatar_moeda()

    @subsidio_casa_verde_amarela.setter
    def subsidio_casa_verde_amarela(self, v: str | Decimal2):
        self._subsidio_casa_verde_amarela = self._validar_decimal(v)

    def _extrair_dados(self, html: str):
        bs = BeautifulSoup(html, 'html.parser')

        titulo = bs.find('h3', attrs={'class': 'simulation-result-title zeta'})
        self.titulo = titulo.text.strip()

        tables = bs.find_all('table', attrs={'class': 'simple-table'})
        num_tables = len(tables)

        get_desc = lambda : tds[0].text.strip()
        get_valor = lambda : tds[1].text.strip()

        trs = tables[0].find_all('tr')
        campo: str = ''
        for i in range(0, len(trs)):
            tds = trs[i].find_all('td')
            if get_desc() in SIMULACAO_RESULTADO_CAIXA_CAMPOS:
                campo = SIMULACAO_RESULTADO_CAIXA_CAMPOS[get_desc()]
                setattr(self, campo, get_valor())
            elif get_desc().startswith(TXT_SISTEMA_AMORTIZACAO):
                self.sistema_amortizacao = get_valor()

    def __str__(self) -> str:
        s = self
        b: str = self._b
        sim: SimuladorCaixa = self.obj_simulador
        txt: str = (
            f'{b}{s.titulo}{b}\n'
            '-----------------------------------\n'
            f'{b}Valor do imóvel:{b} {s.valor_imovel}\n'
            f'{b}Prazo máximo:{b} {s.prazo_max}\n'                # implementar?
            f'{b}Prazo escolhido:{b} {s.prazo}\n'                 # implementar?
            f'{b}Cota máxima financiamento:{b} {s.cota_max}\n'
            f'{b}Valor da entrada:{b} {s.valor_entrada}\n'
        )
        if self._subsidio_casa_verde_amarela:
            txt += f'{b}Subsídio Casa Verde e Amarela{b}: {s.subsidio_casa_verde_amarela}\n'
        txt += (
            f'{b}Valor do financiamento:{b} {s.valor_financiamento}\n'
            f'{b}Sistema de amortização:{b} {s.sistema_amortizacao}\n'
            '\n'
            f'{b}Primeira prestação:{b} {s.primeira_prestacao}\n'
            f'{b}Última prestação:{b} {s.ultima_prestacao}\n'
        )

        return txt

def test1():
    sim_caixa = SimuladorCaixa()
    sim_caixa.valor_imovel = '50.000,22'
    sim_caixa.valor_entrada = '20.000'
    #sim_caixa.prazo
    #sim_caixa.prazo_max


    html: str = ''
    with open('tests/resultado-caixa.html') as f:
        html = f.read()

    src = SimulacaoResultadoCaixa(
        obj_simulador=sim_caixa, html=html
    )
    print(src)

if __name__ == '__main__':
    Decimal2.setar_local_pt_br()
    test1()