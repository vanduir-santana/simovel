#!/usr/bin/env python
# coding: utf-8
"""Simulador de Crédito Imobiliário Bradesco
"""

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.10'


from datetime import date
from decimal import Decimal
from bs4 import BeautifulSoup
import requests
import time
from simovel.sims.base import Banco, SimuladorBase, SimulacaoResultadoBase
from simovel.sims.base import TipoFinanciamento
from simovel.config.geral import Parametros
from simovel.config import geral as config_geral
from enum import Enum, auto
from simovel.exceptions import ErroDataNascimento, ErroDataNascimentoConjuge
from simovel.exceptions import ErroFinanciarDespesas, ErroFormaPagamentoInvalida
from simovel.exceptions import ErroPrazo, ErroSeguradoraInvalida
from simovel.exceptions import ErroSistemaAmortizacaoInvalido, ErroSituacaoImovel
from simovel.exceptions import ErroTipoImovel, ErroValorFinanciamento, ErroValorImovel
from simovel.exceptions import ErroValorMaxFinanciamento, ErroResultadoCampoNaoRetornado
from simovel.util import Decimal2, Cpf, data_eh_valida


class TipoImovel(Enum):
    RESIDENCIAL_POUPANCA = 14   # RESIDENCIAL POUPANCA
    RESIDENCIAL = 1             # RESIDENCIAL
    COMERCIAL = 2               # COMERCIAL


class TipoFinancimento(Enum):
    NOVO = 1                    # NOVO
    USADO = 2                   # USADO

# Bradesco
SituacaoImovel = TipoFinanciamento


class SistemaAmortizacao(Enum):
    SAC = 'S'
    PRICE = 'P'


class FormaPagamento(Enum):
    DEBITO_CONTA = 1
    BOLETO = 31


class Seguradora(Enum):
    BRADESCO_AUTO_RE_CIA_SEGUROS = 5444
    COMPANHIA_SEGUROAS_ALIANCA_BRASIL = 1547


class Interacao(Enum):
    UF = auto()
    TIPO_IMOVEL = auto()
    SITUACAO_IMOVEL = auto()
    VALOR_IMOVEL = auto()
    SOMAR_RENDA_CONJUGE = auto()
    DATA_NASC = auto()
    DATA_NASC_CONJUGE = auto()
    A_PARTIR_VALOR_FINANCIAMENTO = auto()
    VALOR_FINANCIAMENTO = auto()
    PRAZO = auto()
    FINANCIAR_DESPESAS = auto()
    # passa restante dos campos: sist. amort., 
    # forma pag., CPF, seguradora
    PARTE_FINAL = auto()
    SIMULAR = auto()


