#!/usr/bin/env python
# coding: utf-8
"""Simulador de Crédito Imobiliário
"""
__version__ = '0.51'
__author__ = 'Vanduir Santana Medeiros'

import bs4
from exc import *
from util import remover_acentos, ajustar_esc_char, ajustar_unicode_esc_char
from util import data_eh_valida, Cpf, Fone, FoneFormato, Decimal2
from bs4 import BeautifulSoup
from datetime import datetime, date
from enum import Enum
import config.geral
import config.layout
import urllib.request
import urllib.parse
import urllib.error
import ngram
import gzip


UFS = ('AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'ES', 'GO', 'MA', 'MT',
       'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS',
       'RO', 'RR', 'SC', 'SP', 'SE', 'TO', 'DF')


class TipoFinanciamento(Enum):
    NOVO = 1
    USADO = 4
    AQUISICAO_TERRENO = 6
    CONSTRUCAO = 2
    #EMPRESTIMO_GARANTIDO_POR_IMOVEL = 5
    #IMOVEIS_CAIXA = 6
    #REFORMA_AMPLIACAO = 7

    @property
    def name(self):
        if self.value == 6:
            return 'Aquisição de Terreno'
        elif self.value == 2:
            return 'Construção'
        else:
            return self._name_.capitalize()


class OpcaoFinanciamento(Enum):
    # Tipo Financiamento Novo
    PROGRAMA_CASA_VERDE_AMARELA_FAIXA_1_5 = 100501108
    PROGRAMA_CASA_VERDE_AMARELA = 100501103
    SBPE_TR_IPCA_OU_TX_FIXA = 100501102
    SBPE_CRED_IMOB_POUP_CAIXA = 100501123
    SBPE_TR_IPCA_OU_TX_FIXA_IMOVEL_VINCULADO = 100501122
    SBPE_CREDITO_IMOBILIARIO_POUPANÇA_CAIXA = 100501120
    SBPE_TR_IPCA_OU_TX_FIXA_DEBITO_CONTA_CAIXA = 100301129
    SBPE_CRED_IMOB_POUP_CAIXA_IMOVEL_VINC_EMPREEND_FINANC_CAIXA_DEBITO_CONTA_CAIXA = 100301132
    SBPE_TR_IPCA_OU_TX_FIXA_IMoVEL_VINC_EMPREEND_FINANCIADO_CAIXA_DEBITO_CONTA_CAIXA = 100301131
    SBPE_CREDITO_IMOBILIARIO_POUPANCA_CAIXA_DEBITO_CONTA_CAIXA = 100301130
    # Tipo Financiamento Usado
    SBPE_CREDITO_IMOBILIARIO_POUPANCA_CAIXA_DEBITO_CONTA_CAIXA_IMOVEL_USADO = 105801121
    SBPE_TR_IPCA_OU_TX_FIXA_DEBITO_CONTA_CAIXA_IMOVEL_USADO = 105801120
    PROGRAMA_CASA_VERDE_AMARELA_IMOVEL_USADO = 106001102
    # Tipo Financiamento Terreno
    SBPE_RELACIONAMENTO_CAIXA_TERRENO = 103401100
    # Tipo Financiamento Construção
    SBPE_TR_OU_TX_FIXA_DEBITO_CONTA_CAIXA_CONSTRUCAO = 107501106
    SBPE_CREDITO_IMOBILIARIO_POUPANÇA_CAIXA_DEBITO_CONTA_CAIXA_CONSTRUCAO = 107501107
    PROGRAMA_CASA_VERDE_AMARELA_CONSTRUCAO_TERRENO_PROPRIO = 107701100
    PROGRAMA_CASA_VERDE_AMARELA_COMPRA_TERRENO_E_CONSTRUÇÃO = 107701105

    @property
    def versao(self):
        return getattr(self, '_versao', '')
    
    @versao.setter
    def versao(self, v: str):
        self._versao = v    

    @property
    def descricao(self):
        return getattr(self, '_descricao', '')

    @descricao.setter
    def descricao(self, v: str):
        self._descricao = v


class MsgsCaixa(Enum):
    RENDA_INSUFICIENTE = 'ATENÇÃO! RENDA INSUFICIENTE PARA REALIZAR A OPERAÇÃO.'
    RENDA_INSUFICIENTE_FINAL = 'RENDA INSUFICIENTE PARA REALIZAR A OPERAÇÃO.'       # 2 espaços no item acima
    VALOR_FINANCIAMENTO_INFERIOR = 'ATENÇÃO!  VALOR DE FINANCIAMENTO CALCULADO É INFERIOR AOS LIMITES DO PROGRAMA.'


class Banco(Enum):
    CAIXA = 0
    BB = 1
    SANTANDER = 2
    BRADESCO = 3


I_TXT = config.layout.CaixaResultado.I_TXT
I_INDICE = config.layout.CaixaResultado.I_INDICE
I_TXT_AUX = config.layout.CaixaResultado.I_TXT_AUX


class SimuladorResultadoItem():
    """Representa cada linha da tabela de uma tabela 2x2 com o resultado da simulação"""

    def __init__(self, t: tuple[int, str, str]):
        self.indice = t[I_INDICE]
        self.descricao = t[I_TXT]
        self.descricao_aux = t[I_TXT_AUX] if len(t) == 3 else ''
        self.valor = ''

    def set_valor(self, v: str, apenas_valor=False) -> None:
        """Seta o valor de um campo, retirando o texto desnecessário.

        Args:
            v (str): valor a ser setado.
            apenas_valor (bool, optional): retira texto desnecessário a direita. Defaults to False.
        """
        if not apenas_valor:
            self.valor = v
        else:
            self.valor = v[ :v.find('\r')] if '\r' in v else v    

    def ajustar_descricao(self, escape=True) -> None:
        if escape:
            self.descricao = ajustar_unicode_esc_char(self.descricao)
        elif self.descricao_aux:
            self.descricao = self.descricao_aux
    
    @classmethod
    def from_none(cls):
        return cls(t=(-22, '', ''))
            

