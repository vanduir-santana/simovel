#!/usr/bin/env python
# coding: utf-8
"""
Simulador de Crédito Imobiliário Caixa Econômica Federal.

As operações que podem ser feitas no Simulador via site da Caixa,
também podem ser feitas a partir desse módulo. A partir dela é
possível automatizar tarefas, como integrar a uma API REST ou em
para aplicações IA como chatbots.
"""

__version__ = '0.72'
__author__ = 'Vanduir Santana Medeiros'


from enum import Enum
import gzip
import re
import os

from urllib.request import (
    Request,
    build_opener,
    HTTPCookieProcessor,
    OpenerDirector
)
from urllib.response import addinfourl
import http.cookiejar
import urllib.parse
import urllib.error
import bs4
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
import ngram

from simovel.exceptions import *
from simovel.util import remover_acentos
from simovel.util import Decimal2, dwr_gerar_dwrsess, dwr_gerar_page_id
from simovel.config.geral import Caixa as CfgCaixa, Parametros
from simovel.config import layout as config_layout
from simovel.sims.base import SimuladorBase, Banco
from simovel.sims.base import SimulacaoResultadoBase
from rest_api.app_factory import create_app
from rest_api.models.simulacao import EstadoModel


class TipoImovel(Enum):
    RESIDENCIAL = 1
    COMERCIAL = 2
    # RURAL = # TODO: implementar financ. rural


class TipoFinanciamento(Enum):
    # pra imóveis residenciais usa todos descomentados, 
    # pra comerciais apenas novo e usado
    NOVO = 1
    USADO = 4
    AQUISICAO_TERRENO = 6
    CONSTRUCAO = 2
    EMPRESTIMO_GARANTIDO_POR_IMOVEL = 7
    #EMPRESTIMO_GARANTIDO_POR_IMOVEL = 5
    #IMOVEIS_CAIXA = 6
    #REFORMA_AMPLIACAO = 7

    @property
    def name(self):
        if self.value == 6:
            return 'Aquisição de Terreno'
        elif self.value == 2:
            return 'Construção'
        elif self.value == 7:
            return 'Empréstimo Garantido por Imóvel'            
        else:
            return self._name_.capitalize()

    @property
    def texto_categoria_imovel(self) -> str:
        match self.value:
            case 1:
                return 'Aquisição de Imóvel Novo'
            case 4:
                return ''
            case 6:
                return ''
            case 2:
                return ''
            case 7:
                return '' 

    @classmethod
    def obter_tipos_financiamento_comercial(cls) -> tuple:
        return (
            cls.NOVO,
            cls.USADO,
            cls.EMPRESTIMO_GARANTIDO_POR_IMOVEL,
        )
   

class OpcaoFinanciamento:
    """
    Guarda as opções de financiamento geradas quando é chamado o
    endpoint correspondente da Caixa.

    Mantém a compatibilidade com o padrão da classe anterior que
    herdava de Enum. Pra que isso aconteça a classe também tem a
    propriedade value e também é possível instaciar a partir do
    código da opção de financiamento. Agora não armazena mais as
    opções de financiamento. Antes era preciso adicionar manualmente
    as opções de financiamento. Da forma atual preenche a partir do 
    retorn de SimuladorCaixa.obter_opcoes_financiamento().
    """
    def __init__(self, value: str | int) -> None:
        """
        Método construtor.

        Args:
            value (str): valor correspondente ao código da opção de
                financiamento.
        """
        self._value = value

    @property
    def value(self) -> str | int:
        return self._value

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

    def __str__(self) -> str:
        return f'<OpcaoFinanciamento>: {self.value} - {self.descricao}'


class MsgsCaixa(Enum):
    RENDA_INSUFICIENTE = (
        'ATENÇÃO! RENDA INSUFICIENTE PARA REALIZAR A OPERAÇÃO.'
    )
    RENDA_INSUFICIENTE_FINAL = 'RENDA INSUFICIENTE PARA REALIZAR A OPERAÇÃO.'
    # 2 espaços nos item abaixo
    VALOR_FINANCIAMENTO_INFERIOR = (
        'ATENÇÃO!  VALOR DE FINANCIAMENTO CALCULADO É INFERIOR AOS LIMITES '
        'DO PROGRAMA.'
    )
    VALOR_FINANCIAMENTO_INFERIOR2 = (
        'ATENÇÃO!  VALOR DE FINANCIAMENTO CALCULADO É INFERIOR AO LIMITE '
        'PERMITIDO.'
    )


