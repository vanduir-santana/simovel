#!/usr/bin/env python
# coding: utf-8
"""Base Simulador de Crédito Imobiliário
"""
__version__ = '0.4'
__author__ = 'Vanduir Santana Medeiros'


from ast import Param
from enum import Enum, auto
from decimal import Decimal
from util import Decimal2, Cpf, Fone, FoneFormato, FoneTam, data_eh_valida
from datetime import date
from exc import ErroResultadoTituloInvalido, ErroValorImovel
from exc import ErroValorImovelAbaixoMin, ErroCPF, ErroCelular
from exc import ErroBancoInvalido, ErroRendaFamiliar, ErroDataNascimento
from exc import ErroPrazo, ErroUF
from config.geral import Parametros, TipoResultado, Itau as CfgItau

UFS = (
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
    'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP',
    'SE', 'TO', 'DF'
)


class Banco(Enum):
    CAIXA = auto()
    BRADESCO = auto()
    ITAU = auto()
    SANTANDER = auto()


class TipoFinanciamento(Enum):
    """Tipo de financiamento (Caixa), tipo imóvel (Bradesco). Cada 
    módulo irá implementar seu próprio TipoFinanciamento por conta das
    peculiaridades de cada um.
    """
    NOVO = auto()
    USADO = auto()

#class FormatoResultado(Enum):
#    MENSAGEIRO = auto()     # whatsapp, botsite, onde a largura é limitada
#    PDF = auto()            # gera um arquivo PDF com detalhes da simulação
#    HTML = auto()           # gera uma página html


#class TipoImovel(Enum):
#    RESIDENCIAL = auto()
#    COMERCIAL = auto()


