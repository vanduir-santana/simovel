#!/usr/bin/env python
# coding: utf-8
"""Base Simulador de Crédito Imobiliário
"""
__version__ = '0.6'
__author__ = 'Vanduir Santana Medeiros'


from ast import Param
from enum import Enum, auto
from decimal import Decimal
import enum
from typing import Type

import requests
from util import Decimal2, Cpf, Fone, FoneFormato, FoneTam, data_eh_valida, email_valido
from datetime import date
from exc import ErroEmail, ErroNomeCurto, ErroResultadoSimulacao, ErroResultadoTituloInvalido, ErroValorEntrada, ErroValorEntradaAbaixoPermitido, ErroValorEntradaAcimaPermitido, ErroValorImovel
from exc import ErroValorImovelAbaixoMin, ErroCPF, ErroCelular
from exc import ErroBancoInvalido, ErroRendaFamiliar, ErroDataNascimento
from exc import ErroPrazo, ErroUF
from config.geral import Parametros, Itau as CfgItau, Bradesco as ConfigBradesco
from config.geral import Santander as CfgSantander


UFS = (
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
    'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP',
    'SE', 'TO', 'DF'
)


class Banco(Enum):
    CAIXA = 1
    BRADESCO = 2
    ITAU = 3                        # padrão é adquirir direto do site itaú através do selenium
    ITAU_L = 4
    SANTANDER = 5
    ITAU_E_SANTANDER_L = 6          # quando usar api L pd extrair os
                                    # dados dos dois de uma só vez

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
    
    def __init__(self, banco: Banco=Banco.CAIXA) -> None:
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
        self._prazo_min: int = 1 if self.banco != Banco.BRADESCO else ConfigBradesco.PRAZO_MIN
        self._valor_entrada: Decimal2 = Decimal2('0')
        self._checar_limite_valor_entrada: bool = False
        #self._cod_sistema_amortizacao = 'undefined'
        #self._prestacao_max: Decimal2 = Decimal2('0')

        #self._cidades: list[dict] = []
        #self.cidades_filtro: list[str] = []
        #self.cidade_indice: int = -1

        # itaú, santander
        self._nome: str = ''
        self._email: str = ''

    @staticmethod
    def quantidade_bancos_habilitados() -> int:
        return len([b for b in Parametros.BANCOS_ACEITOS.values() if b])

    @staticmethod
    def ao_menos_um_banco_habilitado() -> bool:
        return SimuladorBase.quantidade_bancos_habilitados() >= 1

    @staticmethod
    def apenas_um_banco_habilitado() -> bool:
        return SimuladorBase.quantidade_bancos_habilitados() == 1

    @staticmethod
    def obter_primeiro_banco_habilitado() -> Banco:
        k: str; v: bool
        for k, v in Parametros.BANCOS_ACEITOS.items():
            if v:
                return getattr(Banco, k.upper())

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
                case (Banco.ITAU | Banco.ITAU_L):
                    fone = Fone.a_partir_de_fmt_somente_numeros_sem_ddi(v)
                    # não aceita sem o 9 adicional
                    if len(fone.valor) < FoneTam.DDD_CELULAR_NORMAL.value:
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
        if self._banco != Banco.ITAU and self._banco != Banco.ITAU_L:
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
        if v < self._prazo_min:
            raise ErroPrazo(f'Prazo abaixo do prazo mínimo: {self._prazo_min}.')
        self._prazo = v
    
    @property
    def prazo_max(self) -> str:
        if self._banco == Banco.CAIXA or self._banco == Banco.BRADESCO:
            return f'{self._prazo_max} meses'
        elif self._banco == Banco.ITAU or self._banco.ITAU_L:
            self._prazo_max = CfgItau.PRAZO_MAX
        elif self._banco == Banco.SANTANDER:
            self._prazo_max = CfgSantander.PRAXO_MAX
        
        return f'{self._prazo_max} anos'
    
    @prazo_max.setter
    def prazo_max(self, v):
        """Defini prazo máximo em meses.

        Args:
             v (str or int): o prazo pode ser tanto em string no padrão 
                da caixa (prazo meses) quanto um int.
        """
        #if self._banco == Banco.ITAU:
        #    raise ValueError('Não é permitido definir prazo máximo pra banco Itaú. Ver configs.')
        self._prazo_max = self._validar_prazo(v)

    @property
    def prazo_min(self) -> int:
        return self._prazo_min

    @prazo_min.setter
    def prazo_min(self, v: int):
        if type(v) is not int:
            raise TypeError('Tipo prazo_min precisa ser inteiro.')
        
        self._prazo_min = v

    def _validar_prazo(self, v) -> int:
        """Validar prazo."""
        if type(v) is str:
            # passado a partir do valor adquirido de módulo um sim. esp.
            if ' ' in v:
                prazo: str = ''
                match self._banco:
                    case (Banco.CAIXA | Banco.ITAU | Banco.ITAU_L | Banco.SANTANDER):
                        prazo = v.split(' ')[0]
                    case Banco.BRADESCO:
                        l: list = v.split(' ')
                        if len(l) == 2:
                            prazo = l[0]
                        else:
                            prazo = l[2]
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

    @property
    def checar_limite_valor_entrada(self) -> bool:
        return self._checar_limite_valor_entrada
    
    @checar_limite_valor_entrada.setter
    def checar_limite_valor_entrada(self, v: bool):
        if type(v) is not bool:
            raise TypeError('Tipo checar_limite_valor_entrada precisa ser bool.')

        self._checar_limite_valor_entrada = v

    # propriedades itaú, santander
    @property
    def valor_entrada(self) -> str:
        return self._valor_entrada.formatar_moeda(retirar_rs=True)

    @valor_entrada.setter
    def valor_entrada(self, v: str | Decimal2) -> None:
        """Defini o valor da entrada.

        Args:
            v (str | Decimal): valor da entrada.

        Raises:
            ErroValorEntrada: valor inválido.
            ErroValorEntradaAcimaPermitido: valor da entrada acima do permitido.
            ErroValorEntradaAcimaPermitido: valor da entrada acima do percentual permitido
            ErroValorEntradaAbaixoPermitido: valor da entrada abaixo do permitido.
        """
        if not v:
            self._valor_entrada = ''
            return

        d2: Decimal2
        try:
            d2 = Decimal2.a_partir_de_valor(v)
        except Exception as erro:
            raise ErroValorEntrada('Valor de entrada inválido.')
        
        if d2 >= self._valor_imovel:
            raise ErroValorEntradaAcimaPermitido(
                'Valor da entrada não pode ser igual ou acima do valor do imóvel.'
            )
        if self._checar_limite_valor_entrada:
            banco: str = self.banco.name.lower()
            MAX_PERC = Parametros.VALOR_ENTRADA_MAX_PERC
            MIN_PERC = Parametros.VALOR_ENTRADA_MIN_PERC[banco]
            max_valor_entrada: Decimal2 = Decimal2(self._valor_imovel * (MAX_PERC / 100))
            min_valor_entrada: Decimal2 = Decimal2(self._valor_imovel * (MIN_PERC / 100))
            if d2 > max_valor_entrada:
                raise ErroValorEntradaAcimaPermitido(
                    f'Valor da entrada não pode ser acima de {MAX_PERC}% ({max_valor_entrada.formatar_moeda()})do valor do imóvel ({self._valor_imovel.formatar_moeda()}).'
                )
            if MIN_PERC is not None \
               and d2 < min_valor_entrada:
                raise ErroValorEntradaAbaixoPermitido(
                    f'Valor da entrada não pode ser menor que {MIN_PERC}% ({min_valor_entrada.formatar_moeda()}) do valor do imóvel ({self._valor_imovel.formatar_moeda()}).'
                )

        self._valor_entrada = d2

    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, v: str):
        if type(v) != str:
            raise TypeError('Tipo do nome precisa ser str.')
        if len(v) < 4:
            raise ErroNomeCurto('Nome precisa ter pelo menos 4 caracteres.')
        if not ' ' in v:
            raise ErroNomeCurto('Favor digitar sobrenome.')
        
        l_nome: list = v.split(' ')
        if len(l_nome) == 1:
            raise ErroNomeCurto('Digitar também o sobrenome.')

        if len(l_nome[0].strip()) < 4 and len(l_nome[0].strip()) < 2:
            raise ErroNomeCurto('Nome ou sobrenome muito curto.')

        self._nome = v
    
    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, v: str):
        try:
            email_valido(v)
        except TypeError:
            raise
        except ErroEmail:
            raise
        
        self._email = v

    def simular(self) -> 'SimulacaoResultadoBase':
        """Sobrecarregar esse método."""
        pass

    # def simular_itau(self):
    #     TAXA_JUROS_AO_ANO = Decimal(9.7) / 100
    #     #CESH_AO_ANO = Decimal(3.31) / 100
    #     #CUSTOS_ADMINISTRACAO = Decimal(25)

    #     #CUSTO_EFETIVO_TOTAL_AO_ANO = Decimal(10.5) / 100

    #     valor_imovel: Decimal = Decimal(200000)
    #     valor_financiamento: Decimal = Decimal(160000)
    #     prazo: int = 360
    #     taxa_juros_ao_mes: Decimal = Decimal(TAXA_JUROS_AO_ANO) / 12
    #     idade: int
    #     TR: int
    #     #cesh_ao_mes: Decimal = Decimal(CESH_AO_ANO) / 12

    #     #custo_efetivo_total_ao_mes: Decimal = Decimal(CUSTO_EFETIVO_TOTAL_AO_ANO) / 12

    #     parcela: int = 0
    #     amortizacao: Decimal = Decimal(0)
    #     juros: Decimal = Decimal(0)
    #     valor_prestacao: Decimal = Decimal(0)
    #     saldo_devedor: Decimal = valor_financiamento
    #     prestacao: Decimal = Decimal(0)

    #     # cálculo
    #     parcela = 1
    #     amortizacao = saldo_devedor / prazo
    #     #juros = saldo_devedor * taxa_juros_ao_mes
    #     #seguros: Decimal = saldo_devedor * cesh_ao_mes
    #     #prestacao = amortizacao + juros + seguros + CUSTOS_ADMINISTRACAO
    #     #saldo_devedor -= 

    #     #juros = saldo_devedor * custo_efetivo_total_ao_mes
    #     #prestacao = amortizacao + juros + CUSTOS_ADMINISTRACAO

    #     juros = saldo_devedor * taxa_juros_ao_mes
    #     prestacao = amortizacao + juros

    #     print(f'{amortizacao=}')
    #     print(f'{juros=}')
    #     print(f'{prestacao=}')