class SimuladorBradesco(SimuladorBase):
    URL1 = 'https://wspf.banco.bradesco/CRIM/Simulacao.aspx'
    REQUISICAO_AGUARDAR = 2
    REQUISICAO_TENTATIVAS = 3

    def __init__(self) -> None:
        super().__init__(banco=Banco.BRADESCO)

        self.uf = Parametros.UF_PADRAO
        #self._tipo_financiamento = TipoFinanciamento.NOVO
        self._tipo_imovel = TipoImovel.RESIDENCIAL
        self._situacao_imovel = SituacaoImovel.NOVO
        self._somar_renda_conjuge: bool = False
        self._data_nascimento_conjuge: date = None
        
        self._valor_financiamento: Decimal2 = Decimal2(0)
        self._valor_max_financiamento: Decimal2 = Decimal2(0)
        self._financiar_despesas = False

        self._sistema_amortizacao = SistemaAmortizacao.SAC
        self._forma_pagamento = FormaPagamento.DEBITO_CONTA
        self._seguradora = Seguradora.BRADESCO_AUTO_RE_CIA_SEGUROS

        # Bradesco api oculta
        self._viewstate: str = ''

        self._txt_despesas_cartorarias:str  = ''
        self._hdespesas_cartorarias: str = ''
        self._h2despesas_cartorarias: str = ''
        self._txt_despesas_itbi: str = ''
        self._hdespesas_itbi: str = ''
        self._h2despesas_itbi: str = ''

        self._existe_btn_simular = False

        self._simulacao_resultado: SimulacaoResultadoBradesco = None

    @classmethod
    def a_partir_valor_financiamento(cls, tipo_imovel: TipoImovel,
            situacao_imovel: SituacaoImovel, valor_imovel: str | Decimal2,
            somar_renda_conjuge: bool, data_nascimento: date | str,
            data_nascimento_conjuge: date | str,
            valor_financiamento: str | Decimal2, prazo: int,
            cpf: str | Cpf, financiar_despesas: bool = True,
            sistema_amortizacao: SistemaAmortizacao = SistemaAmortizacao.SAC,
            forma_pagamento: FormaPagamento = FormaPagamento.DEBITO_CONTA,
            seguradora = Seguradora.BRADESCO_AUTO_RE_CIA_SEGUROS) -> 'SimuladorBradesco':
        """Inicializa a partir do valor do financiamento. Efetua todas as interações com o Simulador Bradesco. Obtém o valor máximo financiamento.

        Args:
            tipo_imovel (TipoImovel): imóvel residencial, comercial.
            situacao_imovel (SituacaoImovel): novo, usado.
            valor_imovel (str | Decimal2): valor do imóvel.
            somar_renda_conjuge (bool): somar renda do cônjuge.
            data_nascimento (date | str): data de nascimento.
            data_nascimento_conjuge (date | str): data de nascimento cônjuge, setar somente se param. somar_renda_conjuge True.
            valor_financiamento (str | Decimal2): quando não for definido ('', None ou Decimal(0), False), será usado o valor máximo do financiamento.
            prazo (int): quando = 0 pega o prazo máximo.
            cpf (Cpf): CPF do cliente.
            financiar_despesas (bool): financiar despesas de cartório e ITBI.
            sistema_amortizacao (SistemaAmortizacao): SAC ou PRICE.
            forma_pagamento (FormaPagamento): débito em conta ou boleto.
            seguradora (Seguradora): Bradesco ou Aliança.

        Raises:
            ErroValorFinanciamento: valor financiamento inválido ou acima do máximo.
            ErroValorMaxFinanciamento: valor do financiamento não definido.
            ErroPrazo: prazo inválido ou acima do prazo máximo.

        Returns:
            Simulador: retorna um objeto simulador já com as interações feitas a partir do parâmetros passados.
        """
        sim_bradesco = cls()
        sim_bradesco.tipo_imovel = tipo_imovel
        sim_bradesco.situacao_imovel = situacao_imovel
        sim_bradesco.valor_imovel = valor_imovel
        sim_bradesco.somar_renda_conjuge = somar_renda_conjuge
        sim_bradesco.data_nascimento = data_nascimento
        
        #sim_bradesco.prazo_min = ConfigBradesco.PRAZO_MIN
        if somar_renda_conjuge:
            sim_bradesco.data_nascimento_conjuge = data_nascimento_conjuge

        # interagi com o bradesco desde o attr tipo_imovel até dt_nasc
        sim_bradesco._interagir_parte1()

        if not valor_financiamento:
            valor_financiamento = sim_bradesco.valor_max_financiamento
        try:
            sim_bradesco.valor_financiamento = valor_financiamento
        except ErroValorFinanciamento:
            raise
        except ErroValorMaxFinanciamento:
            raise 
        sim_bradesco._interagir(Interacao.VALOR_FINANCIAMENTO)

        if not prazo:
            prazo = sim_bradesco._prazo_max
        try:
            sim_bradesco.prazo = prazo
        except ErroPrazo:
            raise
        sim_bradesco._interagir(Interacao.PRAZO)

        sim_bradesco.financiar_despesas = financiar_despesas
        sim_bradesco._interagir(Interacao.FINANCIAR_DESPESAS)

        sim_bradesco.cpf = cpf
        sim_bradesco.sistema_amortizacao = sistema_amortizacao
        sim_bradesco.forma_pagamento = forma_pagamento
        sim_bradesco.seguradora = seguradora
        sim_bradesco._interagir(Interacao.PARTE_FINAL)

        #sim_bradesco._interagir(Interacao.SIMULAR)
        
        return sim_bradesco

    @property
    def tipo_imovel(self) -> TipoImovel:
        return self._tipo_imovel

    @tipo_imovel.setter
    def tipo_imovel(self, v: TipoImovel | str):
        if type(v) is not TipoImovel and type(v) is not str:
            raise ErroTipoImovel('Tipo imóvel inválido.')
        self._tipo_imovel = v

    @property
    def situacao_imovel(self) -> SituacaoImovel:
        return self._situacao_imovel
    
    @situacao_imovel.setter
    def situacao_imovel(self, v: SituacaoImovel | str):
        if type(v) is not SituacaoImovel and type(v) is not str:
            raise ErroSituacaoImovel('Situação imóvel inválida.')
        self._situacao_imovel = v

    @property
    def somar_renda_conjuge(self) -> str:
        #return self._somar_renda_conjuge
        return 'S' if self._somar_renda_conjuge else 'N'

    @somar_renda_conjuge.setter
    def somar_renda_conjuge(self, v: bool):
        if type(v) != bool:
            raise ValueError('Propriedade somar_renda_conjuge precisa ser bool.')
        
        self._somar_renda_conjuge = v
    
    @property
    def data_nascimento_conjuge(self) -> str:
        return self._data_nascimento_conjuge.strftime('%d/%m/%Y') if self._data_nascimento_conjuge else ''

    @data_nascimento_conjuge.setter
    def data_nascimento_conjuge(self, v):
        if not v:
            raise ErroDataNascimentoConjuge('É preciso digitar a data de nascimento do cônjuge.')
        
        DATA_FORMATOS = config_geral.Parametros.DATA_FORMATOS
        dt_nasc_conjuge: date = data_eh_valida(sdata=v, formatos=DATA_FORMATOS)
        if not dt_nasc_conjuge:
            raise ErroDataNascimentoConjuge(f'Data {v} inválida.')
        
        hj: date = date.today() - dt_nasc_conjuge
        if (hj.days / 365.25) < config_geral.Parametros.IDADE_MIN:
            raise ErroDataNascimentoConjuge(f'Para financiar você precisar ter pelo menos {config_geral.Parametros.IDADE_MIN} anos de idade.')
        
        self._data_nascimento_conjuge = dt_nasc_conjuge

    @property
    def valor_financiamento(self) -> str:
        return self._valor_financiamento.formatar_moeda(retirar_rs=True)

    @valor_financiamento.setter
    def valor_financiamento(self, v: str):
        if not v:
            self._valor_financiamento = Decimal2(0)
            return
        
        valor_financiamento: Decimal2
        try:
            valor_financiamento = Decimal2.a_partir_de_valor(v)
        except Exception as erro:
            raise ErroValorFinanciamento(erro)

        if not self._valor_max_financiamento:
            # é preciso iniciar do método construtor 
            # Simulador.a_partir_valor_financiamento
            raise ErroValorMaxFinanciamento(
                'Valor máximo do financiamento não definido.'
            )
        if valor_financiamento > self._valor_max_financiamento:
            raise ErroValorFinanciamento(
                f'Valor do financiamento acima do valor máximo aceito. '
                f'O valor do financiamento não pode ser acima de: '
                f'{self._valor_max_financiamento.formatar_moeda()}.'
            )
        
        self._valor_financiamento = valor_financiamento

    @property
    def valor_max_financiamento(self) -> str:
        return self._valor_max_financiamento.formatar_moeda(retirar_rs=True)
    
    def _setar_valor_max_financiamento(self, v: str):
        # setar somente de dentro da classe
        valor_max_financiamento: Decimal2
        try:
            valor_max_financiamento = Decimal2.a_partir_de_valor(v)
        except Exception as erro:
            raise ErroValorMaxFinanciamento(erro)

        self._valor_max_financiamento = valor_max_financiamento

    @property
    def financiar_despesas(self) -> bool:
        """Financiar despesas de cartório e ITBI.

        Returns:
            bool: True quando for permitido financiar despesas.
        """
        return 'S' if self._financiar_despesas else 'N'
    
    @financiar_despesas.setter
    def financiar_despesas(self, v: bool):
        if type(v) is not bool:
            raise ErroFinanciarDespesas('Atributo financiar_despesas precisar ser bool.')        
        self._financiar_despesas = v
    
    @property
    def sistema_amortizacao(self) -> SistemaAmortizacao:
        return self._sistema_amortizacao

    @sistema_amortizacao.setter
    def sistema_amortizacao(self, v: SistemaAmortizacao):
        if type(v) is not SistemaAmortizacao:
            raise ErroSistemaAmortizacaoInvalido('Sistema de amortização inválido.')
        self._sistema_amortizacao = v
    
    @property
    def forma_pagamento(self) -> FormaPagamento:
        return self._forma_pagamento

    @forma_pagamento.setter
    def forma_pagamento(self,v: FormaPagamento):
        if type(v) is not FormaPagamento:
            raise ErroFormaPagamentoInvalida('Forma de pagamento inválida.')
        self._forma_pagamento = v

    @property
    def seguradora(self) -> Seguradora:
        return self._seguradora

    @seguradora.setter
    def seguradora(self, v: Seguradora):
        if type(v) is not Seguradora:
            raise ErroSeguradoraInvalida('Seguradora inválida.')
        self._seguradora = v

    @property
    def simulacao_resultado(self) -> 'SimulacaoResultadoBradesco':
        return self._simulacao_resultado

    def _interagir_parte1(self) -> None:
        """Interações da primeira parte, passando por UF, tipo imóvel, até data de nascimento até chegar a parte que a simulação for a partir do valor do financiamento.

        Raises:
            ErroTipoImovel: Tipo imóvel inválido
            ErroSituacaoImovel: Situação imóvel inválida ou não preenchida
            ErroValorImovel: preencher com valor imóvel ou valor imóvel acima do mínimo.
            ErroDataNascimento: data de nascimento inválida ou de menor de idade (ou configurável.)
            ErroDataNascimentoConjuge: mesmo erro que data de nascimento.

        Returns:
            None: sem retorno.
        """
        if not self._tipo_imovel:
            raise ErroTipoImovel('É preciso preencher tipo do imóvel.')
        if not self.situacao_imovel:
            raise ErroSituacaoImovel('É preciso preencher situação do imóvel.')
        if not self._valor_imovel:
            raise ErroValorImovel('É preciso preencher valor imóvel.')
        if not self._data_nascimento:
            raise ErroDataNascimento('É preciso preencher data de nascimento.')
        if self._somar_renda_conjuge and not self._data_nascimento_conjuge:
            raise ErroDataNascimentoConjuge('É preciso preencher data nascimento do cônjuge.')

        if not self._viewstate:
            if not self._obter_viewstate_ini():
                # TODO: implementar log e mensage de erro
                pass

        if not self._interagir(Interacao.UF):
            pass
        if not self._interagir(Interacao.TIPO_IMOVEL):
            pass
        if not self._interagir(Interacao.SITUACAO_IMOVEL):
            pass
        if not self._interagir(Interacao.VALOR_IMOVEL):
            pass
        if not self._interagir(Interacao.SOMAR_RENDA_CONJUGE):
            pass
        if not self._interagir(Interacao.DATA_NASC):
            pass
        if self._somar_renda_conjuge:
            if not self._interagir(Interacao.DATA_NASC_CONJUGE):
                pass
        if not self._interagir(Interacao.A_PARTIR_VALOR_FINANCIAMENTO):
            pass

    def _obter_viewstate_ini(self) -> bool:
        """O simulador Bradesco passa entre as interações um parâmetro
        essêncial no payload, o __VIEWSTATE, que é gerado de acordo com
        as opções de financiemanto que são selecionadas. Quando 
        encontrado o parâmetro é retornado em self._viewstate.

        Returns:
            bool: True quando tiver obtido o __VIEWSTATE com sucesso.
        """
        self._viewstate = ''

        eh_timeout: bool
        eh_erro_conexao: bool
        for i in range(self.REQUISICAO_TENTATIVAS):
            eh_timeout = False
            eh_erro_conexao = False
            try:
                r = requests.get(self.URL1, timeout=5)
                break
            except requests.Timeout:
                # TODO: log e alerta
                eh_timeout = True
                print(f'TIMEOUT em _obter_viewstate_ini, aguardando {self.REQUISICAO_AGUARDAR}s...')
                time.sleep(self.REQUISICAO_AGUARDAR)
                print('Tentando novamente...')
            except requests.ConnectionError:
                eh_erro_conexao = True
            
        if eh_timeout or eh_erro_conexao:
            # TODO: log e alerta
            print(f'Problema em _obter_view_state_ini depois de tentar {self.TENTATIVAS}.')
            return False

        html: str = r.text
        bs = BeautifulSoup(html, 'html.parser')
        el_input_view_state = bs.find(
            'input', type='hidden', attrs={'id': '__VIEWSTATE'}
        )
        if not el_input_view_state:
            return False
        
        self._viewstate = el_input_view_state['value']
        return True

    def _interagir(self, campo: Interacao) -> bool:
        """Como a cada interação é necessário um no __VIEWSTATE então é
        preciso obter a cada novo valor passado.

        Args:
            campo (Interacao): qual a interação, o campo (UF, valor 
            imóvel?

        Returns:
            bool: True quando conseguir obter o _viewstate com sucesso
        """
        if not self._viewstate:
            # TODO: implementar log
            print('#' * 100)
            print('Não foi definido o _viewstate inicial, executar _obter_viewstate_ini.')
            return False

        extrair_valor_max_financiamento: bool = False
        extrair_prazo_max: bool = False
        extrair_parametros_finais: bool = False
        extrair_btn_simular: bool = False
        extrair_simulacao: bool = False

        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'pt-BR,pt;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://wspf.banco.bradesco',
            'referer': 'https://wspf.banco.bradesco/CRIM/Simulacao.aspx',
            'sec-ch-ua': '"Opera";v="83", "Chromium";v="97", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': 'Windows',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 OPR/83.0.4254.62',
            'x-microsoftajax': 'Delta=true',
            'x-requested-with': 'XMLHttpRequest'
        }

        payload: dict

        match campo:
            case Interacao.UF:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|ddlEstado',
                    'ToolkitScriptManager1_HiddenField': '',
                    '__EVENTTARGET': 'ddlEstado',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': 0,
                    '__SCROLLPOSITIONY': 0,
                    'ddlEstado': self.uf,
                    'HEstado': '',
                    '__ASYNCPOST': 'true'
                }
                extrair_btn_simular: bool = False
            case Interacao.TIPO_IMOVEL:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|ddlTipoImovel',
                    'ToolkitScriptManager1_HiddenField': '',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': '',
                    '__EVENTTARGET': 'ddlTipoImovel',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '0',
                    '__ASYNCPOST': 'true'
                }
            case Interacao.SITUACAO_IMOVEL:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|ddlTipoSituacaoImovel',
                    'ToolkitScriptManager1_HiddenField': '',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': '',
                    '__EVENTTARGET': 'ddlTipoSituacaoImovel',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '0',
                    '__ASYNCPOST': 'true'
                }
            case Interacao.VALOR_IMOVEL:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|btnOkVlImovel',
                    #'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:pt-BR:2f300b3f-a19f-4bcd-92a6-3cc8faf50498:475a4ef5:5546a2b:d2e10b12:effe2a26:37e2e5c9:5a682656:bfe70f69',
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    '__EVENTTARGET': '',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '0',
                    '__ASYNCPOST': 'true',
                    'btnOkVlImovel': 'Ok'
                }
            case Interacao.SOMAR_RENDA_CONJUGE:
                txt_extra: str = '0' if self._somar_renda_conjuge else '1'
                payload = {
                    'ToolkitScriptManager1': f'updPanel|rdoSomarRendaConjuge${txt_extra}',
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral;',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    'rdoSomarRendaConjuge': self.somar_renda_conjuge,
                    'HSomarRendaConjuge': '',
                    '__EVENTTARGET': f'rdoSomarRendaConjuge${txt_extra}',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '0',
                    '__ASYNCPOST': 'true'
                }
            case Interacao.DATA_NASC:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|txtDataNascimento',
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral;',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    'rdoSomarRendaConjuge': self.somar_renda_conjuge,
                    'HSomarRendaConjuge': self.somar_renda_conjuge,
                    'txtDataNascimento': self.data_nascimento,
                    'HDataNascimento': '',
                    'VCERangeValidatorData_ClientState': '',
                    'VCERequiredValidatorData_ClientState': '',
                    'VCECustomValidatorData_ClientState': '',
                    '__EVENTTARGET': 'txtDataNascimento',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '573',
                    '__ASYNCPOST': 'true',
                }
            case Interacao.DATA_NASC_CONJUGE:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|txtDataNascimentoConjuge',
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral;',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    'rdoSomarRendaConjuge': self.somar_renda_conjuge,
                    'HSomarRendaConjuge': self.somar_renda_conjuge,
                    'txtDataNascimento': self.data_nascimento,
                    'HDataNascimento': self.data_nascimento_conjuge,
                    'VCERangeValidatorData_ClientState': '',
                    'VCERequiredValidatorData_ClientState': '',
                    'VCECustomValidatorData_ClientState': '',
                    'txtDataNascimentoConjuge': self.data_nascimento_conjuge,
                    'HDataNascimentoConjuge': '',
                    'VCERangeValidatorDataConjuge_ClientState': '',
                    'VCERequiredValidatorDataConjuge_ClientState': 'INVALID',
                    'VCECustomValidatorDataConjuge_ClientState': '',
                    '__EVENTTARGET': 'txtDataNascimentoConjuge',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '334',
                    '__ASYNCPOST': 'true'
                }                
            case Interacao.A_PARTIR_VALOR_FINANCIAMENTO:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|rdoTipoSimulacao$0',
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral;',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    'rdoSomarRendaConjuge': self.somar_renda_conjuge,
                    'HSomarRendaConjuge': self.somar_renda_conjuge,
                    'txtDataNascimento': self.data_nascimento,
                    'HDataNascimento': self.data_nascimento,
                    'VCERangeValidatorData_ClientState': '',
                    'VCERequiredValidatorData_ClientState': '',
                    'VCECustomValidatorData_ClientState': '',
                    'rdoTipoSimulacao': 'F',            # TODO: colocar como attributo da classe?
                    'HTipoSimulacao': '',
                    '__EVENTTARGET': 'rdoTipoSimulacao$0',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '573',
                    '__ASYNCPOST': 'true'
                }
                extrair_valor_max_financiamento = True                
            case Interacao.VALOR_FINANCIAMENTO:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|btnOValorFinanciamento',
                    #'ToolkitScriptManager1_HiddenField': ;;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:pt-BR:2f300b3f-a19f-4bcd-92a6-3cc8faf50498:475a4ef5:5546a2b:d2e10b12:effe2a26:37e2e5c9:5a682656:bfe70f69;
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral;',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    'rdoSomarRendaConjuge': self.somar_renda_conjuge,
                    'HSomarRendaConjuge': self.somar_renda_conjuge,
                    'txtDataNascimento': self.data_nascimento,
                    'HDataNascimento': self.data_nascimento,
                    'VCERangeValidatorData_ClientState': '',
                    'VCERequiredValidatorData_ClientState': '',
                    'VCECustomValidatorData_ClientState': '',
                    'rdoTipoSimulacao': 'F',            # TODO: colocar como attributo da classe?
                    'HTipoSimulacao': 'F',
                    'txtValorFinanciamento': self.valor_financiamento,
                    'HValorFinanciamento': '',
                    'VLFinanc_ClientState': '',
                    'VLFinanc2_ClientState': '',
                    '__EVENTTARGET': '',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '0',
                    '__ASYNCPOST': 'true',
                    'btnOValorFinanciamento': 'Ok'
                }
                extrair_prazo_max = True
            case Interacao.PRAZO:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|btnOkmeses',
                    #ToolkitScriptManager1_HiddenField: ;;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:pt-BR:2f300b3f-a19f-4bcd-92a6-3cc8faf50498:de1feab2:f2c8e708:720a52bf:f9cec9bc:589eaa30:698129cf:e148b24b;
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral;',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    'rdoSomarRendaConjuge': self.somar_renda_conjuge,
                    'HSomarRendaConjuge': self.somar_renda_conjuge,
                    'txtDataNascimento': self.data_nascimento,
                    'HDataNascimento': self.data_nascimento,
                    'VCERangeValidatorData_ClientState': '',
                    'VCERequiredValidatorData_ClientState': '',
                    'VCECustomValidatorData_ClientState': '',
                    'rdoTipoSimulacao': 'F',            # TODO: colocar como attributo da classe?
                    'HTipoSimulacao': 'F',
                    'txtValorFinanciamento': self.valor_financiamento,
                    'HValorFinanciamento': self.valor_financiamento,
                    'VLFinanc_ClientState': '',
                    'VLFinanc2_ClientState': '',
                    'txtPrazo': self._prazo,
                    'HPrazo': self._prazo,
                    'VCEPrazo_ClientState': '',
                    'VCEPrazo2_ClientState': '',
                    'HFinanciarDespesas': '',
                    '__EVENTTARGET': '',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '0',
                    '__ASYNCPOST': 'true',
                    'btnOkmeses': 'Ok'
                }
            case Interacao.FINANCIAR_DESPESAS:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|rdoFinanciarDespesas$0',
                    #ToolkitScriptManager1_HiddenField: ;;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:pt-BR:2f300b3f-a19f-4bcd-92a6-3cc8faf50498:475a4ef5:5546a2b:d2e10b12:effe2a26:37e2e5c9:5a682656:bfe70f69;
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral;',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    'rdoSomarRendaConjuge': self.somar_renda_conjuge,
                    'HSomarRendaConjuge': self.somar_renda_conjuge,
                    'txtDataNascimento': self.data_nascimento,
                    'HDataNascimento': self.data_nascimento,
                    'VCERangeValidatorData_ClientState': '',
                    'VCERequiredValidatorData_ClientState': '',
                    'VCECustomValidatorData_ClientState': '',
                    'rdoTipoSimulacao': 'F',        # TODO: colocar como atributo da classe?
                    'HTipoSimulacao': 'F',
                    'txtValorFinanciamento': self.valor_financiamento,
                    'HValorFinanciamento': self.valor_financiamento,
                    'VLFinanc_ClientState': '',
                    'VLFinanc2_ClientState': '',
                    'txtPrazo': self._prazo,
                    'HPrazo': self._prazo,
                    'VCEPrazo_ClientState': '',
                    'VCEPrazo2_ClientState': '',
                    'rdoFinanciarDespesas': self.financiar_despesas,
                    'HFinanciarDespesas': '',
                    '__EVENTTARGET': 'rdoFinanciarDespesas$0',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '0',
                    '__ASYNCPOST': 'true'
                }
                extrair_parametros_finais = True
            case Interacao.PARTE_FINAL:
                payload= {
                    'ToolkitScriptManager1': 'updPanel|btnCPF',
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral;',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    'rdoSomarRendaConjuge': self.somar_renda_conjuge,
                    'HSomarRendaConjuge': self.somar_renda_conjuge,
                    'txtDataNascimento': self.data_nascimento,
                    'HDataNascimento': self.data_nascimento,
                    'VCERangeValidatorData_ClientState': '',
                    'VCERequiredValidatorData_ClientState': '',
                    'VCECustomValidatorData_ClientState': '',
                    'rdoTipoSimulacao': 'F',        # TODO: colocar como atributo da classe?
                    'HTipoSimulacao': 'F',
                    'txtValorFinanciamento': self.valor_financiamento,
                    'HValorFinanciamento': self.valor_financiamento,
                    'VLFinanc_ClientState': '',
                    'VLFinanc2_ClientState': '',
                    'txtPrazo': self._prazo,
                    'HPrazo': self._prazo,
                    'VCEPrazo_ClientState': '',
                    'VCEPrazo2_ClientState': '',
                    'rdoFinanciarDespesas': self.financiar_despesas,
                    'txtDespesasCartorarias': self._txt_despesas_cartorarias,
                    'HDespesasCartorarias': self._hdespesas_cartorarias,
                    'H2DespesasCartorarias': self._h2despesas_cartorarias,
                    'txtDespesasItbi': self._txt_despesas_itbi,
                    'HDespesasItbi': self._hdespesas_itbi,
                    'H2DespesasItbi': self._h2despesas_itbi,
                    'HFinanciarDespesas': self.financiar_despesas,
                    'RbSistemaAmortizacaoInicio': self._sistema_amortizacao.value,
                    'rblFormaPagamento': self._forma_pagamento.value,
                    'RbSeguradoraInicio': self._seguradora.value,
                    'txtCPFMain': self.cpf,
                    'vceCPF_ClientState': '',
                    '__EVENTTARGET': '',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE': self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '0',
                    '__ASYNCPOST': 'true',
                    'btnCPF': 'Ok'
                }
                extrair_btn_simular = True
            case Interacao.SIMULAR:
                payload = {
                    'ToolkitScriptManager1': 'updPanel|btnSimular',
                    'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=4.5.7.123, Culture=neutral;',
                    'ddlEstado': self.uf,
                    'HEstado': self.uf,
                    'ddlTipoImovel': self.tipo_imovel.value,
                    'HTipoImovel': self.tipo_imovel.value,
                    'ddlTipoSituacaoImovel': self.situacao_imovel.value,
                    'HTipoSituacaoImovel': self.situacao_imovel.value,
                    'txtValorImovel': self.valor_imovel,
                    'NReqE_ClientState': '',
                    'NReqE2_ClientState': '',
                    'HValorImovel': '',
                    'rdoSomarRendaConjuge': self.somar_renda_conjuge,
                    'HSomarRendaConjuge': self.somar_renda_conjuge,
                    'txtDataNascimento': self.data_nascimento,
                    'HDataNascimento': self.data_nascimento,
                    'VCERangeValidatorData_ClientState': '',
                    'VCERequiredValidatorData_ClientState': '',
                    'VCECustomValidatorData_ClientState': '',
                    'rdoTipoSimulacao': 'F',        # TODO: colocar como atributo da classe?
                    'HTipoSimulacao': 'F',
                    'txtValorFinanciamento': self.valor_financiamento,
                    'HValorFinanciamento': self.valor_financiamento,
                    'VLFinanc_ClientState': '',
                    'VLFinanc2_ClientState': '',
                    'txtPrazo': self._prazo,
                    'HPrazo': self._prazo,
                    'VCEPrazo_ClientState': '',
                    'VCEPrazo2_ClientState': '',
                    'rdoFinanciarDespesas': self.financiar_despesas,
                    'txtDespesasCartorarias': self._txt_despesas_cartorarias,
                    'HDespesasCartorarias': self._hdespesas_cartorarias,
                    'H2DespesasCartorarias': self._h2despesas_cartorarias,
                    'txtDespesasItbi': self._txt_despesas_itbi,
                    'HDespesasItbi': self._hdespesas_itbi,
                    'H2DespesasItbi': self._h2despesas_itbi,
                    'HFinanciarDespesas': self.financiar_despesas,
                    'RbSistemaAmortizacaoInicio': self._sistema_amortizacao.value,
                    'rblFormaPagamento': self._forma_pagamento.value,
                    'RbSeguradoraInicio': self._seguradora.value,
                    'txtCPFMain': self.cpf,
                    'vceCPF_ClientState': '',
                    '__EVENTTARGET': 'btnSimular',
                    '__EVENTARGUMENT': '',
                    '__LASTFOCUS': '',
                    '__VIEWSTATE':self._viewstate,
                    '__VIEWSTATEGENERATOR': '638B4BEA',
                    '__SCROLLPOSITIONX': '0',
                    '__SCROLLPOSITIONY': '0',
                    '__ASYNCPOST': 'true',
                }
                extrair_simulacao = True

        if campo in [Interacao.A_PARTIR_VALOR_FINANCIAMENTO,
                     Interacao.VALOR_FINANCIAMENTO,
                     Interacao.PRAZO,
                     Interacao.FINANCIAR_DESPESAS,
                     Interacao.PARTE_FINAL,
                     Interacao.SIMULAR]:
                if self._somar_renda_conjuge:
                    payload.update(
                        {
                            'txtDataNascimentoConjuge': self.data_nascimento_conjuge,
                            'HDataNascimentoConjuge': self.data_nascimento_conjuge,
                            'VCERangeValidatorDataConjuge_ClientState': '',
                            'VCERequiredValidatorDataConjuge_ClientState': '',
                            'VCECustomValidatorDataConjuge_ClientState': '',
                        }
                    )

        eh_timeout: bool
        eh_erro_conexao: bool
        for i in range(self.REQUISICAO_TENTATIVAS):
            eh_timeout = False
            eh_erro_conexao = False
            try:
                r = requests.post(
                    self.URL1, data=payload, headers=headers, timeout=10
                )
                break
            except requests.Timeout:
                # TODO: log e alerta
                eh_timeout = True
                print(f'TIMEOUT em _interagir, aguardando {self.REQUISICAO_AGUARDAR}s...')
                time.sleep(self.REQUISICAO_AGUARDAR)
                print('Tentando novamente...')
            except requests.ConnectionError:
                eh_erro_conexao = True
            
        if eh_timeout or eh_erro_conexao:
            # TODO: log e alerta
            print(f'Problema em _obter_view_state_ini depois de tentar {self.TENTATIVAS}.')
            return False

        html: str = r.text
        self._viewstate = self._extrair_viewstate_response(html)

        if extrair_valor_max_financiamento:
            self._extrair_valor_max_financiamento(html)
        if extrair_prazo_max:
            self._extrair_prazo_max(html)
        if extrair_parametros_finais:
            self._extrair_parametros_finais(html)
        if extrair_btn_simular:
            self._extrair_btn_simular(html)
        if extrair_simulacao:
            self._extrair_simulacao(html)

        return True
    
    def _extrair_viewstate_response(self, txt: str) -> str:
        """O parâmetro __VIEWSTATE é essencial pras interações fica no
        final de cada response, na última linha.

        Args:
            txt (str): texto contendo o html a ser extraído.

        Returns:
            str: retorna somete o campo.
        """
        PADRAO1 = '__VIEWSTATE|'
        PADRAO2 = '|'
        pos1: int = txt.rfind(PADRAO1)
        if pos1 == -1:
            return ''
        
        pos1 += len(PADRAO1)
        pos2: int = txt.find(PADRAO2, pos1)
        if pos2 == -1:
            return ''

        return txt[pos1:pos2]
    
    def _extrair_valor_max_financiamento(self, html: str) -> None:
        bs = BeautifulSoup(html, 'html.parser')
        el_span = bs.find('span', attrs={'id': 'spnValorFinanciamento'})
        if el_span:
            valor_max_financiamento: str = (
                el_span.text.split('R$ ')[1].rstrip(')')
            )
            self._setar_valor_max_financiamento(valor_max_financiamento)
        else:
            # TODO:  implementar log
            print('#' * 100)
            print('Span com o valor máx. do financiamento NÃO encontrado.')
    
    def _extrair_prazo_max(self, html: str) -> None:
        bs = BeautifulSoup(html, 'html.parser')
        el_span = bs.find('span', attrs={'id': 'spnPrazo'})
        if el_span:
            self.prazo_max  = el_span.text
        else:
            # TODO: implementar log
            print('Span com o vlaor do prazo máxi. NÃO encontrado.')
    
    def _extrair_parametros_finais(self, html: str) -> bool:
        bs = BeautifulSoup(html, 'html.parser')
        el_table_financiar_despesas = bs.find(
            'table', attrs={'id': 'vlFinanciarDespesas'}
        )
        if not el_table_financiar_despesas:
            # TODO: implementar log
            return False
        
        el_input_txt_despesas_cartorarias = el_table_financiar_despesas.find(
            'input', attrs={'id': 'txtDespesasCartorarias'}
        )
        if not el_input_txt_despesas_cartorarias: return False
        
        el_input_hdespesas_cartorarias = el_table_financiar_despesas.find(
            'input', attrs={'id': 'HDespesasCartorarias'}
        )
        if not el_input_hdespesas_cartorarias: return False
            
        el_input_h2despesas_cartorarias = el_table_financiar_despesas.find(
            'input', attrs={'id': 'H2DespesasCartorarias'}
        )
        if not el_input_h2despesas_cartorarias: return False

        el_input_txt_despesas_itbi = el_table_financiar_despesas.find(
            'input', attrs={'id': 'txtDespesasItbi'}
        )
        if not el_input_txt_despesas_itbi: return False
        
        el_input_hdespesas_itbi = el_table_financiar_despesas.find(
            'input', attrs={'id': 'HDespesasItbi'}
        )
        if not el_input_hdespesas_itbi: return False

        el_input_h2despesas_itbi = el_table_financiar_despesas.find(
            'input', attrs={'id': 'H2DespesasItbi'}
        )
        if not el_input_h2despesas_itbi: return False

        self._txt_despesas_cartorarias = el_input_txt_despesas_cartorarias['value']
        self._hdespesas_cartorarias = el_input_hdespesas_cartorarias['value']
        self._h2despesas_cartorarias = el_input_h2despesas_cartorarias['value']
        self._txt_despesas_itbi = el_input_txt_despesas_itbi['value']
        self._hdespesas_itbi = el_input_hdespesas_itbi['value']
        self._h2despesas_itbi = el_input_h2despesas_itbi['value']

        return True

    def _extrair_btn_simular(self, html:str) -> bool:
        bs = BeautifulSoup(html, 'html.parser')
        div_pnl_btn_simulate = bs.find('div', attrs={'id': 'pnlBtnSimulate'})
        # TODO: implementar log
        if not div_pnl_btn_simulate: return False

        input_btn_simular = div_pnl_btn_simulate.find('input', attrs={'name': 'btnSimular'})
        if not input_btn_simular: return False

        self._existe_btn_simular = True

        return True

    def simular(self) -> 'SimulacaoResultadoBradesco':
        if self._interagir(Interacao.SIMULAR):
            return self._simulacao_resultado

    def _extrair_simulacao(self, html: str) -> bool:
        self._simulacao_resultado = SimulacaoResultadoBradesco(html)