class SimuladorBase:
    URL1 = ''
    URL2 = ''
    
    def __init__(self, banco: Banco) -> None:
        self._banco: Banco = None
        self.banco = banco

        #self._tipo_financiamento = TipoFinanciamento.NOVO
        self._valor_imovel: Decimal2 = Decimal2('0')
        self._uf: str = 'GO'
        self._cpf: Cpf = Cpf(cpf='')
        self._celular: str = ''
        self._renda_familiar: Decimal2 = Decimal2(0)
        self._data_nascimento: date = ''
        #self._possui_relacionamento_caixa = False
        #self._tres_anos_fgts: bool = False
        #self._mais_de_um_comprador_dependente: bool = False
        #self._opcao_financiamento = OpcaoFinanciamento.PROGRAMA_CASA_VERDE_AMARELA
        self._prazo: int = 0
        self._prazo_max: int = 0
        self._valor_entrada: Decimal2 = Decimal2('0')
        #self._cod_sistema_amortizacao = 'undefined'
        #self._prestacao_max: Decimal2 = Decimal2('0')

        #self._cidades: list[dict] = []
        #self.cidades_filtro: list[str] = []
        #self.cidade_indice: int = -1

    @property
    def banco(self) -> Banco:
        return self._banco

    @banco.setter
    def banco(self, v: Banco):
        if type(v) is not Banco:
            raise ErroBancoInvalido('Banco inválido.')
        self._banco = v

    @property
    def valor_imovel(self) -> str:
        # padrao simulador caixa sem R$
        return self._valor_imovel.formatar_moeda(retirar_rs=True)

    @valor_imovel.setter
    def valor_imovel(self, v: str):
        if not v:
            self._valor_imovel = Decimal2(0)
            return
        
        valor_imovel: Decimal2
        try:
            valor_imovel = Decimal2.a_partir_de_valor(v)
        except Exception as erro:
            raise ErroValorImovel(erro)

        VALOR_IMOVEL_MIN = Decimal2(Parametros.VALOR_IMOVEL_MIN)
        if valor_imovel < VALOR_IMOVEL_MIN:
            raise ErroValorImovelAbaixoMin(f'O valor do imóvel precisa ser de no mínimo: {VALOR_IMOVEL_MIN.formatar_moeda()}')
        
        self._valor_imovel = valor_imovel

    @property
    def cpf(self) -> str:
        return self._cpf.formatar()

    @cpf.setter
    def cpf(self, v: str):
        try:
            self._cpf = Cpf(v)
            self._cpf.validar(disparar_erro=True)
        except ErroCPF:
            self._cpf = Cpf('')
            raise

    @property
    def celular(self) -> str:
        return self._celular

    @celular.setter
    def celular(self, v):
        fone: Fone
        try:
            match self._banco:
                case Banco.CAIXA:
                    fone = Fone.a_partir_de_fmt_caixa(v)
                case Banco.ITAU:
                    fone = Fone.a_partir_de_fmt_somente_numeros_sem_ddi(v)
                    # não aceita sem o 9 adicional
                    if len(fone.valor) != FoneTam.DDD_CELULAR_NORMAL.value:
                        raise ErroCelular('Celular com o tamanho errado.')
                case _:
                    fone = Fone.a_partir_de_fmt_comum(v)
        except ValueError as erro:
            self._celular = ''
            raise ErroCelular(f'{erro}')
        
        self._celular = fone.formatar()

    @property
    def renda_familiar(self) -> str:
        return self._renda_familiar.formatar_moeda(retirar_rs=True)
    
    @renda_familiar.setter
    def renda_familiar(self, v: str | float | int | Decimal) -> None:
        if not v:
            self._renda_familiar = ''
            return
        
        d2: Decimal2
        try:
            d2 = Decimal2.from_cur_str(v)
        except Exception as erro:
            raise ErroRendaFamiliar(erro)

        RENDA_FAMILIAR_MIN = Decimal2(Parametros.RENDA_FAMLIAR_MIN)
        if d2 < RENDA_FAMILIAR_MIN:
            raise ErroRendaFamiliar(f'O valor da renda familiar bruta de {d2.formatar_moeda()} é baixo, precisa ser de no mínimo: {RENDA_FAMILIAR_MIN.formatar_moeda()}.')

        self._renda_familiar = d2
    
    @property
    def data_nascimento(self) -> str:
        return self._data_nascimento.strftime('%d/%m/%Y') if self._data_nascimento else ''

    @data_nascimento.setter
    def data_nascimento(self, v: str):
        if not v:
            raise ErroDataNascimento('É preciso digitar a data de nascimento')
        
        DATA_FORMATOS = Parametros.DATA_FORMATOS
        dt_nasc: date = data_eh_valida(sdata=v, formatos=DATA_FORMATOS)
        if not dt_nasc:
            raise ErroDataNascimento(f'Data {v} inválida.')
        
        hj: date = date.today() - dt_nasc
        if (hj.days / 365.25) < Parametros.IDADE_MIN:
            raise ErroDataNascimento(f'Para financiar você precisar ter pelo menos {Parametros.IDADE_MIN} anos de idade.')
        
        self._data_nascimento = dt_nasc

    @property
    def prazo(self) -> str:
        if self._banco != Banco.ITAU:
            return f'{self._prazo} meses'
        else:
            return f'{self._prazo} anos'
    
    @prazo.setter
    def prazo(self, v):
        """Define prazo em meses (padrão caixa).

        Args:
            v (str or int): o prazo pode ser tanto em string no padrão 
                da caixa (prazo meses) quanto um int.

        Raises:
            ErroPrazo: Prazo precisa ser inteiro.
            ErroPrazo: Prazo inválido
            ErroPrazo: Prazo precisa ser inteiro.
        """
        v = self._validar_prazo(v)
        if self._prazo_max and v > self._prazo_max:
            raise ErroPrazo(f'Prazo acima do prazo máximo: {self.prazo_max}.')
        self._prazo = v
    
    @property
    def prazo_max(self) -> str:
        if self._banco != Banco.ITAU:
            return self._prazo_max
        else:
            self._prazo_max = CfgItau.PRAZO_MAX
    
    @prazo_max.setter
    def prazo_max(self, v):
        """Defini prazo máximo em meses. Para banco Itaú não é permitido,
        ver configs.

        Args:
             v (str or int): o prazo pode ser tanto em string no padrão 
                da caixa (prazo meses) quanto um int.
        """
        if self._banco == Banco.ITAU:
            raise ValueError('Não é permitido definir prazo máximo pra banco Itaú. Ver configs.')
        self._prazo_max = self._validar_prazo(v)

    def _validar_prazo(self, v) -> int:
        """Validar prazo."""
        if type(v) is str:
            # passado a partir do valor adquirido de módulo um sim. esp.
            if ' ' in v:
                match self._banco:
                    case Banco.CAIXA:
                        prazo = v.split(' ')[0]
                    case Banco.BRADESCO:
                        prazo = v.split(' ')[2]
                if not prazo.isdigit():
                    raise ErroPrazo('Prazo precisa ser inteiro')
                return int(prazo)
            elif v.isdigit():
                return int(v)
            else:
                raise ErroPrazo('Prazo inválido!')
        elif not type(v) is int:
            raise ErroPrazo('Prazo precisa ser inteiro.')
        elif type(v) is int:
            return v
        else:
            raise ErroPrazo('Prazo inválido!')

    @property
    def uf(self):
        return self._uf
    
    @uf.setter
    def uf(self, v:str):
        if type(v) is not str:
            raise ErroUF('UF precisa ser str.')

        if len(v) != 2:
            raise ErroUF('O tamanho da UF tem que ser 2.')

        v = v.upper()
        if not v in UFS:
            raise ErroUF(f'A UF {v} não existe')

        self._uf = v            

    #def teste(self) -> int:
    #    return self._prazo_max - 22

    def simular_itau(self):
        TAXA_JUROS_AO_ANO = Decimal(9.7) / 100
        #CESH_AO_ANO = Decimal(3.31) / 100
        #CUSTOS_ADMINISTRACAO = Decimal(25)

        #CUSTO_EFETIVO_TOTAL_AO_ANO = Decimal(10.5) / 100

        valor_imovel: Decimal = Decimal(200000)
        valor_financiamento: Decimal = Decimal(160000)
        prazo: int = 360
        taxa_juros_ao_mes: Decimal = Decimal(TAXA_JUROS_AO_ANO) / 12
        idade: int
        TR: int
        #cesh_ao_mes: Decimal = Decimal(CESH_AO_ANO) / 12

        #custo_efetivo_total_ao_mes: Decimal = Decimal(CUSTO_EFETIVO_TOTAL_AO_ANO) / 12

        parcela: int = 0
        amortizacao: Decimal = Decimal(0)
        juros: Decimal = Decimal(0)
        valor_prestacao: Decimal = Decimal(0)
        saldo_devedor: Decimal = valor_financiamento
        prestacao: Decimal = Decimal(0)

        # cálculo
        parcela = 1
        amortizacao = saldo_devedor / prazo
        #juros = saldo_devedor * taxa_juros_ao_mes
        #seguros: Decimal = saldo_devedor * cesh_ao_mes
        #prestacao = amortizacao + juros + seguros + CUSTOS_ADMINISTRACAO
        #saldo_devedor -= 

        #juros = saldo_devedor * custo_efetivo_total_ao_mes
        #prestacao = amortizacao + juros + CUSTOS_ADMINISTRACAO

        juros = saldo_devedor * taxa_juros_ao_mes
        prestacao = amortizacao + juros

        print(f'{amortizacao=}')
        print(f'{juros=}')
        print(f'{prestacao=}')