class SimuladorBaseL(SimuladorBase):
    """Implementação simulador de crédito imobiliário Itaú e Santander
    baseado na API do sistema Loft.
    """
    URL = 'https://credit-bff.loft.com.br/mortgage-simulation/potential_with_bank_rates'

    def __init__(self, banco: Banco, nome: str, email: str, 
            valor_imovel: str | Decimal2, valor_entrada: str | Decimal2,
            data_nascimento: str, prazo: int, 
            renda_familiar: str | Decimal2) -> None:
        super().__init__(banco)
        self.nome = nome
        self.email = email
        self.valor_imovel = valor_imovel
        self.valor_entrada = valor_entrada
        self.data_nascimento = data_nascimento
        self.prazo = prazo
        self.renda_familiar = renda_familiar

    @classmethod
    def a_partir_de_obj_limpo(cls) -> 'SimuladorBaseL':
        """Retorna objeto sem definir nenum atributo.

        Returns:
            SimuladorBaseL: objeto a ser retornado
        """
        return cls(
            Banco.ITAU, 'Bastião Teste', 'teste@uai.com', 
            '', '', '08/02/1998', 30, ''
        )

    def _obter_headers(self) -> dict:
        return {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json;charset=UTF-8',
            'Host': 'credit-bff.loft.com.br',
            'Origin': 'https://loft.com.br',
            'Referer': 'https://loft.com.br/loftcred/financiamento-imobiliario/simulador?origin=LANDING_PAGE',
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="99", "Opera";v="85"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': "Windows",
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36 OPR/85.0.4341.60'
        }

    def _obter_payload(self) -> dict:
        return {
            "downPayment": self._valor_entrada.str_inteiro(),
            "income": self._renda_familiar.str_inteiro(),
            "propertyValue": self._valor_imovel.str_inteiro(),
            "purchaseMoment": "THREE_TO_FIVE_MONTHS",
            "term": str(self._prazo),
            "user": {
                "name": self.nome,
                "email": self.email,
                "birthDate": self._data_nascimento.strftime('%Y-%m-%d'),    #"2000-02-01"
            },
            "banksRates": [],
            "totalEffectiveCost": 0,
            "isItauCampaign": False,
            "isFoxterOrigin": False,
            "origin": "LANDING_PAGE"
        }

    def _extrair_simulacao(self) -> list:
        """Extrai simulação do json retornado da API Loft.

        Raises:
            ErroResultadoSimulacao: sem nenhum retorno.
            ErroResultadoSimulacao: resultado da simulação retornou erro.
            ErroResultadoSimulacao: não encontrou o banco no resultado.
            ErroResultadoSimulacao: banco não implementado.

        Returns:
            list: contem os banco(s) com o(s) resultado(s) da simulação.
        """
        headers: dict = self._obter_headers()
        payload: dict = self._obter_payload()

        r = requests.post(self.URL, json=payload, headers=headers)
        json: dict = r.json()
        if not json:
            raise ErroResultadoSimulacao('Resultado da simulação vazio.')
        elif not 'banksSimulation' in json and 'statusCode' in json:
            raise ErroResultadoSimulacao('Resultado da simulação retornou erro.')

        resultados: list[dict] = []
        T_ITAU, T_SANTANDER = 'Itaú', 'Santander'

        if self._banco == Banco.ITAU_L:
            resultados.append(json['banksSimulation'][2])
            if resultados[0]['bankProvider'] != T_ITAU:
                raise ErroResultadoSimulacao(
                    f'Banco {T_ITAU} não encontrado no resultado da simulação.'
                )
        elif self._banco == Banco.SANTANDER:
            resultados.append(json['banksSimulation'][3])
            if resultados[0]['bankProvider'] != T_SANTANDER:
                raise ErroResultadoSimulacao(
                    f'Banco {T_SANTANDER} não encontrado no resultado da simulação.'
                )
        elif self._banco == Banco.ITAU_E_SANTANDER_L:
            resultados.append(json['banksSimulation'][2])
            resultados.append(json['banksSimulation'][3])
            if resultados[0]['bankProvider'] != T_ITAU \
               or resultados[1]['bankProvider'] != T_SANTANDER:
                raise ErroResultadoSimulacao(
                    f'Banco {T_ITAU} ou {T_SANTANDER} não encontrado no resultado da simulação.'
                )
        else:
            raise ErroResultadoSimulacao(
                f'Banco {self._banco} não implementado no resultado da simulação.'
            )        
        # #return d_banco['simulation']
        return resultados
    