class SimuladorCaixa(SimuladorBase):
    """
    Comunica com os simulador da Caixa Econômica Federal para executar
    sua API (oculta) de simulação de Crédito Imobiliário retornando
    dados do resultado da simulação.
    """
    URL0 = (
        'https://www8.caixa.gov.br/siopiinternet-web/'
        'simulaOperacaoInternet.do?method=inicializarCasoUso'
    )
    URL1 = (
        'https://www8.caixa.gov.br/siopiinternet-web/dwr/call/plaincall/'
        'SIOPIAjaxFrontController.callActionForwardMethodLista.dwr'
    )
    URL2 = (
        'https://www8.caixa.gov.br/siopiinternet-web/'
        'simulaOperacaoInternet.do?method=validarMunicipioFeirao&'
        'cidade={cod_cidade}&requisicaoModal=true'
    )
    URL3 = (
        'https://www8.caixa.gov.br/siopiinternet-web/'
        'simulaOperacaoInternet.do?method=enquadrarProdutos'
    )
    URL4 = (
        'https://www8.caixa.gov.br/siopiinternet-web/dwr/call/plaincall/'
        'SIOPIAjaxFrontController.callActionForwardMethodDiv.dwr'
    )
    # Expressão Regular pra encontrar array de objetos js com cidades:
    #     dwr.engine.remote.handleCallback("5", "0", [{
    RE_PADRAO_CIDADES = \
        r'\s+dwr.engine.remote.handleCallback\("\d",\s*"\d",\s*(\[\{.*?\}\])\)'
    # Padrões Expressão Regular para campos no objeto de cidades dentro 
    # do array js retornado pela URL Caixa
    RE_PADRAO_CIDADES_CODIGO = r'\s*(codigo):\s*(\d*),'
    RE_PADRAO_CIDADES_NOME = r'\s*nome:\s*"([^"]*)",'
    RE_PADRAO_CIDADES_SEM_ASPA = r'\s*nomeSemAspa:\s*"([^"]*)",'
    # Padrao Resultado simulacao
    #  'preencheDiv("resultadoSimulacao","aqui fica o html");'
    RE_RESULTADO_SIMULACAO = \
        r'\s*preencheDiv\("resultadoSimulacao",\s*"(.*?)"\);'
    ARQUIVO_VERSAO = '.sim-caixa-versao'

    def __init__(self) -> None:
        super().__init__(banco=Banco.CAIXA)
        self._tipo_imovel = TipoImovel.RESIDENCIAL
        self._tipo_financiamento = TipoFinanciamento.NOVO
        self._possui_imovel_cidade = False
        self._tres_anos_fgts: bool = False
        self._mais_de_um_comprador_dependente: bool = False
        self._possui_relacionamento_caixa = False
        self._servidor_publico = False
        #self._opcao_financiamento = \
        #    OpcaoFinanciamento.PROGRAMA_CASA_VERDE_AMARELA
        self._opcao_financiamento = OpcaoFinanciamento('')
        self._valor_entrada: Decimal2 = Decimal2('0')
        self._cod_sistema_amortizacao = 'undefined'
        self._prestacao_max: Decimal2 = Decimal2('0')

        self._cidades: list[dict] = []
        self.cidades_filtro: list[str] = []
        self.cidade_indice: int = -1
        self._versao_salva: str = ''
        self._versao_atual: str = ''

        # melhoria: inicia sessão com cookies compartilhados entre URLs
        self._user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        )
        self._cookie_jar = http.cookiejar.CookieJar()
        self._opener: OpenerDirector = build_opener(
            HTTPCookieProcessor(self._cookie_jar)
        )
        self._headers_base = {
            "User-Agent": self._user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/"
                "avif,image/webp,image/apng,*/*;q=0.8,application/"
                "signed-exchange;v=b3;q=0.7"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self._iniciar_sessao()
        self._script_session_id = self._gerar_script_session_id()

    def _iniciar_sessao(self,):
        """
        Abre página inicial do simulador sempre que instanciar classe.
        Isso garante que os cookies serão salvos e compartilhados entre
        as aberturas de URLs.
        """
        req = Request(self.URL0, headers=self._headers_base)
        html: str = ''
        with self._opener.open(req) as response:
            response: addinfourl
            html = response.read().decode('latin-1')

        # obtem versão simulador (atual e salva)
        self._versao_salva = self._obter_versao_salva()
        self._versao_atual = self._obter_versao_atual(html)
        self._comparar_versoes()
    
    def _obter_versao_salva(self) -> str:
        """
        Obtem versão salva localmete no arquivo de versão do simulador
        (site).
        """
        if not os.path.exists(self.ARQUIVO_VERSAO):
            raise Exception(f'Favor criar arquivo {self.ARQUIVO_VERSAO}.')

        versao: str = ''
        with open(self.ARQUIVO_VERSAO, 'r') as f:
            versao = f.readline().strip()

        if not versao:
            raise Exception(f'Arquivo de versão está vazio!')

        return versao 

    def _obter_versao_atual(self, html: str) -> str:
        """
        Obtem versão a partir da página inicial do simulador (site).
        Chamar quando estiver na fase de opções de financiamento.
        """
        bs = BeautifulSoup(html, 'html.parser')
        input_versao = bs.find(
            'input',
            attrs={'type': 'hidden', 'name': 'versao'}
        )

        if not input_versao:
            raise Exception('NÃO encontrou input com a versão!')

        if isinstance(input_versao, Tag):
            return str(input_versao.get('value', '')).strip()

        raise Exception('Não conseguiu obter versão atual do simulaodr!')

    def setar_versao_arquivo(self, versao: str) -> None:
        """
        Seta versão em arquivo texto quando acessar URL inicial do simulador.
        """
        with open(self.ARQUIVO_VERSAO, 'w') as f:
            f.write(versao)

    def _comparar_versoes(self) -> None:
        """
        Comparar versão salva com versão atual. Atualiza versão salva
        se tiver diferente. Disparar evento quando versões forem
        diferentes.
        """
        print(f'Versão salva: "{self._versao_salva}"')
        print(f'Versão atual: "{self._versao_atual}"')

        if self._versao_atual != self._versao_salva:
            # TODO: disparar evento para enviar e-mail avisando mudança
            # de versão. Útil para fazer ajustes no layout
            print('#' * 44)
            print('Versão salva diferente da versão atual!')
            print('#' * 44)
            print('Salvando versão atual em arquivo...')
            self.setar_versao_arquivo(self._versao_atual)
            self._versao_salva = self._obter_versao_salva()
            print(f'Versão salva: {self._versao_salva}')

    def _obter_valor_cookie(self, nome: str) -> str | None:
        """
        Obtem valor do cookie a partir do nome (key).
        """
        for c in self._cookie_jar:
            if c.name == nome:
                print(
                    f'>>> _obter_valor_cookie():{nome}={c.value}'
                )
                return c.value

        return ''
    
    def _gerar_script_session_id(self) -> str:
        """
        Gerar o scriptSessionId, que geralmente é gerado a partir da
        lib engine.js, no carregamento do simulador (site). Como a
        urllib não roda o JS, então é preciso converter o trecho
        onde o scriptSessionId é gerado para código Python.
        scriptSessionId é gerado a partir da combinação do cookie
        DWRSESSIONID e _pageId. Tanto a primeira de scriptSessionId,
        quanto a segunda parte são gerados por funções (começam com
        as iniciais dwr_) que foram convertidas do engine.js para
        Python.
        """
        dwr_session_id: str = dwr_gerar_dwrsess()
        page_id: str = dwr_gerar_page_id()

        script_session_id = f"{dwr_session_id}/{page_id}"
        return script_session_id

    @classmethod
    def a_partir_nome_cidade(
        cls, nome_cidade: str,
        tipo_financiamento: TipoFinanciamento,
        valor_imovel: Decimal2 | str,
        cpf: str,
        celular: str, 
        renda_familiar: str | Decimal2,
        data_nasc: str, 
        tres_anos_fgts: bool,
        mais_de_um_comprador_dependente: bool
    ) -> 'SimuladorCaixa':
        """
        Cria um objeto SimuladorCaixa a partir do nome da cidade, 
        pesquisando as cidades do site da Caixa. Pra dar continuidade a
        simulação é preciso obter as opções de financiamento,
        selecionar uma e executar o método simular.

        Args:
            nome_cidade (str): nome exato da cidade a ser pesquisada.
            tipo_financiamento (TipoFinanciamento): tipo financiamento.
            valor_imovel (str | Decimal2): valor do imóvel.
            cpf (str): CPF.
            celular (str): fone celular.
            renda_familiar (str | Decimal2): renda familiar bruta.
            data_nasc (str): data de nascimento.
            tres_anos_fgts (bool): possui três anos de FGTS?
            mais_de_um_comprador_dependente (bool): mais de um comprador
            ou dependente?

        Raises:
            ErroCidadeNaoSelecionada: não existe a cidade.

        Returns:
            SimuladorCaixa: retorna objeto com os parâmetros definidos.
        """
        Decimal2.setar_local_pt_br()
        sim_caixa = cls()
        sim_caixa.obter_cidades()
        cod_cidade: int = sim_caixa.obter_cod_cidade_por_nome(nome_cidade)

        if cod_cidade == 0:
            raise ErroCidadeNaoSelecionada(
                f'NÃO encontrou a cidade {nome_cidade}'
            )

        sim_caixa.tipo_financiamento = tipo_financiamento
        sim_caixa.valor_imovel = valor_imovel
        sim_caixa.cpf = cpf
        sim_caixa.celular = celular
        sim_caixa.renda_familiar = renda_familiar
        sim_caixa.data_nascimento = data_nasc
        sim_caixa.tres_anos_fgts = tres_anos_fgts
        sim_caixa.mais_de_um_comprador_dependente = \
            mais_de_um_comprador_dependente

        return sim_caixa

    @property
    def tipo_imovel(self) -> TipoImovel:
        return self._tipo_imovel

    @tipo_imovel.setter
    def tipo_imovel(self, v: TipoImovel):
        if type(v) is not TipoImovel:
            raise ErroTipoImovel(f'Tipo imóvel precisa ser {TipoImovel}')

        self._tipo_imovel = v
    
    @property
    def tipo_financiamento(self) -> TipoFinanciamento:
        return self._tipo_financiamento

    @tipo_financiamento.setter
    def tipo_financiamento(self, v: TipoFinanciamento):
        if type(v) is not TipoFinanciamento:
            raise ErroTipoFinanciamento(
                f'Tipo Imóvel precisa ser {TipoFinanciamento}'
            )
            
        if (
            self._tipo_imovel == TipoImovel.COMERCIAL and
            v not in TipoFinanciamento.obter_tipos_financiamento_comercial()
        ):
            raise ErroTipoFinanciamento(
                f'Tipo de financiamento {v} não aceito para imóvel '
                f'comercial.'
            )
        
        self._tipo_financiamento = v

    @property
    def possui_imovel_cidade(self) -> bool:
        return self._possui_imovel_cidade
    
    @possui_imovel_cidade.setter
    def possui_imovel_cidade(self, v: bool):
        self._possui_imovel_cidade = v

    @property
    def tres_anos_fgts(self) -> bool:
        return self._tres_anos_fgts

    @tres_anos_fgts.setter
    def tres_anos_fgts(self, v: bool):
        self._tres_anos_fgts = v

    @property
    def mais_de_um_comprador_dependente(self) -> bool:
        return self._mais_de_um_comprador_dependente

    @mais_de_um_comprador_dependente.setter
    def mais_de_um_comprador_dependente(self, v):
        if type(v) != bool:
            raise ValueError(
                'Propriedade mais_de_um_comprador_dependente precisa ser bool.'
            )
        
        self._mais_de_um_comprador_dependente = v

    @property
    def possui_relacionamento_caixa(self) -> bool:
        return self._possui_relacionamento_caixa

    @possui_relacionamento_caixa.setter
    def possui_relacionamento_caixa(self, v: bool):
        self._possui_relacionamento_caixa = v

    @property
    def servidor_publico(self) -> bool:
        return self._servidor_publico

    @servidor_publico.setter
    def servidor_publico(self, v: bool):
        self._servidor_publico = v

    @property
    def opcao_financiamento(self) -> OpcaoFinanciamento:
        return self._opcao_financiamento

    @opcao_financiamento.setter
    def opcao_financiamento(self, v: OpcaoFinanciamento):
        if type(v) is not OpcaoFinanciamento:
            raise ErroOpcaoFinanciamento(v)
        self._opcao_financiamento = v
    
    @property
    def valor_entrada(self) -> str:
        return self._valor_entrada.formatar_moeda(retirar_rs=True)

    @valor_entrada.setter
    def valor_entrada(self, v) -> None:
        if not v:
            self._valor_entrada = Decimal2(0)
            return

        d2: Decimal2
        try:
            d2 = Decimal2.from_cur_str(v)
        except Exception:
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
            self._prestacao_max = Decimal2(0)
        d2: Decimal2

        try:
            d2 = Decimal2.from_cur_str(v)
        except Exception:
            raise ErroPrestacaoMax('Valor da prestação inválido.')
        self._prestacao_max = d2

    def obter_cidades_db(self, uf: str='') -> list[dict] | None:
        """
        Obtém cidades a partir do banco de dados da API.

        Args:
            uf (str): sigla do estado.

        Returns:
            list[dict]: retorna um dicionário contendo a chave como uma
            string sem aspas com o nome cidade; o valor é uma tupla com
            o código da cidade e o nome dela com aspas.
        """
        if uf:
            self.uf = uf
        else:
            uf = self.uf

        print(f'Buscando cidades no banco de dados para a UF: {uf}...')

        app = create_app()

        with app.app_context():
            cidades: list[dict] = EstadoModel.obter_cidades(
                uf=uf,
                lista_dicts=True
            )

            if len(cidades) == 0:
                print('Não conseguiu carregar cidades do banco de dados!')
                return []

            self._cidades = cidades
            return cidades

    def obter_cidades(self, uf: str = '') -> list[dict] | None:
        """
        Obtém cidades com seus respectivos códigos no modo raw.

        Args:
            uf (str): sigla do estado.

        Returns:
            list[dict]: retorna um dicionário contendo a chave como uma 
            string sem aspas com o nome cidade; o valor é uma tupla com
            o código da cidade e o nome dela com aspas.
        """
        if uf:
            self.uf = uf
        else:
            uf = self.uf

        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'text/plain',
            "User-Agent": self._user_agent,
        }

        params = {
            'callCount': 1,
            'nextReverseAjaxIndex': 0,
            'c0-scriptName': 'SIOPIAjaxFrontController',
            'c0-methodName': 'callActionForwardMethodLista',
            'c0-id': 0,
            'c0-param0': 'string:%2FsimulaOperacaoInternet',
            'c0-param1': 'string:listarCidades',
            'c0-param2': f'string:uf%3D{uf}',
            'batchId': 5,
            'instanceId': 0,
            'page': (
                '%2Fsiopiinternet-web%2FsimulaOperacaoInternet.do%3F'
                'method%3DinicializarCasoUso'
            ),
            'scriptSessionId': self._script_session_id
        }

        dados = urllib.parse.urlencode(params).encode('utf-8')
        # TODO: tratamento de exceções: quando a página não existir,
        # mudar url, quando tiver sem conexão, etc
        req = Request(self.URL1, data=dados, headers=headers)
        try:
            with self._opener.open(req) as response:
                response: addinfourl
                raw: bytes = gzip.decompress(response.read())
                cidades_js = raw.decode('utf-8')
        except urllib.error.URLError as erro:
            print(f'Problemas com a URL: {self.URL1} -> {erro}')
            return None
        except Exception as erro:
            print(f'Erro ao obter cidades: {erro=}')
            return None
        
        # TODO: implementar tratamento de exceções 
        self._extrair_cidades(cidades_js)
        return self._cidades

    def _extrair_cidades(self, texto: str) -> list[dict]:
        """
        Extrai cidades de str contendo javascript retornado pela Caixa.
        Extrai cidades e seus códigos da chamada a url retornada em
        variáveis javascript pelo método obter_cidades. O resultado da
        extração é setado no dicionário Simulador.cidades.

        Args:
            texto (str): string contendo o retorno em javascript

        Returns:
            list[dict]: retorna uma lista de dicionários contendo as
            cidades. 
        """
        self._cidades = []

        # procurar pelo padrão:
        #  dwr.engine.remote.handleCallback("5", "0", [{
        match = re.search(self.RE_PADRAO_CIDADES, texto, re.DOTALL)

        if not match:
            print('Não encontrou padrão RE_PADRAO_CIDADES!')
            breakpoint()
            return []

        print('Encontrou padrão de array de objetos contendo cidades!')
        array_js = match.group(1)

        codigo: str = '' 
        nome: str = ''
        nome_sem_aspa: str = ''

        for linhas_obj_js in array_js.split(r'}'):
            match = re.search(self.RE_PADRAO_CIDADES_CODIGO, linhas_obj_js) 
            codigo = '' if not match else match.group(2)
            if match:
                codigo = match.group(2)
            else:
                continue

            match = re.search(self.RE_PADRAO_CIDADES_NOME, linhas_obj_js)
            nome = '' if not match else match.group(1)

            match = re.search(self.RE_PADRAO_CIDADES_SEM_ASPA, linhas_obj_js)
            nome_sem_aspa = '' if not match else match.group(1)

            self._cidades.append({
                'cod_caixa': codigo,
                'nome': nome,
                'nome_sem_aspa': nome_sem_aspa
            })


        return self._cidades

    @property
    def total_cidades(self) -> int:
        """
        Retorna quantidade de cidades.
        """
        return len(self._cidades)

    @property
    def cidades(self) -> list[dict]:
        return self._cidades

    @cidades.setter
    def cidades(self, v: list[dict]):
        """
        Cidades podem ser definidas também fora do módulo. Precisa
        atender  alguns critérios:
        - ser uma lista de dicionários;
        - ter os campos: cod_caixa, nome, nome_sem_aspa.
         """
        if type(v) is not list:
            raise ValueError('Tipo cidades precisa ser list.')

        if not v:
            raise ValueError('A lista de cidades não pode ser vazia.')

        if (
            not 'cod_caixa' in v[0] or
            not 'nome' in v[0] or
            not 'nome_sem_aspa' in v[0]
        ):
            raise ValueError(
                'Lista precisa conter pelo menos um dicionário com os campos: '
                'cod_caixa, nome, nome_sem_aspa.'
            )
        
        self._cidades = v

    def adicionar_cidade(
        self, cod_caixa: int,
        nome: str,
        nome_sem_aspa: str
    ) -> bool:
        """
        Adiciona uma cidade a lista de dicionários de cidades. Usado
        quando os valores não são obtidos da caixa, mas sim de um
        banco de dados.

        Args:
            cod_caixa (int): código de identeficaçãod a cidade pra
            CEF.
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
        """
        Verifica se existe uma cidade selecionada pelo usuário.

        Returns:
            bool: True quando existir cidade
        """
        if self.cidade_indice == -1:
            print(
                'Não foi definido um índice. É preciso obter cidades e'
                'depois pesquisar código da cidade por nome.'
            )
            return False
        else:
            return True

    def obter_opcoes_financiamento(self) -> list[OpcaoFinanciamento]:
        """
        Obtem as opções de financiamento de acordo com os dados
        passados. As opções de financiamento são retornadas numa
        lista de Enums OpcaoFinanciamento.

        Raises:
            ErroCidadeNaoSelecionada: é preciso selecionar uma cidade.
            ErroValorImovel: é preciso definir o valor do imóvel.
            ErroCPF: é preciso definir um CPF.
            ErroCelular: celular inválido ou não definido.
            ErroRendaFamiliar: renda familiar não definida ou
            inválida.
            ErroDataNascimento: data de nascimento não definida ou
            inválida.

        Returns:
            str: lista de Enums OpcaoFinanciamento com os campos versão
            de descrição preenchidos.
        """
        if not self._existe_cidade_selecionada():
            raise ErroCidadeNaoSelecionada(
                'É preciso primeiro selecionar uma cidade.'
            )
        
        cod_cidade = self._cidades[self.cidade_indice]['cod_caixa']
        cidade_sem_aspa = self._cidades[self.cidade_indice]['nome_sem_aspa']
        
        if type(cod_cidade) is not int:
            if cod_cidade and cod_cidade.isdigit():
                cod_cidade = int(cod_cidade)
            else:
                print('Não encontrou o código da cidade!')
                return []

        if not self._valor_imovel:
            raise ErroValorImovel('É preciso definir o valor do imóvel')

        if not self.cpf:
            raise ErroCPF('É preciso definir um CPF válido.')

        if not self.celular:
            raise ErroCelular('É preciso definir o celular.')

        if not self._renda_familiar:
            raise ErroRendaFamiliar(
                'É preciso definir a renda familiar bruta.'
            )

        if not self.data_nascimento:
            raise ErroDataNascimento(
                'É preciso definir a data de nascimento.'
            )

        texto_tipo_financiamento: str = 'Residencial' \
            if self._tipo_imovel == TipoImovel.RESIDENCIAL else 'Comercial'
        texto_categoria_imovel = self.tipo_financiamento.texto_categoria_imovel
        texto_cidade:str = cidade_sem_aspa
        texto_uf: str = self.uf
        tipo_imovel: int = self.tipo_imovel.value
        grupo_tipo_financiamento: int = self.tipo_financiamento.value
        valor_imovel: str = self.valor_imovel
        cpf: str = self.cpf
        celular: str = self.celular
        renda_familiar_bruta: str = self.renda_familiar
        data_nascimento: str = self.data_nascimento

        #VERSAO = config_layout.CaixaObterOpcoesFinanciamento.VERSAO
        versao: str = self._versao_atual

        headers = {
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;'
                'q=0.9,image/avif,image/webp,image/apng,*/*;'
                'q=0.8,application/signed-exchange;v=b3;q=0.7'
            ),
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/x-www-form-urlencoded',
            "User-Agent": self._user_agent,
        }

        params = {
            'versao': versao,
            'permitePlanilha': 'S',
            'vaEnquadraWS': '',
            'vaMunicipioImovelWS': '',
            'vaVlAvaliacaoWS': '',
            'vaVlRendaFamBrutaWS': '',
            'vaDtNascimentoProp1WS': '',
            'vaPossuiImovelWS': '',
            'vaContaFgtsWS': '',
            'inicioWS': '',
            'existeCpfCnpj': '',
            'textoTipoFinanciamento': texto_tipo_financiamento,
            'textoCategoriaImovel': texto_categoria_imovel,
            'textoCidade': texto_cidade,
            'textoUF': texto_uf,
            'convenio': '',
            'permiteDetalhamento': 'S',
            'nuSeqPropostaInternet': '',
            'icPerguntaFatorSocial': 'S',
            # TODO: implementar mais de um comprador
            'noPerguntaFatorSocial': (
                'Possui mais de um comprador e/ou dependente na proposta?'
            ),
            # TODO: implementar mais de um comprador
            'dePerguntaFatorSocial': (
                'Informar se possui mais de um comprador na proposta e/ou '
                'possui dependente.'
            ),
            'isVoltar': 'false',
            'isFiltrosDefault': '',
            'nomeConvenio': '',
            'codContextoCredito': 1,
            'vaNuApf': '',
            'isTipoPessoaEditavel': '',
            'vaIcTaxaCustomizada': '',
            # TODO: ehPeriodoFeirao: obter primeiro através de URL
            'ehPeriodoFeirao': 'false',
            'ehMunicipioFeirao': 'false',
            # TODO: ehMunicipioFeirao: obter primeiro através de URL
            # TODO: implementar pessoa jurídica
            'pessoa': 'F',
            'tipoImovel': tipo_imovel,
            'grupoTipoFinanciamento': grupo_tipo_financiamento, 
            'valorReforma': '',
            'valorImovel': valor_imovel,
            'uf': self.uf,
            'cidade': cod_cidade,
            'nuCpfCnpjInteressado': cpf,
            'nuTelefoneCelular': celular,
            'rendaFamiliarBruta': renda_familiar_bruta,
            'dataNascimento': data_nascimento,
        }

        if self._possui_imovel_cidade:
            params['imovelCidade'] = 'V'

        if self.tres_anos_fgts:
            params['vaContaFgts'] = 'V'

        params.update({
            #'beneficiadoFGTS': 'F',
            'dataBeneficioFGTS': '',
            'cnpjConvenio': ''
        })

        if self.mais_de_um_comprador_dependente:
            params['icFatorSocial'] = 'V'

        if (
            (not CfgCaixa.PERGUNTAR_CLIENTE_CAIXA 
             and CfgCaixa.CLIENTE_CAIXA) 
             or self.possui_relacionamento_caixa
        ):
            params['icPossuiRelacionamentoCAIXA'] = 'V'

            if self.servidor_publico:
                params['icServidorPublico'] = 'V'

        payload_str = urllib.parse.urlencode(params, encoding='latin-1')
        dados_bytes = payload_str.encode('latin-1')
        # TODO: tratamento de exceções: quando a página não existir,
        # quando  tiver sem conexão, etc
        html: str = ''
        req = Request(self.URL3, data=dados_bytes, headers=headers)

        with self._opener.open(req) as response:
            response: addinfourl
            raw: bytes = gzip.decompress(response.read())
            html = raw.decode('latin-1')

        return self._extrair_opcoes_financiamento(html)

    def _extrair_opcoes_financiamento(
        self,
        html: str
    ) -> list[OpcaoFinanciamento]:
        """
        Extrai opções de financiamento a partir do html e define uma
        lista de opções de financiamento. Em cada opção de
        financiamento é definida a versão e a descrição.

        Args:
            html (str): html passado com o resultado da chamada a URL.

        Raises:
            ErroObterOpcaoFinanciamento: não encontrou nenhuma tag li.
            ErroObterOpcaoFinanciamento: não encontrou os links com a
            opções de financiamento.
            ErroObterOpcaoFinanciamento: não encontrou os eventos
            onclick dos links a.
            ErroObterOpcaoFinanciamento: não encontrou o JS com os
            parâmetros versão e descrição.
            ErroObterOpcaoFinanciamento: não encontrou o separador no
            JS.
            ErroObterOpcaoFinanciamento: não encontrou todos os
            parâmetros.
            ErroObterOpcaoFinanciamento: não conseguiu definir todas as
            variáveis

        Returns:
            list[OpcaoFinanciamento]: lista de enums com as opções de
            financiamento.
        """

        bs = BeautifulSoup(html, "html.parser")

        lis = bs.find_all('li', attrs={'class': 'group-block-item'})
        if len(lis) == 0:
            breakpoint()
            raise ErroObterOpcaoFinanciamento(
                "Não encontrou os li's em _extrair_opcoes_financiamento."
            )

        layout_obter_opcoes_financ = \
            config_layout.CaixaObterOpcoesFinanciamento

        T_OBTER_OPCOES_FINANCIAMENTO_JS = \
            layout_obter_opcoes_financ.T_OBTER_OPCOES_FINANCIAMENTO_JS

        T_OBTER_OPCOES_FINANCIAMENTO_SEP1 = \
            layout_obter_opcoes_financ.T_OBTER_OPCOES_FINANCIAMENTO_SEP1

        OPCOES_FINANCIAMENTO_ACEITAS: list = [] 
        if not CfgCaixa.PERMITIR_TODAS_OPCOES_FINANCIAMENTO:
            OPCOES_FINANCIAMENTO_ACEITAS = (
                CfgCaixa.OPCOES_FINANCIAMENTO_ACEITAS
            )

        opcoes_financiamento: list = []
        for i in range(len(lis)):
            a = lis[i].find('a')
            if not a:
                raise ErroObterOpcaoFinanciamento(
                    'Não encontrou os links ao _extrair_opcoes_financiamento.'
                )
                
            onclick = a.get('onclick')
            if not onclick:
                raise ErroObterOpcaoFinanciamento(
                    'Não conseguiu obter os ev. onclick dos links em '
                    '_extrair_opcoes_financiamento.'
                )
            
            pos: int
            pos = onclick.find(T_OBTER_OPCOES_FINANCIAMENTO_JS)
            if pos == -1:
                raise ErroObterOpcaoFinanciamento(
                    'Não encontrou método JS ao '
                    '_extrair_opcoes_financiamento.'
                )

            pos = onclick.find(T_OBTER_OPCOES_FINANCIAMENTO_SEP1)
            if pos == -1:
                raise ErroObterOpcaoFinanciamento(
                    'Não encontroou padrão SEP1 em '
                    '_extrair_opcoes_financiamento.'
                )

            met: str = onclick[ :pos]
            
            try:
                params = met.split('\n')[1:4]
            except Exception:
                raise ErroObterOpcaoFinanciamento(
                    'Não encontrou todos os parâmetros ao '
                    '_extrair_opcoes_financiamento'
                )

            try:
                cod: str | int = params[0].strip()[ :-1]
                versao: str = params[1].strip()[ :-1]
                descricao: str = params[2].strip()[1:-1]
            except Exception:
                raise ErroObterOpcaoFinanciamento(
                    'Não conseguiu definir as variávels em '
                    '_extrair_opcoes_financiamento'
                )

            if not cod:
                raise ErroObterOpcaoFinanciamento(
                    'Não encontrou código da opção de financiamento!'
                )
            
            cod = int(cod)

            if OPCOES_FINANCIAMENTO_ACEITAS:
                if not cod in OPCOES_FINANCIAMENTO_ACEITAS:
                    print(
                        f'Opção de financiamento NÃO aceita: '
                        f'{cod}: {descricao}'
                    )
                    continue

            opcao_financiamento = OpcaoFinanciamento(cod)
            opcao_financiamento.versao = versao
            opcao_financiamento.descricao = descricao
            opcoes_financiamento.append(opcao_financiamento)

        return opcoes_financiamento

    def simular(self) -> 'SimulacaoResultadoCaixa':
        """
        Executa a simulação a partir dos atributos definidos, traz as
        informações do banco e guarda num objeto SimulacaoResultado.

        Raises:
            ErroCidadeNaoSelecionada: não foi definida uma cidade,
            primeiro é preciso buscar cidades.
            ErroTipoFinanciamento: precisa ser definido o tipo de
              imóvel.
            ErroValorImovel: valor do imóvel não definido ou abaixo do
              valor mínimo aceito.
            ErroCPF: CPF não definido ou não passou na validação.
            ErroCelular: celular não definido ou inválido.
            ErroRendaFamiliar: renda familiar não definida ou abaixo da
              renda familiar bruta mínima.
            ErroDataNascimento: data de nascimento inválida ou não
              definida.
            ErroOpcaoFinanciamentoVersao: é preciso definir uma versão
              pra OpcaoFinanciamento, obter_opcoes_financiamento.
            ErroRendaFamiliarInsuficente: acontece quando o banco recusa
              a renda familiar pra essa simulação.

        Returns:
            SimulacaoResultado: traz os dados obtidos transformados do
            HTML pra esse objeto que contém as principais informações
            da simulação.
        """
        if not self._existe_cidade_selecionada():
            raise ErroCidadeNaoSelecionada(
                'É preciso primeiro selecionar uma cidade.'
            )

        if not self._tipo_financiamento:
            raise ErroTipoFinanciamento(
                'É preciso definir o tipo de financiamento (usado, novo, '
                'reforma, etc).'
            )

        if not self._valor_imovel:
            raise ErroValorImovel('É preciso definir o valor do imóvel')

        if not self.cpf:
            raise ErroCPF('É preciso definir um CPF válido.')
        
        if not self.celular:
            raise ErroCelular('É preciso definir o celular.')
        
        if not self._renda_familiar:
            raise ErroRendaFamiliar(
                'É preciso definir a renda familiar bruta.'
            )

        if not self.data_nascimento:
            raise ErroDataNascimento(
                'É preciso definir a data de nascimento.'
            )

        if not self._opcao_financiamento.versao:
            raise ErroOpcaoFinanciamentoVersao(
                'É preciso definir uma versão para OpcaoFinanciamento. '
                'Executar Simulador.obter_opcao_financiamento.'
            )

        tipo_imovel: int = self._tipo_imovel.value
        imovel_cidade: str = 'V' if self.possui_imovel_cidade else ''
        va_conta_fgts: str = 'V' if self.tres_anos_fgts else ''
        grupo_tipo_financiamento: int = self.tipo_financiamento.value
        data_beneficio_fgts: str = ''
        #beneficiado_fgts: str = 'F'
        beneficiado_fgts: str = ''
        cod_contexto_credito = 1
        permite_detalhamento: str = 'S'
        ic_fator_social: str = \
            '' if not self.mais_de_um_comprador_dependente else 'V'

        possui_relacionamento_caixa: str = ''
        if (
            (CfgCaixa.PERGUNTAR_CLIENTE_CAIXA == False and
             CfgCaixa.CLIENTE_CAIXA) or
             self.possui_relacionamento_caixa
        ):
            possui_relacionamento_caixa = 'V'

        servidor_publico: str = 'V' if self.servidor_publico else ''
        valor_imovel: str = urllib.parse.quote(self.valor_imovel)
        renda_familiar: str = urllib.parse.quote(self.renda_familiar)
        data_nascimento: str = urllib.parse.quote_plus(self.data_nascimento)
        uf: str = self.uf
        cod_cidade = self._cidades[self.cidade_indice]['cod_caixa']
        nu_item_produto = self.opcao_financiamento.value
        versao = self._opcao_financiamento.versao
        valor_reforma = ''          # TODO: implementar?
        # TODO: verificar Itamarzim se vai vender pessoa Jurídica tb
        tipo_pessoa = 'F'
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
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Content-Type': 'text/plain',
            'Priority': 'u=1, i',
            'Referer': (
                'https://www8.caixa.gov.br/siopiinternet-web/'
                'simulaOperacaoInternet.do?method=enquadrarProdutos'
            ),
            'User-Agent': self._user_agent,
        }

        cod_sa_alt = cod_sistema_amortizacao_alterado

        param2: str
        param2 = (
            f"string:valorImovel%3D{valor_imovel}%3A"
            f"rendaFamiliarBruta%3D{renda_familiar}%3A"
            f"tipoImovel%3D{tipo_imovel}%3A"
            f"imovelCidade%3D{imovel_cidade}%3A"
            f"vaContaFgts%3D{va_conta_fgts}%3A"
            f"grupoTipoFinanciamento%3D{grupo_tipo_financiamento}%3A"
            f"dataNascimento%3D{data_nascimento}%3A"
            f"uf%3D{uf}%3A"
            f"cidade%3D{cod_cidade}%3A"
            f"nuItemProduto%3D{nu_item_produto}%3A"
            f"nuVersao%3D{versao}%3A"
            f"valorReforma%3D{valor_reforma}%3A"
            f"codigoSeguradoraSelecionada%3Dundefined%3A"
            f"nomeSeguradora%3Dundefined%3A"
            f"dataBeneficioFGTS%3D{data_beneficio_fgts}%3A"
            f"beneficiadoFGTS%3D{beneficiado_fgts}%3A"
            f"codContextoCredito%3D{cod_contexto_credito}%3A"
            f"complementouDadosSubsidio%3D{complementou_dados_subsidio}%3A"
            f"pessoa%3D{tipo_pessoa}%3A"
            f"convenio%3D%3A"
            f"nuEmpresa%3D%3A"
            f"nuSeqPropostaInternet%3D%3A"
            f"permiteDetalhamento%3D{permite_detalhamento}%3A"
            f"codSistemaAmortizacaoAlterado%3D{cod_sa_alt}%3A"
            f"nuCpfCnpjInteressado%3D{cpf}%3A"
            f"icFatorSocial%3D{ic_fator_social}%3A"
            f"icPossuiRelacionamentoCAIXA%3D{possui_relacionamento_caixa}%3A"
            f"icServidorPublico%3D{servidor_publico}%3A"
            f"icContaSalarioCAIXA%3D%3A"
            f"icPortabilidadeCreditoImobiliario%3D%3A"
            f"vaNuApf%3D%3A"
            f"nuTelefoneCelular%3D{celular}%3A"
            f"icArmazenamentoDadoCliente%3D%3A"
            f"vaIcTaxaCustomizada%3D"
        )

        if valor_entrada:
            param2 += (
                f"%3Aprazo%3D{prazo}%3A"
                f"recursosProprios%3D{valor_entrada}"
            )

        if prestacao_max:
            param2 += f"%3AprestacaoMaxDesejada%3D{prestacao_max}"

        params = {
            'callCount': 1,
            'nextReverseAjaxIndex': 0,
            'c0-scriptName': 'SIOPIAjaxFrontController',
            'c0-methodName': 'callActionForwardMethodDiv',
            'c0-id': 0,
            'c0-param0': 'string:%2FsimulaOperacaoInternet',
            'c0-param1': 'string:simularOperacaoImobiliariaInternet',
            'c0-param2': f'{param2}',
            'c0-param3': 'string:resultadoSimulacao',
            'batchId': 0,
            'instanceId': 0,
            'page': (
                '%2Fsiopiinternet-web%2FsimulaOperacaoInternet.do%3F"method%3D'
                'enquadrarProdutos'
            ),
            # 'httpSessionId': (
            #     'LxaBwu1OVnyP1Sm6KPSANsgJ.habitacao_dbrnpapllx016:siopi-'
            #     'internet-prd-node02_lx016'
            # ),
            'scriptSessionId': self._script_session_id
        }

        dados = urllib.parse.urlencode(params).encode('latin-1')
        req = Request(self.URL4, dados, headers)
        simulacao_raw: str = ''

        # TODO: tratamento de exceções: quando a página não existir,
        # quando tiver sem conexão, etc
        with self._opener.open(req) as response:
            response: addinfourl
            raw: bytes = gzip.decompress(response.read())
            simulacao_raw: str = raw.decode('utf-8')
        
        html = self._extrair_html_sim(simulacao_raw)
        sim_resultado = SimulacaoResultadoCaixa()

        try:
            sim_resultado.extrair_dados(html)
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
        
        match = re.search(self.RE_RESULTADO_SIMULACAO, simulacao_raw)
        if not match:
            raise Exception(
                'Padrão HTML Resultado da Simulacao NÃO encontrado!'
            )
        
        html = match.group(1)

        if not html:
            print('Não encontrou html no resultado da simulação!')
            return ''
        
        return html

    def procurar(self, s: str, l: list, max_res: int = 10) -> list[str]:
        """
        Procurar texto por similaridade em uma lista. Se for texto 
        identico retorna apenas um item, caso contrário retorna uma
        lista de str.

        Args:
            s (str): string contendo parte ou o nome da string a ser
              procurada.
            l (list): lista contendo todos os itens.
            max_res (int, optional): corresponde ao número máximo de
              resultados a serem trazidos na pesquisa. Defaults to 10.

        Returns:
            list: cada item da lista corresponde a uma str, se for s
              identico ao da lista retorna apenas um item.
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

    def procurar2(
        self,
        q: str,
        l: list[tuple],
        key: int=2,
        max_res: int=10
    ) -> list[dict]:
        """
        Procurar texto por similaridade em uma lista. Se for texto 
        identico retorna apenas um item, caso contrário retorna uma
        lista de dicionários com os campos como na propriedade cidades.

        Args:
            q (str): string contendo parte ou o nome da string a ser
              procurada.
            l (list): lista de tuplas contendo todos os itens separados
              por campos.
            key (int): chave da tuple que vai ser pesquisada.
            max_res (int, optional): corresponde ao número máximo de
              resultados a serem trazidos na pesquisa. Defaults to 10.

        Returns:
            list: cada item da lista corresponde a uma str, se for s
              identico ao da lista retorna apenas um item.
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
        """
        Extrai apenas os nomes da lista de dicionários de cidades.

        Returns:
            list: lista com todas as cidades.
        """
        if len(self._cidades) == 0:
            print('Favor obter cidades antes de converter pra lista.')
            return []

        return [d['nome'] for d in self._cidades]

    def obter_cod_cidade_por_nome(self, cidade: str) -> int:
        """
        Obtém código da cidade através do nome exato. Também
        armazena o índice da lista de cidades em
        Simulador.cidade_indice.

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