class SimulacaoResultadoBase:
    """Resultado da simulação, contém os dados do retorno da simulação,
    entre eles o título, valor do imóvel, prazo, valor do 
    financiamento, valor da entrada (Caixa), sistema de amortização,
    valor da prestação, primeira e última prestação (Caixa e Itaú).
    """
    def __init__(self, tipo_resultado: TipoResultado=None) -> None:
        self._titulo: str = ''
        self._valor_imovel: Decimal2 = Decimal2(0)
        self._prazo: int = 0
        self._valor_financiamento: Decimal2 = Decimal2(0)
        self._sistema_amortizacao: str = ''
        self._valor_prestacao: Decimal2 = Decimal2(0)

        if not tipo_resultado:
            self._tipo_resultado = Parametros.TIPO_RESULTADO_SIMULACAO
        else:
            self._tipo_resultado = tipo_resultado

    @classmethod
    def a_partir_de_tipo_resultado_comum(cls):
        return cls(TipoResultado.COMUM)

    @classmethod
    def a_partir_de_tipo_resultado_extra(cls):
        return cls(TipoResultado.EXTRA)

    @classmethod
    def a_partir_de_tipo_resultado_original(cls):
        return cls(TipoResultado.ORIGINAL)
    
    @property
    def titulo(self) -> str:
        return self._titulo
    
    @titulo.setter
    def titulo(self, v: str):
        self._titulo = v

    @property
    def valor_imovel(self) -> str:
        return self._valor_imovel.formatar_moeda()
    
    @valor_imovel.setter
    def valor_imovel(self, v: str | float | Decimal2):
        if not v:
            raise ErroValorImovel(
                'Valor imóvel do resultado da simulação inválido.')
        elif type(v) is str:
            try:
                self._valor_imovel = Decimal2.a_partir_de_valor(v)
            except ValueError as erro:
                raise ErroValorImovel(
                    'Valor imóvel do resultado da simulação inválido na conv.')
        elif type(v) is not float or type(v) is not Decimal2:
            raise ErroValorImovel(
                'Valor imóvel do resultado da simulação tipo inválido.')
        else:
            self._valor_imovel = Decimal2(v)
            
    @property
    def prazo(self):
        return self._prazo
    
    @prazo.setter
    def prazo(self, v: int | str):
        if type(v) is not int and type(v) is str and not v.isdigit():
            raise('Prazo do resultado da simulação inválido.')
        self._prazo = v

    @property
    def valor_financiamento(self) -> str:
        return self._valor_financiamento.formatar_moeda()

    @valor_financiamento.setter
    def valor_financiamento(self, v: str | Decimal2 | float):
        # certamente não precisa fazer validações aqui, pois se der 
        # algum problema a validação do valor do imóvel já vai gerar
        # uma exceção na hora de extrair o resultado da simulaç~~ao
        if type(v) is str:
            self._valor_financiamento = Decimal2.from_cur_str(v)
        elif type(v) is Decimal2 or type(v) is float:
            self._valor_financiamento = Decimal2(v)
        else:
            self._valor_financiamento = Decimal2(0)

    @property
    def sistema_amortizacao(self) -> str:
        return self._sistema_amortizacao

    @sistema_amortizacao.setter
    def sistema_amortizacao(self, v: str):
        self._sistema_amortizacao = v

    @property
    def valor_prestacao(self) -> str:
        return self._valor_prestacao.formatar_moeda()

    @valor_prestacao.setter
    def valor_prestacao(self, v: str | Decimal2 | float):
        if type(v) is str:
            self._valor_prestacao = Decimal2.from_cur_str(v)
        elif type(v) is Decimal2 or type(v) is float:
            self._valor_prestacao = Decimal2(v)
        else:
            self._valor_prestacao = Decimal2(0)