class SimulacaoResultadoBradesco(SimulacaoResultadoBase):
    def __init__(self, html: str):
        super().__init__()

        self._modalidade: str = ''
        self._forma_pagamento: str = ''
        self._taxa_juros: str = ''
        self._renda_liquida_minima: Decimal2 = Decimal2(0)
        self._valor_devido_ato_contratacao: str | Decimal2 = ''
        self._valor_a_ser_liberado: str | Decimal2 = ''
    
        self._extrair_dados(html)

    @property
    def modalidade(self) -> str:
        return self._modalidade

    @property
    def forma_pagamento(self) -> str:
        return self._forma_pagamento

    @property
    def taxa_juros(self) -> str:
        return self._taxa_juros

    @property
    def renda_liquida_minima(self) -> str:
        return self._renda_liquida_minima.formatar_moeda()
    
    @renda_liquida_minima.setter
    def renda_liquida_minima(self, v: str | Decimal2 | float):
        if type(v) is str:
            self._renda_liquida_minima = Decimal2.from_cur_str(v)
        elif type(v) is Decimal2 or type(v) is float:
            self._renda_liquida_minima = Decimal2(v)
        else:
            self._renda_liquida_minima = Decimal2(0)
    
    @property
    def valor_devido_ato_contratacao(self) -> str:
        return self._valor_devido_ato_contratacao

    @property
    def valor_a_ser_liberado(self) -> str:
        return self._valor_a_ser_liberado

    def _extrair_dados(self, html) -> bool:
        bs = BeautifulSoup(html, 'html.parser')
        div_resultado_simulacao = bs.find(
            'div', attrs={'id': 'pnlResultadoSimulacao'}
        )
        if not div_resultado_simulacao:
            # TODO: implementar log
            raise ErroResultadoCampoNaoRetornado(
                'Não Encontrou a tabela com o resultado da simulação.'
            )

        span_modalidade = div_resultado_simulacao.find(
            'span', attrs={'id': 'lblModalidade'}
        )
        tds_modalidade = span_modalidade.find_all('td')

        tab_resultado = div_resultado_simulacao.find(
            'table', attrs={'id': 'tablePnlImpressaoResultado'}
        )
        span_valor_imovel = tab_resultado.find(
            'span', attrs={'id': 'lblValorImovel'}
        )
        span_valor_financiamento = tab_resultado.find(
            'span', attrs={'id': 'lblValorFinanciamento_Adquirir'}
        )
        span_prazo = tab_resultado.find(
            'span', attrs={'id': 'lblPrazo_Adquirir'}
        )
        span_sistema_amortizacao = tab_resultado.find(
            'span', attrs={'id': 'lblSistemaAmortizacao_Adquirir'}
        )
        span_forma_pagamento = tab_resultado.find(
            'span', attrs={'id': 'lblResultadoFormaPagamento'}
        )
        span_taxa_juros = tab_resultado.find(
            'span', attrs={'id': 'lblTaxaJurosEfetivaAno_Adquirir'}
        )
        span_valor_prestacao = tab_resultado.find(
            'span', attrs={'id': 'lblValorPrestacaoMensal_Adquirir'}
        )
        span_renda_liquida_minima = tab_resultado.find(
            'span', attrs={'id': 'lblRendaLiquidaMinima_Adquirir'}
        )
        span_valor_devido_ato_contratacao = tab_resultado.find(
            'span', attrs={'id': 'lblVLValorDevido_Adquirir'}
        )
        span_valor_a_ser_liberado = tab_resultado.find(
            'span', attrs={'id': 'lblVLValorLiberado_Adquirir'}
        )

        self.titulo = 'Resultado da Simulação Bradesco'
        self._modalidade = tds_modalidade[0].text + tds_modalidade[1].text
        self.valor_imovel = span_valor_imovel.text
        self.valor_financiamento = span_valor_financiamento.text
        self.prazo = span_prazo.text
        self.sistema_amortizacao = span_sistema_amortizacao.text
        self._forma_pagamento = span_forma_pagamento.text
        self._taxa_juros = span_taxa_juros.text
        self.valor_prestacao = span_valor_prestacao.text
        self.renda_liquida_minima = span_renda_liquida_minima.text
        self._valor_devido_ato_contratacao = span_valor_devido_ato_contratacao.text
        self._valor_a_ser_liberado = span_valor_a_ser_liberado.text
    
    def __str__(self):
        TAM_TRACEJADO = Parametros.TAM_TRACEJADO
        return (
            f'*{self.titulo}*\n'
            f'{"-" * TAM_TRACEJADO}\n'
            #f'{self.modalidade}\n'
            f'*Valor do imóvel:* {self.valor_imovel}\n'
            f'*Valor do financiamento:* {self.valor_financiamento}\n'
            f'*Prazo:* {self.prazo}\n'
            f'*Sistema de Amortização:* {self.sistema_amortizacao}\n'
            f'*Forma de Pagamento:* {self.forma_pagamento}\n'
            f'*Taxa de Juros Efetiva ao Ano:* {self.taxa_juros}\n'
            f'*Valor da prestação mensal:* {self.valor_prestacao}\n'
            f'*Renda líquida mínima:* {self.renda_liquida_minima}\n'
            f'*Valor devido no ato da contratação:* {self.valor_devido_ato_contratacao}\n'
            f'*Valor a ser liberado:* {self.valor_a_ser_liberado}\n'
        )