class SimuladorItauSantanderL(SimuladorBaseL):
    """Implementação simuladores de crédito imobiliário Itaú e Santander
    baseado na API do sistema Loft.
    """
    TITULO_RES1 = 'Resultado Simulação Itaú'
    TITULO_RES2 = 'Resultado Simulação Santander'
    def __init__(self, nome: str, email: str, 
            valor_imovel: str | Decimal2, valor_entrada: str | Decimal2,
            data_nascimento: str, prazo: int, 
            renda_familiar: str | Decimal2) -> None:
        
        super().__init__(
            Banco.ITAU_E_SANTANDER_L, nome, email, valor_imovel, valor_entrada,
            data_nascimento, prazo, renda_familiar
        )

    def simular(self) -> list['SimulacaoResultadoBase']:
        """Simulador pros bancos Itaú e Santander. Retorna o resultado em
        apenas uma chamada.

        Returns:
            list: lista contendo os resultados da simulação pra Itaú e
                Santander.
        """
        resultados: list = self._extrair_simulacao()
        res_itau: dict = resultados[0]['simulation']
        res_san: dict = resultados[1]['simulation']
        sim_res_itau: SimulacaoResultadoBase
        sim_res_san: SimulacaoResultadoBase
        
        sim_res_itau = SimulacaoResultadoBase.a_partir_de_valores_l(
            self,
            self.TITULO_RES1,
            res_itau
        )
        sim_res_san = SimulacaoResultadoBase.a_partir_de_valores_l(
            self,
            self.TITULO_RES2,
            res_san
        )
        return [sim_res_itau, sim_res_san]