class SimulacaoResultado():
    """Organiza os dados html retornados da simulação do serviço da caixa.
    """
    def __init__(self, html: str, opcao_financiamento: OpcaoFinanciamento):
        self.bs = BeautifulSoup(html, 'html.parser')
        self.opcao_financiamento = opcao_financiamento
        self.titulo = ''
        self._cods_sistema_amortizacao: dict[str, str] = {}
        self._sistema_amortizacao_chave_sel: str = ''
        self._prestacao_max: str = ''

    @property
    def opcao_financiamento(self) -> OpcaoFinanciamento:
        return getattr(self, '_opcao_financiamento', OpcaoFinanciamento.SBPE_CRED_IMOB_POUP_CAIXA)

    @opcao_financiamento.setter
    def opcao_financiamento(self, v: OpcaoFinanciamento):
        if type(v) is not OpcaoFinanciamento:
            raise ErroOpcaoFinanciamento(v)
        
        self._opcao_financiamento = v
        self._setar_layout()

    @property
    def cods_sistema_amortizacao(self) -> dict[str, str]:
        """Obtem todos os códigos de sistema de amortização disponíveis
        para esse financiamento.

        Returns:
            dict[str, str]: dicionário contendo o texto e o código da
                taxa de amortização/indexador.
        """
        return self._cods_sistema_amortizacao

    @property
    def sistema_amortizacao_chave_sel(self) -> str:
        """Obtem chave do código de amortização selecionado.

        Returns:
            str: str contendo o texto da chave selecionada da taxa de
                amortização.
        """
        return self._sistema_amortizacao_chave_sel

    @sistema_amortizacao_chave_sel.setter
    def sistema_amortizacao_chave_sel(self, v: str):
        """Define a chave do sistema de amortização selecionada.

        Args:
            v (str): key do dicionário cods_sistema_amortizacao.
        """
        if v in self._cods_sistema_amortizacao:
            self._sistema_amortizacao_chave_sel = v
        else:
            print()
            print('Key Sistema Amortização inválida.')

    @property
    def prestacao_max(self) -> str:
        return self._prestacao_max

    def _setar_prestacao_max(self) -> None:
        div_res = self.bs.find('input', attrs={'name': 'prestacaoMaxDesejada'})
        if not div_res:
            return
        self._prestacao_max = div_res['value']

    def _setar_cods_sistema_amortizacao(self, el_select: bs4.element.Tag):
        """Seta dicionário com as taxas de amortização, a key é o texto,
        value é o código da taxa.

        Args:
            el_select (bs4.element.Tag): elemento select de onde será 
            extraído os valores.

        Returns:
            None: sem retorno.
        """
        if not el_select:
            # TODO: implementar log e alerta ao desenvolvedor
            print('#' * 50)
            print('Elemento select com taxas de amortização NÃO encontrado.')
            print('#' * 50)
            return {}

        el_option: bs4.element.Tag
        el_option_selected: bs4.element.Tag = el_select.find(
            'option', {'selected': 'selected'}
        )
        el_options: bs4.element.ResultSet = el_select.findChildren('option')
        for el_option in el_options:
            self._cods_sistema_amortizacao[el_option.text] = el_option['value']
            if el_option == el_option_selected:
                self._sistema_amortizacao_chave_sel = el_option.text

    def _setar_layout(self):
        layout: config.layout.CaixaResultado = config.layout.CaixaResultado()
        OF = OpcaoFinanciamento
        match self.opcao_financiamento:
            case (OF.PROGRAMA_CASA_VERDE_AMARELA 
                | OF.PROGRAMA_CASA_VERDE_AMARELA_COMPRA_TERRENO_E_CONSTRUÇÃO
                | OF.PROGRAMA_CASA_VERDE_AMARELA_CONSTRUCAO_TERRENO_PROPRIO):
                layout = config.layout.CaixaResultado2()
            case OpcaoFinanciamento.PROGRAMA_CASA_VERDE_AMARELA_FAIXA_1_5:
                layout = config.layout.CaixaResultado3()

        self.valor_imovel = SimuladorResultadoItem(layout.T_VALOR_IMOVEL)
        self.prazo_maximo  = SimuladorResultadoItem(layout.T_PRAZO_MAXIMO)
        self.prazo_escolhido  = SimuladorResultadoItem(layout.T_PRAZO_ESCOLHIDO)
        self.cota_maxima  = SimuladorResultadoItem(layout.T_COTA_MAXIMA)
        self.valor_entrada  = SimuladorResultadoItem(layout.T_VALOR_ENTRADA)

        match type(layout):
            case config.layout.CaixaResultado2:
                self.valor_subsidio = SimuladorResultadoItem(layout.T_SUBSIDIO_CASA_VERDE_AMARELA)
            case config.layout.CaixaResultado3:
                self.valor_subsidio = SimuladorResultadoItem(layout.T_SUBSIDIO_CASA_VERDE_AMARELA_FAIXA__INI)
            case _:
                self.valor_subsidio = SimuladorResultadoItem.from_none()

        self.valor_financiamento = SimuladorResultadoItem(layout.T_VALOR_FINANCIAMENTO)
        self.sistema_amortizacao_indexador = SimuladorResultadoItem(layout.T_SISTEMA_AMORTIZACAO_INDEXADOR__INI)
        self.primeira_prestacao = SimuladorResultadoItem(layout.T_PRIMEIRA_PRESTACAO)
        self.ultima_prestacao = SimuladorResultadoItem(layout.T_ULTIMA_PRESTACAO)
        self.msg_erro: str  = ''

    def __str__(self):
        tam = 40
        s = ''
        s += f'{"#" * len(self.titulo)}\n'
        s += f'{self.titulo}\n'
        s += f'{"#" * len(self.titulo)}\n'
        s += f'{self.valor_imovel.descricao:>{tam}}: {self.valor_imovel.valor}\n'
        s += f'{self.prazo_maximo.descricao:>{tam}}: {self.prazo_maximo.valor}\n'
        s += f'{self.prazo_escolhido.descricao:>{tam}}: {self.prazo_escolhido.valor}\n'
        s += f'{self.cota_maxima.descricao:>{tam}}: {self.cota_maxima.valor}\n'
        s += f'{self.valor_entrada.descricao:>{tam}}: {self.valor_entrada.valor}\n'
        if self.valor_subsidio.valor:
            s += f'{self.valor_subsidio.descricao:>{tam}}: {self.valor_subsidio.valor}\n'
        s += f'{self.valor_financiamento.descricao:>{tam}}: {self.valor_financiamento.valor}\n'
        s += f'{self.sistema_amortizacao_indexador.descricao:>{tam}}: {self.sistema_amortizacao_indexador.valor}\n'
        s += '\n'
        s += f'{self.primeira_prestacao.descricao:>{tam}}: {self.primeira_prestacao.valor}\n'
        s += f'{self.ultima_prestacao.descricao:>{tam}}: {self.ultima_prestacao.valor}'
        return s

    def extrair_dados(self) -> bool:
        """Extrai dados, valor do imóvel, prazos, cota, valor de entrada, subsídio, etc. 
        Seta essas informações como atributos. Obtém dados da primeira e segunda tabelas,
        na primeira existem os dados do financiamento.

        Returns:
            bool: retorna True quando a extração foi um sucesso.
        """
        self.msg_erro = ''

        self._setar_prestacao_max()

        titulo = self.bs.find('h3', attrs={'class': 'simulation-result-title zeta'})
        if titulo:
            self.titulo = ajustar_unicode_esc_char(titulo.text.strip())

        tables = self.bs.find_all('table', attrs={'class': 'simple-table'})
        num_tables = len(tables)
        if num_tables < 2:
            print('Não encontrou nenhuma tabela no resulado da simulação!')
            div_erro = self.bs.find('div', attrs={'class': 'erro_feedback'})
            if div_erro:
                self.msg_erro = ajustar_unicode_esc_char(div_erro.text.strip())
                if self.msg_erro.endswith(MsgsCaixa.RENDA_INSUFICIENTE_FINAL.value):
                    raise ErroRendaFamiliarInsuficente(self.msg_erro)
                elif self.msg_erro == MsgsCaixa.VALOR_FINANCIAMENTO_INFERIOR.value:
                    raise ErroValorFinanciamentoInferior(self.msg_erro)
            return False

        tds = tables[0].find_all('td')
        if not tds:
            print('Não encontrou células com o resultado da simulação!')
            return False

        get_desc = lambda : tds[i].text.strip()
        get_valor = lambda : tds[i + 1].text.strip()
                
        for i in range(0, len(tds)):
            txt = get_desc()
            match i:
                case self.valor_imovel.indice:
                    if txt == self.valor_imovel.descricao:
                        self.valor_imovel.set_valor(get_valor())
                        self.valor_imovel.ajustar_descricao()
                    else:
                        # TODO: implementar log e alerta (quire?) quando não achar o texto correto na célula
                        pass
                case self.prazo_maximo.indice:
                    if txt == self.prazo_maximo.descricao:
                        self.prazo_maximo.set_valor(get_valor())
                    else:
                        pass
                case self.prazo_escolhido.indice:
                    if txt == self.prazo_escolhido.descricao:
                        self.prazo_escolhido.set_valor(get_valor(), apenas_valor=True)
                    else:
                        pass
                case self.cota_maxima.indice:
                    if txt == self.cota_maxima.descricao:
                        self.cota_maxima.set_valor(get_valor())
                        self.cota_maxima.ajustar_descricao(escape=True)
                    else:
                        pass
                case self.valor_entrada.indice:
                    if txt == self.valor_entrada.descricao:
                        self.valor_entrada.set_valor(get_valor(), apenas_valor=True)
                    else:
                        pass
                case self.valor_subsidio.indice:
                    if txt == self.valor_subsidio.descricao or txt.startswith(self.valor_subsidio.descricao):
                        self.valor_subsidio.set_valor(get_valor(), apenas_valor=True)
                        self.valor_subsidio.ajustar_descricao()
                    else:
                        print('Não encontrado o valor do subsídio!')
                case self.valor_financiamento.indice:
                    if txt == self.valor_financiamento.descricao:
                        self.valor_financiamento.set_valor(get_valor())
                    else:
                        pass
                case self.sistema_amortizacao_indexador.indice:
                    if txt.startswith(self.sistema_amortizacao_indexador.descricao):
                        self.sistema_amortizacao_indexador.set_valor(get_valor(), apenas_valor=True)
                        self.sistema_amortizacao_indexador.ajustar_descricao(escape=False)
                    else:
                        pass
                case _:
                    pass
        
        LINHA_ULT_PREST = self.ultima_prestacao.indice 
        trs = tables[2].find_all('tr')
        if not trs:
            print('Não encontrou nenhuma linha das prestações.')
            return False

        if len(trs) < LINHA_ULT_PREST:
            print('Não encontrou linhas das prestações.')
            return False
        
        def get_valor(c):
            valores = [s for s in c.text.replace('\r', '').replace('\t', '').split('\n') if s]
            if len(valores) >= 2:
                return ' '.join(valores[0:2])
            return ''

        ind_prim_prest = self.primeira_prestacao.indice
        tds = trs[ind_prim_prest].findChildren('td')
        if not tds:
            print('Não encontrou células da primeira prestação.')
            return False

        if tds[0].text.strip() == self.primeira_prestacao.descricao:
            center = tds[1].find("center")
            if not center:
                print('Não encontrou center onde tá o valor da prestação.')
                return False

            valor = get_valor(center)
            # TODO: NÃO É MAIS NECESSÁRIO (ver abaixo): disparar alerta
            # quando retornar "." e mais de duas casas decimais
            pos_ponto, pos_virg = valor.rfind('.'), valor.rfind(',')
            if pos_virg < pos_ponto:
                if pos_ponto < len(valor) - 3:
                    raise ErroValorPrimeiraPrestacao(valor)
                else:
                    # CORRIGIDO: retornava certamente por conta das 
                    # headers q não tavam definidas
                    valor = Decimal2.from_cur_str(valor).formatar_moeda()
            self.primeira_prestacao.set_valor(valor)
        
        ind_ult_prest = self.ultima_prestacao.indice
        tds = trs[ind_ult_prest].findChildren('td')
        if not tds:
            print('Não encontrou células da última prestação.')
            return False
        
        if tds[0].text.strip() == self.ultima_prestacao.descricao:
            center = tds[1].find('center')
            if not center:
                print('Não encontrou center onde tá o valor da última prestação.')
                return False

            valor = get_valor(center)    
            self.ultima_prestacao.set_valor(valor)
        
        el_select = el_select = self.bs.find(
            'select', attrs={'id': 'codSistemaAmortizacaoAlterado'}
        )
        self._setar_cods_sistema_amortizacao(el_select)

        return True