class SiteImobiliaria:
    """Faz interações com o site da imobiliária e traz os dados pro 
    cliente através de uma URL. Nesse endereço já seram filtrados os
    imóveis de acordo com os dados passados pelo simulador, na faixa
    pretendida.
    """
    #url_base = 'https://itamarzinimoveis.com.br/imovel?operacao=1&tipoimovel=&imos_codigo=&empreendimento=&destaque=false&vlini=85000.00&vlfim=170000.00&exclusivo=false&cidade=&pais=1&filtropais=false&order=maxval&limit=9&page=0&ttpr_codigo=1'
    url_base = 'https://itamarzinimoveis.com.br/imovel?operacao=1&tipoimovel=&imos_codigo=&empreendimento=&destaque=false&vlini={}&vlfim={}&exclusivo=false&cidade=&pais=1&filtropais=false&order=minval&limit=9&page=0&ttpr_codigo=1'
    MSG_VALOR_IMOVEL_TIPO_INVALIDO = 'Valor do imóvel precisa ser float, Decimal2 ou int.'

    def __init__(self, valor_imovel_inicial: float|Decimal2|int,
                       valor_imovel_final: float|Decimal2|int):
        if (not type(valor_imovel_inicial) in [float, Decimal2, int]
            or not type(valor_imovel_final) in [float, Decimal2, int]):
            raise ValueError(self.MSG_VALOR_IMOVEL_TIPO_INVALIDO)
        self._valor_imovel_inicial = valor_imovel_inicial
        self._valor_imovel_final = valor_imovel_final
        self._url = ''

    @classmethod
    def a_partir_de_valor_imovel(cls, valor_imovel: float|Decimal2|int,
                                 variacao_perc: int):
        if not type(valor_imovel) in [float, Decimal2, int]:
            raise ValueError(cls.MSG_VALOR_IMOVEL_TIPO_INVALIDO)

        valor_perc = valor_imovel * Decimal2(variacao_perc / 100)

        valor_inicial = Decimal2(int(valor_imovel - valor_perc))
        valor_final = Decimal2(int(valor_imovel + valor_perc))

        return cls(valor_inicial, valor_final)

    @property
    def url(self) -> str:
        valor_imovel_inicial: str = f'{self._valor_imovel_inicial:.2f}'
        valor_imovel_final: str = f'{self._valor_imovel_final:.2f}'

        return self.url_base.format(valor_imovel_inicial, valor_imovel_final)


def test1():
    s = SimuladorBase(Banco.ITAU)
    s.simular_itau()


if __name__ == '__main__':
    test1()