class SimulacaoResultadoBase:
    """Resultado da simulação, contém os dados do retorno da simulação,
    entre eles o título, valor do imóvel, prazo, valor do 
    financiamento, valor da entrada (Caixa), sistema de amortização,
    valor da prestação, primeira e última prestação (Caixa e Itaú).
    """
    #def __init__(self, tipo_resultado: TipoResultado=None) -> None:
    def __init__(self) -> None:
        self._titulo: str = ''
        self._valor_imovel: Decimal2 = Decimal2(0)
        self._prazo: int = 0
        self._valor_financiamento: Decimal2 = Decimal2(0)
        self._sistema_amortizacao: str = ''
        self._valor_prestacao: Decimal2 = Decimal2(0)

        # caixa, itaú, santander (primeira e última parcela)
        self._primeira_prestacao: Decimal2 = Decimal2(0)
        self._ultima_prestacao: Decimal2 = Decimal2(0)
        self._primeira_parcela: Decimal2 = self._primeira_prestacao
        self._ultima_parcela: Decimal2 = self._ultima_prestacao
        self._taxa_juros: Decimal2 = Decimal2('0')
        # itaú e santander
        self._somatorio_parcelas: Decimal2 = Decimal2('0')
        
        self._obj_simulador: SimuladorBase = None
        self._negrito_resultado: bool = True
        self._b: str = '*'

    @classmethod
    def a_partir_de_valores_l(cls, obj_simulador: SimuladorBase, 
                    titulo: str, v: dict) -> 'SimulacaoResultadoBase':
        """Retorna um objeto a partir dos valores do resultado da API L.

        Args:
            v (dict): dict contendo os campos a serem extraídos.
            obj_simulador (SimuladorBase): objeto referenciando o 
                simulador. É usado pra obter informações como
                valor_imovel e valor_entrada

        Returns:
            SimulacaoResultadoBase: retorna objeto com simulação.
        """
        taxa_juros: Decimal2 = \
            Decimal2(Decimal2(str(v['anualInterestRate'])) * 100)

        sim_res: SimulacaoResultadoBase = cls()
        sim_res.titulo = titulo
        sim_res.obj_simulador = obj_simulador
        sim_res.primeira_parcela = str(v['firstPaymentValue'])
        sim_res.ultima_parcela = str(v['lastPaymentValue'])
        sim_res.taxa_juros = taxa_juros
        sim_res.somatorio_parcelas = str(v['mortgageTotalPaymentValue'])
        sim_res.total_financiado = str(v['requestedValue'])
        sim_res.prazo = v['term']

        return sim_res
    
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
        return f'{self._prazo} meses'
    
    @prazo.setter
    def prazo(self, v: int | str):
        if type(v) is str:
            if ' ':
                v = int(v.split(' ')[0])
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
        # uma exceção na hora de extrair o resultado da simulação
        self._valor_financiamento = self._validar_decimal(v)

    @property
    def total_financiado(self) -> str:
        """Alias Itaú pra self.valor_financiamento"""
        return self.valor_financiamento

    @total_financiado.setter
    def total_financiado(self, v: str | Decimal2 | float):
        self.valor_financiamento = v

    @property
    def sistema_amortizacao(self) -> str:
        return self._sistema_amortizacao

    @sistema_amortizacao.setter
    def sistema_amortizacao(self, v: str):
        self._sistema_amortizacao = v

    @property
    def valor_prestacao(self) -> str:
        return self._valor_prestacao.formatar_moeda()

    def _validar_decimal(self, v: str | Decimal2 | float) -> Decimal2:
        if type(v) is str:
            if v.endswith('a.a.'):  # itaú (selenium)
                v = v.split('%')[0]
            return Decimal2.a_partir_de_valor(v)
        if type(v) is Decimal:
            return Decimal2(v)
        elif type(v) is Decimal2:
            return v
        elif type(v) is float:
            return Decimal2(str(v))
        else:
            return Decimal2(0)

    @valor_prestacao.setter
    def valor_prestacao(self, v: str | Decimal2 | float):
        self._valor_prestacao = self._validar_decimal(v)
    
    @property
    def valor_parcela(self) -> str:
        """Alias pra self.valor_prestacao"""
        return self.valor_prestacao
    
    @valor_parcela.setter
    def valor_parcela(self, v: str | Decimal2 | float):
        """Alias pra self.valor_prestacao"""
        self.valor_prestacao = v

    @property
    def primeira_prestacao(self) -> str:
        return self._primeira_prestacao.formatar_moeda()
    
    @primeira_prestacao.setter
    def primeira_prestacao(self, v: str | Decimal2 | float):
        self._primeira_prestacao = self._validar_decimal(v)
    
    @property
    def primeira_parcela(self) -> str:
        """Alias pra self.primeira_prestacao"""
        return self.primeira_prestacao
    
    @primeira_parcela.setter
    def primeira_parcela(self, v: str | Decimal2 | float):
        """Alias pra self.primeira_prestacao"""
        self.primeira_prestacao = v

    @property
    def ultima_prestacao(self) -> str:
        return self._ultima_prestacao.formatar_moeda()

    @ultima_prestacao.setter
    def ultima_prestacao(self, v: str | Decimal2 | float):
        self._ultima_prestacao = self._validar_decimal(v)
    
    @property
    def ultima_parcela(self) -> str:
        """Alias pra self.ultima_prestacao"""
        return self.ultima_prestacao
    
    @ultima_parcela.setter
    def ultima_parcela(self, v: str | Decimal2 | float):
        """Alias pra self.ultima_prestacao"""
        self.ultima_prestacao = v

    @property
    def taxa_juros(self) -> str:
        return f'{self._taxa_juros.formatar_moeda(True)}% ao ano'
    
    @taxa_juros.setter
    def taxa_juros(self, v: str | Decimal2 | float):
        self._taxa_juros = self._validar_decimal(v)

    @property
    def somatorio_parcelas(self) -> str:
        return self._somatorio_parcelas.formatar_moeda()

    @somatorio_parcelas.setter
    def somatorio_parcelas(self, v: str | Decimal2 | float):
        self._somatorio_parcelas = self._validar_decimal(v)

    @property
    def obj_simulador(self) -> SimuladorBase:
        return self._obj_simulador

    @obj_simulador.setter
    def obj_simulador(self, v: SimuladorBase):
        if not isinstance(v, SimuladorBase):
            raise TypeError('obj_simulador precisa ser do tipo SimuladorBase')
        
        self._obj_simulador = v

    @property
    def negrito_resultado(self) -> bool:
        return self._negrito_resultado

    @negrito_resultado.setter
    def negrito_resultado(self, v: bool):
        if not type(v) is bool:
            raise TypeError('negrito_resultado precisa ser do tipo bool.')
        self._b: str = '' if not v else '*'            
        self._negrito_resultado = v

    def __str__(self):
        TAM_TRACEJADO = Parametros.TAM_TRACEJADO
        s = self
        # simplificado
        b: str = self._b
        t: str = (
            f'{b}{s.titulo}{b}\n'
            f'{"-" * TAM_TRACEJADO}\n'
        )
        if self._obj_simulador:
            b: str = '' if not self._negrito_resultado else '*'
            t += (
                f'{b}Valor do Imóvel:{b} {s._obj_simulador.valor_imovel}\n'
                f'{b}Valor de Entrada:{b} {s._obj_simulador.valor_entrada}\n'
                #f'Prazo: {s._obj_simulador.prazo}\n'
                f'{b}Prazo:{b} {s.prazo}\n'
            )
        t += (
            f'{b}Primeira Parcela:{b} {s.primeira_parcela}\n'
            f'{b}Última Parcela:{b} {s.ultima_parcela}\n'
            f'{b}Taxa de Juros:{b} {s.taxa_juros}\n'
        )
        t += (
            f'{b}Somatório das Parcelas:{b} {s.somatorio_parcelas}\n'
            f'{b}Total Financiado:{b} {s.total_financiado}\n'
        )
        return t