class SimulacaoResultadoCaixa(SimulacaoResultadoBase):
    _prazo_max: int = 0
    _cota_max: int = 0
    _valor_entrada: Decimal2 = Decimal2('0')
    _subsidio_casa_verde_amarela: Decimal2 = Decimal2('0')
    _prestacao_max: str = ''

    # extração de dados pra fazer a alteração do sistema de
    # amortização através do simulador
    _cods_sistema_amortizacao: dict[str, str] = {}
    _sistema_amortizacao_chave_sel: str = ''
    _msg_erro: str = ''

    _largura_tracejado: int = Parametros.TAM_TRACEJADO
    _exibir_obs_sistema_amortizacao: bool = \
        CfgCaixa.ObservacaoSistemaAmortizacao.EXIBIR_OBS_SISTEMA_AMORTIZACAO

    def __init__(self,):
        super().__init__()

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

    @property
    def cods_sistema_amortizacao(self) -> dict[str, str]:
        """
        Obtem todos os códigos de sistema de amortização disponíveis
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

    def _setar_prestacao_max(self, bs) -> None:
        div_res = bs.find('input', attrs={'name': 'prestacaoMaxDesejada'})
        if not div_res:
            return
        self._prestacao_max = div_res['value']

    def _setar_cods_sistema_amortizacao(self, el_select: bs4.element.Tag):
        """
        Seta dicionário com as taxas de amortização, a key é o
        texto, value é o código da taxa.

        Args:
            el_select (bs4.element.Tag): elemento select de onde serão
            extraídos os valores.

        Returns:
            None: sem retorno.
        """
        if not el_select:
            # TODO: implementar log e alerta ao desenvolvedor
            print('#' * 50)
            print(
                'Elemento select com taxas de amortização NÃO encontrado.'
            )
            print('#' * 50)
            return {}

        el_option: bs4.element.Tag
        el_option_selected: bs4.element.Tag | NavigableString  | None = ( 
            el_select.find(
                'option', {'selected': 'selected'}
        ))
        el_options: bs4.element.ResultSet = el_select.findChildren('option')

        for el_option in el_options:
            self._cods_sistema_amortizacao[el_option.text] = \
                str(el_option['value'])

            if el_option == el_option_selected:
                self._sistema_amortizacao_chave_sel = el_option.text

    def extrair_dados(self, html_str: str) -> bool:
        """
        Extrai dados, valor do imóvel, prazos, cota, valor de entrada,
        subsídio, etc. Seta essas informações como atributos. Obtém
        dados da primeira e segunda tabelas, na primeira existem os
        dados do financiamento.

        Args:
            html_str (str): html contendo a tabela e os campos a serem extraídos.

        Returns:
            bool: retorna True quando extração for um sucesso.        
        """
        self.msg_erro = ''

        # decodificar as entidades html pra evitar conteúdo com escapes
        # remove barra invertida do fechamento de tags
        html_str = re.sub(r'\\/', '/', html_str)

        # resolve escapes (como \n, \t, \r)
        # usamos 'latin-1' no encode para preservar caracteres
        # acentuados durante o processo
        try:
            html_str = html_str.encode('latin-1').decode('unicode_escape')
        except UnicodeEncodeError:
            # Fallback caso a string contenha caracteres não-latin1
            html_str = html_str.encode('utf-8').decode('unicode_escape')        

        bs = BeautifulSoup(html_str, 'html.parser')

        self._setar_prestacao_max(bs)

        titulo = bs.find('h3', attrs={'class': 'simulation-result-title zeta'})
        if titulo:
            #self.titulo = ajustar_unicode_esc_char(titulo.text.strip())
            self.titulo = titulo.text.strip()

        tables = bs.find_all('table', attrs={'class': 'simple-table'})
        num_tables = len(tables)

        RENDA_INSUFICIENTE_FINAL = MsgsCaixa.RENDA_INSUFICIENTE_FINAL
        VALOR_FINANCIAMENTO_INFERIOR = MsgsCaixa.VALOR_FINANCIAMENTO_INFERIOR
        VALOR_FINANCIAMENTO_INFERIOR2 = MsgsCaixa.VALOR_FINANCIAMENTO_INFERIOR2

        if num_tables < 2:
            #print('Não encontrou nenhuma tabela no resultado da simulação!')
            # sem resultado de simulação, certamente msg de erro
            div_erro = bs.find('div', attrs={'class': 'erro_feedback'})

            if div_erro:
                self.msg_erro = (
                    div_erro.text.strip()
                    .encode('latin-1')
                    .decode('unicode_escape')
                )
                
                if self.msg_erro.endswith(RENDA_INSUFICIENTE_FINAL.value):
                    raise ErroRendaFamiliarInsuficente(self.msg_erro)
                elif self.msg_erro == VALOR_FINANCIAMENTO_INFERIOR.value:
                    raise ErroValorFinanciamentoInferior(self.msg_erro)
                elif self.msg_erro == VALOR_FINANCIAMENTO_INFERIOR2.value:
                    raise ErroValorFinanciamentoInferior2(self.msg_erro)

            return False

        SIMULACAO_RESULTADO_CAIXA_CAMPOS = \
            config_layout.CaixaResultado.SIMULACAO_RESULTADO_CAIXA_CAMPOS
        
        TXT_SISTEMA_AMORTIZACAO_INI = \
            config_layout.CaixaResultado.TXT_SISTEMA_AMORTIZACAO_INI

        TXT_SUBSIDIO_CASA_VERDE_AMARELA_INI = config_layout.CaixaResultado.TXT_SUBSIDIO_CASA_VERDE_AMARELA_INI

        trs = tables[0].find_all('tr')
        if not trs:
            print(
                'Não encontrou linhas da tabela com o resultado da simulação!'
            )
            return False

        retirar_espacos_multiplos = lambda s : re.sub(r'\s+', ' ', s)
        get_desc = lambda : retirar_espacos_multiplos(tds[0].text.strip())
        get_valor = lambda : retirar_espacos_multiplos(tds[1].text.strip())

        campo: str = ''

        # seta campos (setattr) de acordo como o mapeamento:
        # SIMULACAO_RESULTADO_CAIXA_CAMPOS
        for i in range(0, len(trs)):
            tds = trs[i].find_all('td')

            descricao: str = get_desc()
            valor: str = get_valor()

            if descricao in SIMULACAO_RESULTADO_CAIXA_CAMPOS:
                campo = SIMULACAO_RESULTADO_CAIXA_CAMPOS[descricao]
                setattr(self, campo, valor)
            elif descricao.startswith(TXT_SUBSIDIO_CASA_VERDE_AMARELA_INI):
                self.subsidio_casa_verde_amarela = valor
            elif descricao.startswith(TXT_SISTEMA_AMORTIZACAO_INI):
                self.sistema_amortizacao = valor
        
        # extrair primeira e última prestações
        # TODO: substituir prints abaixo por raise
        trs = tables[2].find_all('tr')
        if not trs:
            print('Não encontrou nenhuma linha das prestações.')
            return False

        I_LINHA_ULT_PREST = config_layout.CaixaResultado.ULTIMA_PRESTACAO[0]
        if len(trs) < I_LINHA_ULT_PREST:
            print('Não encontrou linhas das prestações.')
            return False

        I_LINHA_PRIM_PREST = config_layout.CaixaResultado.PRIMEIRA_PRESTACAO[0]
        tds = trs[I_LINHA_PRIM_PREST].findChildren('td')
        if not tds:
            print('Não encontrou células da primeira prestação.')
            return False

        def get_valor2(c):
            valores = [
                s for s in 
                c.text.replace('\r', '').replace('\t', '').split('\n') if s
            ]
            #valores = html_str.encode('utf-8').decode('unicode_escape')        
            if len(valores) >= 2:
                return ' '.join(valores[0:2])
            return ''

        T_PRIM_PREST = config_layout.CaixaResultado.PRIMEIRA_PRESTACAO[1]

        if tds[0].text.strip() == T_PRIM_PREST:
            center = tds[1].find("center")
            if not center:
                print('Não encontrou center onde tá o valor da prestação.')
                return False

            valor = get_valor2(center)
            # TODO: NÃO É MAIS NECESSÁRIO (ver abaixo): disparar
            # alerta quando retornar "." e mais de duas casas decimais
            pos_ponto, pos_virg = valor.rfind('.'), valor.rfind(',')

            if pos_virg < pos_ponto:
                if pos_ponto < len(valor) - 3:
                    raise ErroValorPrimeiraPrestacao(valor)
                else:
                    # CORRIGIDO: retornava certamente por conta das 
                    # headers q não tavam definidas
                    valor = Decimal2.a_partir_de_valor(valor).formatar_moeda()
            self.primeira_prestacao = valor

        tds = trs[I_LINHA_ULT_PREST].findChildren('td')

        if not tds:
            print('Não encontrou células da última prestação.')
            return False

        T_ULT_PREST = config_layout.CaixaResultado.ULTIMA_PRESTACAO[1]

        if tds[0].text.strip() == T_ULT_PREST:
            center = tds[1].find('center')
            if not center:
                print(
                    'Não encontrou center onde tá o valor da última '
                    'prestação.'
                )
                return False

            valor = get_valor2(center)    
            self.ultima_prestacao = valor

        el_select = el_select = bs.find(
            'select', attrs={'id': 'codSistemaAmortizacaoAlterado'}
        )
        if isinstance(el_select, Tag):
            self._setar_cods_sistema_amortizacao(el_select)
        else:
            raise Exception(
                'Não é possível setar códigos amortização, '
                'el_select precisa ser do tipo Tag' 
            )

        return True

    def __str__(self) -> str:

        s = self
        # negrito abertura (n) e fechamento (nf)
        na: str = self._negrito_abertura
        nf: str = self._negrito_fechamento

        txt: str = (
            f'{na}{s.titulo}{nf}\n'
            f'{"-" * self._largura_tracejado}\n'
            f'{na}Valor do imóvel:{nf} {s.valor_imovel}\n'
            f'{na}Prazo máximo:{nf} {s.prazo_max}\n'
            f'{na}Prazo escolhido:{nf} {s.prazo}\n'
            f'{na}Cota máxima financiamento:{nf} {s.cota_max}\n'
            f'{na}Valor da entrada:{nf} {s.valor_entrada}\n'
        )

        if self._subsidio_casa_verde_amarela:
            txt += (
                f'{na}Subsídio Casa Verde e Amarela{nf}: '
                f'{s.subsidio_casa_verde_amarela}\n'
            )

        txt += (
            f'{na}Valor do financiamento:{nf} {s.valor_financiamento}\n'
            f'{na}Sistema de amortização:{nf} {s.sistema_amortizacao}\n'
            '\n'
            f'{na}Primeira prestação:{nf} {s.primeira_prestacao}\n'
            f'{na}Última prestação:{nf} {s.ultima_prestacao}\n'
        )

        if self._exibir_obs_sistema_amortizacao:
            obs: str = ''

            if s.sistema_amortizacao.startswith('SAC'):
                obs = (
                    CfgCaixa.ObservacaoSistemaAmortizacao
                    .OBS_SISTEMA_AMORTIZACAO_SAC
                )
            elif s.sistema_amortizacao.startswith('PRICE'):
                obs = (
                    CfgCaixa.ObservacaoSistemaAmortizacao
                    .OBS_SISTEMA_AMORTIZACAO_PRICE
                )

            if obs:
                txt += (
                    f'{"-" * self._largura_tracejado}\n'
                    f'{obs}\n'
                )

        return txt


def test1():
    print('#' * 100)
    print('>> Simulação Caixa a partir do nome da cidade.')
    sim_caixa = SimuladorCaixa.a_partir_nome_cidade(
        nome_cidade='ITABERAI',
        tipo_financiamento=TipoFinanciamento.CONSTRUCAO,
        valor_imovel='140.000,00',
        cpf='857.121.060-86',
        celular='62998758239',
        renda_familiar=Decimal2(2600),
        data_nasc='08/10/1988',
        tres_anos_fgts=True,
        mais_de_um_comprador_dependente=True
    )
    
    opcoes_financ: list[OpcaoFinanciamento]
    opcoes_financ = sim_caixa.obter_opcoes_financiamento()
    opcao_financ: OpcaoFinanciamento
    print('>> Listando opções de financiamento...')
    for opcao_financ in opcoes_financ:
        print(f'{opcao_financ.descricao=}')
    print('>> Pegar última opção de financiamento:')
    i: int = len(opcoes_financ) - 1
    opcao_financ = OpcaoFinanciamento(opcoes_financ[i].value)
    opcao_financ.versao = opcoes_financ[i].versao
    opcao_financ.descricao = opcoes_financ[i].descricao
    print(f'{opcao_financ.descricao=}')
    sim_caixa.opcao_financiamento = opcao_financ
    
    sim_resultado: SimulacaoResultadoCaixa = sim_caixa.simular()
    print(sim_resultado)


if __name__ == '__main__':
    test1()