class Simulador():
    """Comunica com os simuladores dos bancos para executar suas APIs de simulação
    de Crédito Imobiliário retornando dados sobre o resultado da simulação.
    """

    URL1 = 'http://www8.caixa.gov.br/siopiinternet-web/dwr/call/plaincall/SIOPIAjaxFrontController.callActionForwardMethodLista.dwr'
    URL2 = 'http://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=validarMunicipioFeirao&cidade={cod_cidade}&requisicaoModal=true'
    URL3 = 'http://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=enquadrarProdutos'
    URL4 = 'http://www8.caixa.gov.br/siopiinternet-web/dwr/call/plaincall/SIOPIAjaxFrontController.callActionForwardMethodDiv.dwr'

    ACHAR1 ='s0.codigo='
    ACHAR2='dwr.engine.'
    CODIGO=0
    NOME=13
    NOME_SEM_ASPA=15
    total_cidades = 0

    ACHAR_INI_HTML_SIM = 'preencheDiv("resultadoSimulacao","'
    ACHAR_FIM_HTML_SIM = r'//#DWR-REPLY'

    def __init__(self) -> None:
        self._tipo_financiamento = TipoFinanciamento.NOVO
        self._valor_imovel: Decimal2 = Decimal2('0')
        self._uf: str = 'GO'
        self._cpf: str = Cpf(cpf='')
        self._celular: str = ''
        self._renda_familiar: Decimal2 = Decimal2(0)
        self._data_nascimento: date = ''
        self._possui_relacionamento_caixa = False
        self._tres_anos_fgts: bool = False
        self._mais_de_um_comprador_dependente: bool = False
        self._opcao_financiamento = OpcaoFinanciamento.PROGRAMA_CASA_VERDE_AMARELA
        self._prazo: int = 0
        self._prazo_max: int = 0
        self._valor_entrada: Decimal2 = Decimal2('0')
        self._cod_sistema_amortizacao = 'undefined'
        self._prestacao_max: Decimal2 = Decimal2('0')

        self._cidades: list[dict] = []
        self.cidades_filtro: list[str] = []
        self.cidade_indice: int = -1
    
    @property
    def tipo_financiamento(self) -> TipoFinanciamento:
        return self._tipo_financiamento

    @tipo_financiamento.setter
    def tipo_financiamento(self, v: TipoFinanciamento):
        if type(v) is not TipoFinanciamento:
            raise ErroTipoFinanciamento(f'Tipo Imóvel precisa ser {TipoFinanciamento}')
        
        self._tipo_financiamento = v

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
            valor_imovel = Decimal2.from_cur_str(v)
        except Exception as erro:
            raise ErroValorImovel(erro)

        VALOR_IMOVEL_MIN = Decimal2(config.geral.Parametros.VALOR_IMOVEL_MIN)
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
            #fone = Fone(valor=v)
            fone = Fone.a_partir_de_fmt_caixa(valor=v)
        except ValueError as erro:
            self._celular = ''
            raise ErroCelular(f'{erro}')
        
        #fone.formato = FoneFormato.CAIXA_SIMULADOR
        self._celular = fone.formatar()

    @property
    def renda_familiar(self) -> str:
        return self._renda_familiar.formatar_moeda(retirar_rs=True)
    
    @renda_familiar.setter
    def renda_familiar(self, v) -> None:
        if not v:
            self._renda_familiar = ''
            return
        
        d2: Decimal2
        try:
            d2 = Decimal2.from_cur_str(v)
        except Exception as erro:
            raise ErroRendaFamiliar(erro)

        RENDA_FAMILIAR_MIN = Decimal2(config.geral.Parametros.RENDA_FAMLIAR_MIN)
        if d2 < RENDA_FAMILIAR_MIN:
            raise ErroRendaFamiliar(f'O valor da renda familiar bruta de {d2.formatar_moeda()} é baixo, precisa ser de no mínimo: {RENDA_FAMILIAR_MIN.formatar_moeda()}.')

        self._renda_familiar = d2
    
    @property
    def data_nascimento(self) -> str:
        return self._data_nascimento.strftime('%d/%m/%Y') if self._data_nascimento else ''

    @data_nascimento.setter
    def data_nascimento(self, v):
        if not v:
            raise ErroDataNascimento('É preciso digitar a data de nascimento')
        
        DATA_FORMATOS = config.geral.Parametros.DATA_FORMATOS
        dt_nasc: date = data_eh_valida(sdata=v, formatos=DATA_FORMATOS)
        if not dt_nasc:
            raise ErroDataNascimento(f'Data {v} inválida.')
        
        hj: date = date.today() - dt_nasc
        if (hj.days / 365.25) < config.geral.Parametros.IDADE_MIN:
            raise ErroDataNascimento(f'Para financiar você precisar ter pelo menos {config.geral.Parametros.IDADE_MIN} anos de idade.')
        
        self._data_nascimento = dt_nasc

    @property
    def possui_relacionamento_caixa(self) -> bool:
        return self._possui_relacionamento_caixa

    @possui_relacionamento_caixa.setter
    def possui_relacionamento_caixa(self, v: bool):
        if type(v) is not bool:
            raise ValueError('Propriedade possui_relacionamento_caixa precisa ser bool.')

        self._possui_relacionamento_caixa = v

    @property
    def tres_anos_fgts(self) -> bool:
        return self._tres_anos_fgts

    @tres_anos_fgts.setter
    def tres_anos_fgts(self, v):
        if type(v) != bool:
            raise ValueError('Propriedade tres_anos_fgts presica ser bool.')
        
        self._tres_anos_fgts = v

    @property
    def mais_de_um_comprador_dependente(self) -> bool:
        return self._mais_de_um_comprador_dependente

    @mais_de_um_comprador_dependente.setter
    def mais_de_um_comprador_dependente(self, v):
        if type(v) != bool:
            raise ValueError('Propriedade mais_de_um_comprador_dependente precisa ser bool.')
        
        self._mais_de_um_comprador_dependente = v

    @property
    def opcao_financiamento(self) -> OpcaoFinanciamento:
        return self._opcao_financiamento

    @opcao_financiamento.setter
    def opcao_financiamento(self, v):
        if type(v) is not OpcaoFinanciamento:
            raise ErroOpcaoFinanciamento(v)
        self._opcao_financiamento = v
    
    @property
    def prazo(self) -> str:
        return f'{self._prazo} meses'
    
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
        return self._prazo_max
    
    @prazo_max.setter
    def prazo_max(self, v):
        """Defini prazo máximo em meses.

        Args:
             v (str or int): o prazo pode ser tanto em string no padrão 
                da caixa (prazo meses) quanto um int.
        """
        self._prazo_max = self._validar_prazo(v)

    def _validar_prazo(self, v) -> int:
        """Validar prazo."""
        if type(v) is str:
            if ' ' in v:
                prazo: str
                prazo = v.split(' ')[0]
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
    def valor_entrada(self) -> str:
        return self._valor_entrada.formatar_moeda(retirar_rs=True)

    @valor_entrada.setter
    def valor_entrada(self, v) -> None:
        if not v:
            self._valor_entrada = ''
            return

        d2: Decimal2
        try:
            d2 = Decimal2.from_cur_str(v)
        except Exception as erro:
            raise ErroValorEntrada('Valor de entrada inválido.')
        
        self._valor_entrada = d2

    @property
    def cod_sistema_amortizacao(self) -> str:
        return self._cod_sistema_amortizacao

    @cod_sistema_amortizacao.setter
    def cod_sistema_amortizacao(self, v: str):
        self._cod_sistema_amortizacao = v

    @property
    def prestacao_max(self) -> str:
        return self._prestacao_max.formatar_moeda(retirar_rs=True)

    @prestacao_max.setter
    def prestacao_max(self, v) -> None:
        if not v:
            self._prestacao_max = ''
        d2: Decimal2

        try:
            d2 = Decimal2.from_cur_str(v)
        except Exception as erro:
            raise ErroPrestacaoMax('Valor da prestação inválido.')
        self._prestacao_max = d2

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
    def obter_lista_dic_cidades(self):
        """Obter_lista_dic_cidades (bool): utilizado apenas quando é 
        necessário extrair as cidades pra inserção em massa através do SQLAlchemy.
        """
        return self._obter_lista_dic_cidades
    
    @obter_lista_dic_cidades.setter
    def obter_lista_dic_cidades(self, v):
        self._obter_lista_dic_cidades = v


    def obter_cidades(self, uf: str = '') -> list[dict]:
        """Obtém cidades com seus respectivos códigos no modo raw.

        Args:
            uf (str): sigla do estado.

        Returns:
            list[dict]: retorna um dicionário contendo a chave como uma 
            string sem aspas com o nome cidade; o valor é uma tupla com o 
            código da cidade e o nome dela com aspas.
        """
        if uf:
            self.uf = uf
        else:
            uf = self.uf

        params =  {
            'callCount': 1,
            'page': '/siopiinternet-web/simulaOperacaoInternet.do?method: inicializarCasoUso',
            'httpSessionId': '8xcvLr-SmEs-yq6RtTF5wXY6.habitacao_bbrnpapllx013:siopi-internet-prd-node01_lx013',
            'scriptSessionId': '99E63DC129315328D07CCF8C813117E6517',
            'c0-scriptName': 'SIOPIAjaxFrontController',
            'c0-methodName': 'callActionForwardMethodLista',
            'c0-id': 0,
            'c0-param0': 'string:%2FsimulaOperacaoInternet',
            'c0-param1': 'string:listarCidades',
            'c0-param2': f'string:uf%3D{uf}',
            'batchId': 2
        }

        dados = urllib.parse.urlencode(params).encode('utf-8')
        # TODO: tratamento de exceções: quando a página não existir, mudar url, quando tiver sem conexão, etc
        try:
            with urllib.request.urlopen(self.URL1, dados) as response:
                response_text = response.read()
                cidades_raw = response_text.decode('utf-8')
        except urllib.error.URLError as erro:
            print(f'Problemas com a URL: {self.URL1} -> {erro}')
            return None
        except Exception as erro:
            print(f'Erro ao obter cidades: {erro=}')
            return None
        
        # TODO: implementar tratamento de exceções 
        self._extrair_cidades(cidades_raw)
        return self._cidades

    def _extrair_cidades(self, s: str) -> list[dict]:
        """Extrai cidades de str contendo javascript retornado pela Caixa.
        Extrai cidades e seus códigos da chamada a url retornada em variáveis javascript pelo método obter_cidades.
        O resultado da extração é setado no dicionário Simulador.cidades

        Args:
            s (str): string contendo o retorno em javascript

        Returns:
            list[dict]: retorna uma lista de dicionários contendo as cidades. 
        """
        self._cidades = []

        pos = s.find(self.ACHAR1)
        print('Econtrado padrão na posição: {}'.format(pos))
        if pos < 50:
            print('Não é possível continuar pois houve algum erro ao retornar as cidades!')
            return False

        # pega a partir do começo da declaração das variáveis
        s = s[pos:]

        # varrer linhas
        for linha in s.split('\n'):
            # verificar se chegou ao fim
            if linha.startswith(self.ACHAR2):
                break

            # retirar primeira parte, o objeto (antes do primeiro ponto)
            pos = linha.find('.')
            texto = linha[:pos + 1]
            linha = linha.replace(texto, '')

            # separar campos
            campos = linha.split(';')
            nome = campos[self.NOME].split('=')[1].replace('"', '').replace('\\', '')
            nome_sem_aspa = campos[self.NOME_SEM_ASPA].split('=')[1].replace('"', '')
            codigo = campos[self.CODIGO].split('=')[1]

            self._cidades.append(
                {
                    'cod_caixa': codigo,
                    'nome': nome,
                    'nome_sem_aspa': nome_sem_aspa
                }
            )

        self.total_cidades = len(self._cidades) 
        return self._cidades

    @property
    def cidades(self) -> list[dict]:
        return self._cidades

    @cidades.setter
    def cidades(self, v: list[dict]):
        """Cidades podem ser definidas também fora do módulo. Precisa atender 
        alguns critérios:
        - ser uma lista de dicionários;
        - ter os campos: cod_caixa, nome, nome_sem_aspa.
         """
        if type(v) is not list:
            raise ValueError('Tipo cidades precisa ser list.')

        if not v:
            raise ValueError('A lista de cidades não pode ser vazia.')

        if not 'cod_caixa' in v[0] or not 'nome' in v[0] or not 'nome_sem_aspa' in v[0]:
            raise ValueError('Lista precisa conter pelo menos um dicionário com os campos: cod_caixa, nome, nome_sem_aspa.')
        
        self._cidades = v
        self.total_cidades = len(self._cidades)

    def adicionar_cidade(self, cod_caixa: int, nome: str, 
                         nome_sem_aspa: str) -> bool:
        """Adiciona uma cidade a lista de dicionários de cidades. Usado
        quando os valores não são obtidos da caixa, mas sim de um banco
        de dados.

        Args:
            cod_caixa (int): código de identeficaçãod a cidade pra CEF.
            nome (str): nome da cidade.
            nome_sem_aspa (str): nome da cidade sem aspas.

        Returns:
            bool: True em caso de sucesso.
        """
        if cod_caixa == 0:
            print('cod_caixa não pode ser zero!')
            return False
        
        if len(nome) < 4:
            print('nome muito curto!')
            return False
        
        if len(nome_sem_aspa) < 4:
            print('É preciso preencher nome_sem_aspa!')
            return False
    
        self._cidades.append(
            {
                'cod_caixa': cod_caixa,
                'nome': nome,
                'nome_sem_aspa': nome_sem_aspa
            }
        )
        return True

    def _existe_cidade_selecionada(self) -> bool:
        """Verifica se existe uma cidade selecionada pelo usuário.

        Returns:
            bool: True quando existir cidade
        """
        if self.cidade_indice == -1:
            print('Não foi definido um índice. É preciso obter cidades e depois pesquisar código da cidade por nome.')
            return False
        else:
            return True

    def obter_opcoes_financiamento(self) -> list[OpcaoFinanciamento]:
        """Obtem as opções de financiamento de acordo com os dados passados. As opções de financiamento
        são retornadas numa lista de Enums OpcaoFinanciamento.

        Raises:
            ErroCidadeNaoSelecionada: é preciso selecionar uma cidade.
            ErroValorImovel: é preciso definir o valor do imóvel.
            ErroCPF: é preciso definir um CPF.
            ErroCelular: celular inválido ou não definido.
            ErroRendaFamiliar: renda familiar não definida ou inválida.
            ErroDataNascimento: data de nascimento não definida ou inválida.

        Returns:
            str: lista de Enums OpcaoFinanciamento com os campos versão de descrição preenchidos.
        """
        if not self._existe_cidade_selecionada():
            raise ErroCidadeNaoSelecionada('É preciso primeiro selecionar uma cidade.')
        
        cod_cidade = self._cidades[self.cidade_indice]['cod_caixa']
        cidade_sem_aspa = self._cidades[self.cidade_indice]['nome_sem_aspa']
        if type(cod_cidade) is not int:
            if cod_cidade and cod_cidade.isdigit():
                cod_cidade = int(cod_cidade)
            else:
                print('Não encontrou o código da cidade!')
                return ''

        if not self._valor_imovel:
            raise ErroValorImovel('É preciso definir o valor do imóvel')

        if not self.cpf:
            raise ErroCPF('É preciso definir um CPF válido.')

        if not self.celular:
            raise ErroCelular('É preciso definir o celular.')

        if not self._renda_familiar:
            raise ErroRendaFamiliar('É preciso definir a renda familiar bruta.')

        if not self.data_nascimento:
            raise ErroDataNascimento('É preciso definir a data de nascimento.')

        texto_tipo_financiamento: str='Residencial'     # TODO: implementar outros tipos de financiamento?
        texto_cidade:str = cidade_sem_aspa
        texto_uf: str = self.uf
        tipo_imovel = 1
        grupo_tipo_financiamento = self.tipo_financiamento.value
        valor_imovel: str = self.valor_imovel
        cpf: str = self.cpf
        celular: str = self.celular
        renda_familiar_bruta: str = self.renda_familiar
        data_nascimento: str = self.data_nascimento

        VERSAO = config.layout.CaixaObterOpcoesFinanciamento.VERSAO
        params = {
            'versao': VERSAO,             'permitePlanilha': 'S', 
            'vaEnquadraWS': '',           'vaMunicipioImovelWS': '',
            'vaVlAvaliacaoWS': '',        'vaVlRendaFamBrutaWS': '',
            'vaDtNascimentoProp1WS': '',  'vaPossuiImovelWS': '',
            'vaContaFgtsWS': '',          'inicioWS': '',
            'existeCpfCnpj': '',          'textoTipoFinanciamento': texto_tipo_financiamento,
            'textoCategoriaImovel': '',   'textoCidade': texto_cidade,
            'textoUF': texto_uf,          'convenio': '',
            'permiteDetalhamento': 'S',   'nuSeqPropostaInternet': '',
            'icPerguntaFatorSocial': 'S',
            'noPerguntaFatorSocial': 'Mais de um comprador ou dependente?',     # TODO: implementar mais de um comprador
            'dePerguntaFatorSocial': 'Informar se possui mais de um comprador na proposta e/ou possui dependente.',     # TODO: implementar mais de um comprador
            'isVoltar': 'false',          'isFiltrosDefault': '',
            'nomeConvenio': '',           'codContextoCredito': 1,
            'vaNuApf': '',                'isTipoPessoaEditavel': '',
            'vaIcTaxaCustomizada': '',    'ehPeriodoFeirao': 'false',   # TODO: ehPeriodoFeirao: obter primeiro através de URL
            'ehMunicipioFeirao': 'false', 'pessoa': 'F',                # TODO: ehMunicipioFeirao: obter primeiro através de URL
            'tipoImovel': tipo_imovel,    'grupoTipoFinanciamento': grupo_tipo_financiamento, 
            'valorReforma': '',           'valorImovel': valor_imovel,
            'uf': self.uf,                'cidade': cod_cidade,
            'nuCpfCnpjInteressado': cpf,  'nuTelefoneCelular': celular,
            'rendaFamiliarBruta': renda_familiar_bruta, 'dataNascimento': data_nascimento,
        }

        if ((not config.geral.Caixa.PERGUNTAR_CLIENTE_CAIXA 
             and config.geral.Caixa.CLIENTE_CAIXA) 
             or self.possui_relacionamento_caixa):
            params['icPossuiRelacionamentoCAIXA'] = 'V'

        if self.tres_anos_fgts:
            params['vaContaFgts'] = 'V'

        params.update(
            {
                'beneficiadoFGTS': 'F',     'dataBeneficioFGTS': '',
                'cnpjConvenio': ''
            }
        )

        if self.mais_de_um_comprador_dependente:
            params['icFatorSocial'] = 'V'

        dados = urllib.parse.urlencode(params).encode('utf-8')
        # TODO: tratamento de exceções: quando a página não existir, quando tiver sem conexão, etc
        html: str = ''
        with urllib.request.urlopen(self.URL3, dados) as response:
            html = response.read().decode('ISO-8859-1')
        return self._extrair_opcoes_financiamento(html)

    def _extrair_opcoes_financiamento(self, html: str) -> list[OpcaoFinanciamento]:
        """Extrai opções de financiamento a partir do html e defini uma lista de opções de financiamento.
        Em cada opção de financiamento é definida a versão e a descrição.

        Args:
            html (str): html passado com o resultado da chamada a URL.

        Raises:
            ErroObterOpcaoFinanciamento: não encontrou nenhuma tag li.
            ErroObterOpcaoFinanciamento: não encontrou os links com a opções de financiamento.
            ErroObterOpcaoFinanciamento: não encontrou os eventos onclick dos links a.
            ErroObterOpcaoFinanciamento: não encontrou o JS com os parâmetros versão e descrição.
            ErroObterOpcaoFinanciamento: não encontrou o separador no JS.
            ErroObterOpcaoFinanciamento: não encontrou todos os parâmetros.
            ErroObterOpcaoFinanciamento: não conseguiu definir todas as variáveis

        Returns:
            list[OpcaoFinanciamento]: lista de enums com as opções de financiamento.
        """

        bs = BeautifulSoup(html, "html.parser")
        lis = bs.find_all('li', attrs={'class': 'group-block-item'})

        if len(lis) == 0:
            raise ErroObterOpcaoFinanciamento("Não encontrou os li's em _extrair_opcoes_financiamento.")

        T_OBTER_OPCOES_FINANCIAMENTO_JS = config.layout.CaixaObterOpcoesFinanciamento.T_OBTER_OPCOES_FINANCIAMENTO_JS
        T_OBTER_OPCOES_FINANCIAMENTO_SEP1 = config.layout.CaixaObterOpcoesFinanciamento.T_OBTER_OPCOES_FINANCIAMENTO_SEP1

        OPCOES_FINANCIAMENTO_ACEITAS = config.geral.Caixa.OPCOES_FINANCIAMENTO_ACEITAS

        opcoes_financiamento: list = []
        for i in range(len(lis)):
            a = lis[i].find('a')
            if not a:
                raise ErroObterOpcaoFinanciamento('Não encontrou os links ao _extrair_opcoes_financiamento.')
                
            onclick = a.get('onclick')
            if not onclick:
                raise ErroObterOpcaoFinanciamento('Não conseguiu obter os ev. onclick dos links em _extrair_opcoes_financiamento.')
            
            pos: int
            pos = onclick.find(T_OBTER_OPCOES_FINANCIAMENTO_JS)
            if pos == -1:
                raise ErroObterOpcaoFinanciamento('Não encontrou método JS ao _extrair_opcoes_financiamento.')

            pos = onclick.find(T_OBTER_OPCOES_FINANCIAMENTO_SEP1)
            if pos == -1:
                raise ErroObterOpcaoFinanciamento('Não encontroou padrão SEP1 em _extrair_opcoes_financiamento.')

            met: str = onclick[ :pos]
            
            try:
                params = met.split('\n')[1:4]
            except Exception:
                raise ErroObterOpcaoFinanciamento('Não encontrou todos os parâmetros ao _extrair_opcoes_financiamento')

            try:
                cod: str = params[0].strip()[ :-1]
                versao: str = params[1].strip()[ :-1]
                descricao: str = params[2].strip()[1:-1]
            except Exception:
                raise ErroObterOpcaoFinanciamento('Não conseguiu definir as variávels em _extrair_opcoes_financiamento')

            if not cod:
                raise ErroObterOpcaoFinanciamento('Não encontrou código da opção de financiamento!')
            
            cod = int(cod)

            if OPCOES_FINANCIAMENTO_ACEITAS:
                if not cod in OPCOES_FINANCIAMENTO_ACEITAS:
                    print(f'Opção de financiamento NÃO aceita: {cod}: {descricao}')
                    continue

            try:
                opcao_financiamento = OpcaoFinanciamento(cod)
            except ValueError as erro:
                # TODO: implementar log de erro
                # TODO: implementar alerta ao desenvolvedor
                print('OPÇÃO DE FINANCIMENTO DESCONHECIDA!')
                continue
            opcao_financiamento.versao = versao
            opcao_financiamento.descricao = descricao
            opcoes_financiamento.append(opcao_financiamento)
        return opcoes_financiamento

    def simular(self) -> SimulacaoResultado:
        """Executa a simulação a partir dos atributos definidos, traz as informações 
        do banco e guarda num objeto SimulacaoResultado.

        Raises:
            ErroCidadeNaoSelecionada: não foi definida uma cidade, primeiro é preciso buscar cidades.
            ErroTipoFinanciamento: precisa ser definido o tipo de imóvel.
            ErroValorImovel: valor do imóvel não definido ou abaixo do valor mínimo aceito.
            ErroCPF: CPF não definido ou não passou na validação.
            ErroCelular: celular não definido ou inválido.
            ErroRendaFamiliar: renda familiar não definida ou abaixo da renda familiar bruta mínima.
            ErroDataNascimento: data de nascimento inválida ou não definida.
            ErroOpcaoFinanciamentoVersao: é preciso definir uma versão pra OpcaoFinanciamento, obter_opcoes_financiamento.
            ErroRendaFamiliarInsuficente: acontece quando o banco recusa a renda familiar pra essa simulação.

        Returns:
            SimulacaoResultado: traz os dados obtidos transformados do HTML pra esse objeto que contém
            as principais informações da simulação.
        """        
        if not self._existe_cidade_selecionada():
            raise ErroCidadeNaoSelecionada('É preciso primeiro selecionar uma cidade.')

        if not self._tipo_financiamento:
            raise ErroTipoFinanciamento('É preciso definir o tipo de financiamento (usado, novo, reforma, etc).')

        if not self._valor_imovel:
            raise ErroValorImovel('É preciso definir o valor do imóvel')

        if not self.cpf:
            raise ErroCPF('É preciso definir um CPF válido.')
        
        if not self.celular:
            raise ErroCelular('É preciso definir o celular.')
        
        if not self._renda_familiar:
            raise ErroRendaFamiliar('É preciso definir a renda familiar bruta.')

        if not self.data_nascimento:
            raise ErroDataNascimento('É preciso definir a data de nascimento.')

        if not self._opcao_financiamento.versao:
            raise ErroOpcaoFinanciamentoVersao('É preciso definir uma versão para OpcaoFinanciamento. Executar Simulador.obter_opcao_financiamento.')

        tipo_imovel = 1
        va_conta_fgts = '' if not self.tres_anos_fgts else 'V'
        grupo_tipo_financiamento = self.tipo_financiamento.value
        
        data_beneficio_fgts = ''
        beneficiado_fgts: str = 'F'
        cod_contexto_credito = 1
        permite_detalhamento = 'S'
        ic_fator_social = '' if not self.mais_de_um_comprador_dependente else 'V'
        possui_relacionamento_caixa = 'V' if ((not 
            config.geral.Caixa.PERGUNTAR_CLIENTE_CAIXA
            and config.geral.Caixa.CLIENTE_CAIXA) 
            or self.possui_relacionamento_caixa) else ''

        valor_imovel = urllib.parse.quote(self.valor_imovel)
        renda_familiar = urllib.parse.quote(self.renda_familiar)
        data_nascimento = urllib.parse.quote_plus(self.data_nascimento)
        uf = self.uf
        cod_cidade = self._cidades[self.cidade_indice]['cod_caixa']

        nu_item_produto = self.opcao_financiamento.value
        versao = self._opcao_financiamento.versao
        valor_reforma = ''          # TODO: implementar?
        tipo_pessoa = 'F'           # TODO: verificar Itamarzim se vai vender pessoa Jurídica tb
        cpf = str(self._cpf)        # CPF  não é formatado
        celular = urllib.parse.quote_plus(self.celular, safe='()')

        # alteração de prazo, valor de entrada        
        prazo: int = 0
        valor_entrada: str = ''
        complementou_dados_subsidio: str = ''
        cod_sistema_amortizacao_alterado: str = 'undefined'
        if self._prazo or self._valor_entrada:
            prazo = self._prazo
            valor_entrada = urllib.parse.quote(self.valor_entrada)
            complementou_dados_subsidio = 'true'
            cod_sistema_amortizacao_alterado = \
                urllib.parse.quote(self._cod_sistema_amortizacao, safe='')
            celular = ''

        prestacao_max: str = ''
        if self._prestacao_max:
            prestacao_max = urllib.parse.quote(self.prestacao_max)

        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Content-Type': 'text/plain',
            'Origin': 'http://www8.caixa.gov.br',
            'Referer': 'http://www8.caixa.gov.br/siopiinternet-web/simulaOperacaoInternet.do?method=enquadrarProdutos',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 OPR/82.0.4227.58',
        }

        param2: str
        param2 = f"""string:valorImovel%3D{valor_imovel}%3ArendaFamiliarBruta%3D{renda_familiar}%3AtipoImovel%3D{tipo_imovel}%3AimovelCidade%3D%3AvaContaFgts%3D{va_conta_fgts}%3AgrupoTipoFinanciamento%3D{grupo_tipo_financiamento}%3AdataNascimento%3D{data_nascimento}%3Auf%3D{uf}%3Acidade%3D{cod_cidade}%3AnuItemProduto%3D{nu_item_produto}%3AnuVersao%3D{versao}%3AvalorReforma%3D{valor_reforma}%3AcodigoSeguradoraSelecionada%3Dundefined%3AnomeSeguradora%3Dundefined%3AdataBeneficioFGTS%3D{data_beneficio_fgts}%3AbeneficiadoFGTS%3D{beneficiado_fgts}%3AcodContextoCredito%3D{cod_contexto_credito}%3AcomplementouDadosSubsidio%3D{complementou_dados_subsidio}%3Apessoa%3D{tipo_pessoa}%3Aconvenio%3D%3AnuEmpresa%3D%3AnuSeqPropostaInternet%3D%3ApermiteDetalhamento%3D{permite_detalhamento}%3AcodSistemaAmortizacaoAlterado%3D{cod_sistema_amortizacao_alterado}%3AnuCpfCnpjInteressado%3D{cpf}%3AicFatorSocial%3D{ic_fator_social}%3AicPossuiRelacionamentoCAIXA%3D{possui_relacionamento_caixa}%3AicServidorPublico%3D%3AicContaSalarioCAIXA%3D%3AvaNuApf%3D%3AnuTelefoneCelular%3D{celular}%3AicAceitaReceberSMS%3D%3AvaIcTaxaCustomizada%3D"""
        if valor_entrada:
            param2 += f"""%3Aprazo%3D{prazo}%3ArecursosProprios%3D{valor_entrada}"""
        if prestacao_max:
            param2 += f"""%3AprestacaoMaxDesejada%3D{prestacao_max}"""

        params = {
            'callCount': 1,
            'page': '/siopiinternet-web/simulaOperacaoInternet.do?method=enquadrarProdutos',
            'httpSessionId': 'LxaBwu1OVnyP1Sm6KPSANsgJ.habitacao_dbrnpapllx016:siopi-internet-prd-node02_lx016',
            'scriptSessionId': 'F9BEB90B5F0DCAB29782C79D4A842155976',
            'c0-scriptName': 'SIOPIAjaxFrontController',
            'c0-methodName': 'callActionForwardMethodDiv',
            'c0-id': 0,
            'c0-param0': 'string:%2FsimulaOperacaoInternet',
            'c0-param1': 'string:simularOperacaoImobiliariaInternet',
            'c0-param2': f'{param2}',
            'c0-param3': 'string:resultadoSimulacao',
            'batchId': 0
        }

        dados = urllib.parse.urlencode(params).encode('utf-8')
        req = urllib.request.Request(self.URL4, dados, headers)
        simulacao_raw: str = ''
        # TODO: tratamento de exceções: quando a página não existir, quando tiver sem conexão, etc
        with urllib.request.urlopen(req) as response:
            # correção, agora sempre tá retornando gzip, precisa descompactar primeiro
            #simulacao_raw = response.read().decode('utf-8')
            simulacao_raw = gzip.decompress(response.read()).decode('utf-8')
        
        html = self._extrair_html_sim(simulacao_raw)
        sim_resultado = SimulacaoResultado(html, self.opcao_financiamento)
        try:
            sim_resultado.extrair_dados()
        except:
            raise

        sa_chave = sim_resultado.sistema_amortizacao_chave_sel
        self.cod_sistema_amortizacao = (
            sim_resultado.cods_sistema_amortizacao[sa_chave]
        )

        return sim_resultado

    def _extrair_html_sim(self, simulacao_raw: str) -> str:
        if not simulacao_raw:
            print('É preciso executar simulação antes de extrair html!')
            return ''
        
        pos1 = simulacao_raw.find(self.ACHAR_INI_HTML_SIM) + len(self.ACHAR_INI_HTML_SIM)
        if pos1 < 50:
            print('Padrão HTML ini da simulação não encontrado!')
            return ''
        
        pos2 = simulacao_raw.find(self.ACHAR_FIM_HTML_SIM)
        html = simulacao_raw[pos1:pos2]
        html = ajustar_esc_char(html)
        if not html:
            print('Não encontrou html no resultado da simulação!')
            return ''
        
        return html

    def procurar(self, s: str, l: list, max_res: int = 10) -> list[str]:
        """Procurar texto por similaridade em uma lista. Se for texto 
        identico retorna apenas um item, caso contrário retorna uma lista
        de str.

        Args:
            s (str): string contendo parte ou o nome da string a ser procurada.
            l (list): lista contendo todos os itens.
            max_res (int, optional): corresponde ao número máximo de resultados 
                    a serem trazidos na pesquisa. Defaults to 10.

        Returns:
            list: cada item da lista corresponde a uma str, se for s identico ao da 
                  lista retorna apenas um item.
        """
        s = remover_acentos(s.upper())
        pesq = ngram.NGram(l)
        self.cidades_filtro = []

        for i, (cidade, rank) in enumerate(pesq.search(s, threshold=0.1)):
            self.cidades_filtro.append(cidade)
            # texto eh igual
            if rank == 1.0:
                break

            if i + 1 == max_res:
                break

        return self.cidades_filtro

    def procurar2(self, q: str, l: list[tuple], key: int=2, max_res: int=10) -> list[dict]:
        """Procurar texto por similaridade em uma lista. Se for texto 
        identico retorna apenas um item, caso contrário retorna uma lista
        de dicionários com os campos como na propriedade cidades.

        Args:
            q (str): string contendo parte ou o nome da string a ser procurada.
            l (list): lista de tuplas contendo todos os itens separados por campos.
            key (int): chave da tuple que vai ser pesquisada.
            max_res (int, optional): corresponde ao número máximo de resultados 
                    a serem trazidos na pesquisa. Defaults to 10.

        Returns:
            list: cada item da lista corresponde a uma str, se for s identico ao da 
                  lista retorna apenas um item.
        """
        q = remover_acentos(q.upper())
        n = ngram.NGram(l, key=lambda x: x[key])
        cidades: list[dict] = []
        for i, t in enumerate(n.search(query=q, threshold=0.1)):
            cidade_dados = t[0]
            rank = t[1]

            id, cod_caixa, nome, nome_sem_aspa = cidade_dados

            cidades.append(
                {
                    'id': id,
                    'cod_caixa': cod_caixa,
                    'nome': nome,
                    'nome_sem_aspa': nome_sem_aspa,
                    'rank': rank
                }
            )

            if rank == 1.0 or i + 1 == max_res:
                break

        return cidades

    def obter_cidades_nomes(self) -> list:
        """Extrai apenas os nomes da lista de dicionários de cidades.

        Returns:
            list: lista com todas as cidades.
        """
        if len(self._cidades) == 0:
            print('Favor obter cidades antes de converter pra lista.')
            return []

        return [d['nome'] for d in self._cidades]

    def obter_cod_cidade_por_nome(self, cidade: str) -> int:
        """Obtém código da cidade através do nome exato. Também armazena o índice da 
        lista de cidades em Simulador.cidade_indice.

        Args:
            cidade (str): nome exato da cidade.

        Returns:
            int: código da cidade
        """
        if not cidade:
            print('Definir cidade!')
            return 0

        if not self._cidades:
            print('self._cidades está vazia. Tente obj_sim.obter_cidades()')
            return 0
        
        for i, d in enumerate(self._cidades):
            if d['nome'] == cidade:
                self.cidade_indice = i
                return d['cod_caixa']

        return 0


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

        valor_inicial  = Decimal2(int(valor_imovel - valor_perc))
        valor_final = Decimal2(int(valor_imovel + valor_perc))
        return cls(valor_inicial, valor_final)

    @property
    def url(self) -> str:
        valor_imovel_inicial: str = f'{self._valor_imovel_inicial:.2f}'
        valor_imovel_final: str = f'{self._valor_imovel_final:.2f}'

        return self.url_base.format(valor_imovel_inicial, valor_imovel_final)