class SiteImobiliaria:
    """Faz interações com o site da imobiliária e traz os dados pro 
    cliente através de uma URL. Nesse endereço já seram filtrados os
    imóveis de acordo com os dados passados pelo simulador, na faixa
    pretendida.
    """
    #url_base = 'https://itamarzinimoveis.com.br/imovel?operacao=1&tipoimovel=&imos_codigo=&empreendimento=&destaque=false&vlini=85000.00&vlfim=170000.00&exclusivo=false&cidade=&pais=1&filtropais=false&order=maxval&limit=9&page=0&ttpr_codigo=1'
    #url_base = 'https://itamarzinimoveis.com.br/imovel?operacao=1&tipoimovel=&imos_codigo=&empreendimento=&destaque=false&vlini={}&vlfim={}&exclusivo=false&cidade=&pais=1&filtropais=false&order=minval&limit=9&page=0&ttpr_codigo=1'
    #url_base = 'https://www.itamarzinimoveis.com.br/imoveis/a-venda/casa?preco-de-venda=200000~400000'
    url_base = 'https://www.itamarzinimoveis.com.br/imoveis/a-venda/casa?preco-de-venda={}~{}&ordenar=menor-valor'
    
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
        valor_imovel_inicial: str = f'{self._valor_imovel_inicial:.0f}'
        valor_imovel_final: str = f'{self._valor_imovel_final:.0f}'

        return self.url_base.format(valor_imovel_inicial, valor_imovel_final)


def test1():
    #s = SimuladorBase(Banco.ITAU)
    #s.simular_itau()
    pass

def test2() -> bool:
    nome: str = 'Blase Pascal'
    email: str = 'blasep318@gmail.com'
    #valor_imovel: str = '200000'
    #valor_entrada: str = '40000'
    valor_imovel: str = '140000'
    valor_entrada: str = '26000'
    data_nascimento: str = '08/10/1999'
    prazo: int = 30
    #renda_familiar: str = '6422'
    renda_familiar: str = '2600'

    sim_itau_san = SimuladorItauSantanderL(
        nome, email, valor_imovel, valor_entrada,
        data_nascimento, prazo, renda_familiar
    )
    sim_resultados: list[SimulacaoResultadoBase] = sim_itau_san.simular()

    print()
    print(sim_resultados[0])
    print()
    print(sim_resultados[1])
    return True 


if __name__ == '__main__':
    import locale
    locale.setlocale(locale.LC_MONETARY, 'pt_BR.utf8')

    #test1()
    test2()