def test1():
    sim_brad = SimuladorBradesco()
    print(f'{sim_brad._obter_viewstate_ini()=}')
    print(f'{sim_brad._viewstate=}\n')
    
    sim_brad.uf = 'GO'
    print(f"{sim_brad._interagir(Interacao.UF)=}")
    print(f'{sim_brad._viewstate=}\n')

    sim_brad.tipo_imovel = TipoImovel.RESIDENCIAL
    print(f"{sim_brad._interagir(Interacao.TIPO_IMOVEL)=}")
    print(f'{sim_brad._viewstate=}\n')

    sim_brad.situacao_imovel = SituacaoImovel.NOVO
    print(f"{sim_brad._interagir(Interacao.SITUACAO_IMOVEL)=}")
    print(f'{sim_brad._viewstate=}\n')

    sim_brad.valor_imovel = '228.000'
    print(f"{sim_brad._interagir(Interacao.VALOR_IMOVEL)=}")
    print(f'{sim_brad._viewstate=}\n')

    sim_brad.somar_renda_conjuge = False
    print(f"{sim_brad._interagir(Interacao.SOMAR_RENDA_CONJUGE)=}")
    print(f'{sim_brad._viewstate=}\n')

    sim_brad.data_nascimento = '08/02/1998'
    print(f"{sim_brad._interagir(Interacao.DATA_NASC)=}")
    print(f'{sim_brad._viewstate=}\n')

    print(f'{sim_brad._interagir(Interacao.A_PARTIR_VALOR_FINANCIAMENTO)=}')
    print(f'{sim_brad._viewstate=}\n')
    print(f'{sim_brad._valor_max_financiamento.formatar_moeda()=}')


def test2():
    print('#' * 100)
    print('>> Simulação Bradesco a partir do valor do financiamento...')
    print()
    try:
        sim_brad = SimuladorBradesco.a_partir_valor_financiamento(
            tipo_imovel=TipoImovel.RESIDENCIAL,
            situacao_imovel=SituacaoImovel.NOVO,    # = tipo_financiamento
            valor_imovel=140000.44,
            somar_renda_conjuge=True,
            data_nascimento='25/10/1992',
            data_nascimento_conjuge='10/08/1995',
            valor_financiamento='',
            prazo=350,
            cpf='857.121.060-86'
        )
    except ErroPrazo as erro:
        print(f'Erro ao definir prazo. {erro}')
        return False
    except Exception as erro:
        print(erro)
        return False

    sim_brad_resultado: SimulacaoResultadoBradesco = sim_brad.simular()
    print(sim_brad_resultado)


def test3():
    sim_brad = SimuladorBradesco()
    sim_brad.cpf = '000 802 871 07'
    print(f'{sim_brad._cpf.sem_formatacao=}')
    print(f'{sim_brad.cpf=}')

if __name__ == '__main__':
    import locale
    locale.setlocale(locale.LC_MONETARY, 'pt_BR.utf8')
    
    test2()
    #test3()
