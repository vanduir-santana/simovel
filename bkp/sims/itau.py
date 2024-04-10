#!/usr/bin/env python
# coding: utf-8
"""Simulador de Crédito Imobiliário Bradesco
"""

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.9'


from datetime import date
from enum import Enum
from types import ClassMethodDescriptorType
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException
from sims.base import UFS, Banco, SimuladorBase, SimulacaoResultadoBase, TipoResultado
from util import Cpf, Decimal2, Fone, email_valido
from exc import ErroEmail, ErroNomeCurto, ErroResultadoSimulacao, ErroTipoImovel, ErroValorEntrada, ErroValorEntradaAcimaPermitido
from selenium.webdriver.common.keys import Keys

from time import sleep


class TipoImovel(Enum):
    RESIDENCIAL = 'RESIDENCIAL'
    COMERCIAL = 'COMERCIAL'


class SimuladorItauBase(SimuladorBase):
    """Base para outas classes do simulador de crédito imobiliário Itaú.
    """

    def __init__(self):
        super().__init__(Banco.ITAU)

        self._nome: str = ''
        self._email: str = ''
        #self._tipo_imovel: TipoImovel = TipoImovel.RESIDENCIAL

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
        
        if d2 >= self._valor_imovel:
            raise ErroValorEntradaAcimaPermitido(
                'Valor da entrada não pode ser igual ou acima do valor do imóvel.'
                )
        self._valor_entrada = d2


class SimuladorItauL(SimuladorItauBase):
    """Implementação simulador de crédito imobiliário Itaú baseado na API
    do sistema Loft.
    """

    URL = 'https://credit-bff.loft.com.br/mortgage-simulation/potential_with_bank_rates'

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def a_partir_de_dados_financiamento(cls, nome: str, 
            email: str, valor_imovel: str | Decimal2, 
            valor_entrada: str | Decimal2, 
            data_nascimento: str, 
            prazo: int,
            renda_familiar: str | Decimal2
        ) -> 'SimuladorItauL':

        sim_itau_l: SimuladorItauL = cls()
        sim_itau_l.nome = nome
        sim_itau_l.email = email
        sim_itau_l.valor_imovel = valor_imovel
        sim_itau_l.valor_entrada = valor_entrada
        sim_itau_l.data_nascimento = data_nascimento
        sim_itau_l.prazo = prazo
        sim_itau_l.renda_familiar = renda_familiar

        return sim_itau_l

    def _obter_headers(self) -> dict:
        return {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            #'Content-Length': 296,
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

    def simular(self) -> 'SimulacaoResultadoItau':
        headers: dict = self._obter_headers()
        payload: dict = self._obter_payload()

        r = requests.post(self.URL, json=payload, headers=headers)
        json: dict = r.json()
        if not json:
            raise ErroResultadoSimulacao('Resultado da simulação vazio.')
        d_itau: dict = json['banksSimulation'][2]
        if d_itau['bankProvider'] != 'Itaú':
            d_banco: dict
            for d_banco in json['banksSimulation']:
                if d_banco['bankProvider'] == 'Itaú':
                    d_itau = d_banco
                    break
            else:
                raise ErroResultadoSimulacao('Não encontrou o banco no resultado da simulação.')
        return SimulacaoResultadoItau.a_partir_de_valores_l(d_itau['simulation'])


class SimuladorItau(SimuladorItauBase):
    URL = 'https://credito-imobiliario.itau.com.br/'

    def __init__(self) -> None:
        super().__init__()

        self._tipo_imovel: TipoImovel = TipoImovel.RESIDENCIAL

        # selenium
        self._chrome_options = None
        self._service = None

    @classmethod
    def a_partir_de_dados_financiamento(cls, cpf: str | Cpf, nome: str, 
            email: str, celular: str | Fone, tipo_imovel: TipoImovel, 
            valor_imovel: str | Decimal2, valor_entrada: str | Decimal2, 
            data_nascimento: str | date, prazo: int
        ) -> 'SimuladorItau':

        sim_itau: SimuladorItau = cls()
        sim_itau.cpf = cpf
        sim_itau.nome = nome
        sim_itau.email = email
        sim_itau.celular = celular
        sim_itau.tipo_imovel = tipo_imovel
        sim_itau.valor_imovel = valor_imovel
        sim_itau.valor_entrada = valor_entrada
        sim_itau.data_nascimento = data_nascimento
        sim_itau.prazo = prazo

        cls._setar_opcoes_navegador()

        return sim_itau    

    @property
    def tipo_imovel(self) -> TipoImovel:
        return self._tipo_imovel

    @tipo_imovel.setter
    def tipo_imovel(self, v: TipoImovel):
        if type(v) is not TipoImovel:
            raise ErroTipoImovel('Tipo imóvel inválido.')
        self._tipo_imovel = v

    def _setar_opcoes_navegador(self):
        self._service = Service(ChromeDriverManager().install())

        self._chrome_options = Options()
        self._chrome_options.headless = True
        # performance: desabilitar carregamento imagens
        #self._chrome_options.experimental_options["prefs"] = {
	    #    "profile.managed_default_content_settings.images": 2
        #} 
        self._chrome_options.add_argument('--disable-gpu')
        self._chrome_options.add_argument('--disable-dev-shm-usage')
        self._chrome_options.add_argument("--incognito")

    def simular(self) -> 'SimulacaoResultadoItau':
        with webdriver.Chrome(
                service=self._service, options=self._chrome_options
            ) as driver:
            driver.get(self.URL)

            print(f'{driver.current_url=}')
            print(f'{driver.title=}')

            print('Preenchendo formulário #1')
            input_cpf = driver.find_element(
                by=By.CSS_SELECTOR, value='input#cpf'
            )
            input_cpf.clear()
            input_cpf.send_keys(self.cpf)

            input_cpf.submit()


            print('Preenchendo formulário #2')
            input_nome: WebElement = WebDriverWait(driver, timeout=5).until(
                lambda d: d.find_element(
                    by=By.CSS_SELECTOR, value='input#proponent_name'
                )
            )
            input_nome.send_keys(self.nome)

            input_email = driver.find_element(
                by=By.CSS_SELECTOR, value='input#proponent_email'
            )
            input_email.send_keys(self.email)

            input_celular = driver.find_element(
                by=By.CSS_SELECTOR, value='input#proponent_phone'
            )
            input_celular.send_keys(self.celular)

            # testes
            # softlead-simulation
            #driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            input_celular.submit()
            sleep(5)
            driver.save_screenshot('screenshot.png')

            for i in range(1, 4):
                print(f'Aguardando carregamento formulário #3. Tentaiva {i}...')
                try:
                    select_tipo_imovel = WebDriverWait(driver, timeout=20).until(
                        lambda d: d.find_element(
                            by=By.CSS_SELECTOR, value='select#property_type'
                        )
                    )
                    break
                except TimeoutException as erro:
                    # TODO: log
                    #print('Erro ao aguardar carregamento do formulário #3.', erro)
                    print('Erro ao aguardar carregamento do formulário #3.')
            else:
                # TODO: log
                print('Não carregou formulário #3!')
                return None

            print('Preenchendo formulário #3...')
            select = Select(select_tipo_imovel)
            select.select_by_value(self.tipo_imovel.value)

            input_valor_imovel = driver.find_element(
                by=By.CSS_SELECTOR, value='input#property_value'
            )
            input_valor_imovel.send_keys(self.valor_imovel)

            input_valor_entrada = driver.find_element(
                by=By.CSS_SELECTOR, value='input#input_value'
            )
            input_valor_entrada.send_keys(self.valor_entrada)

            input_data_nasc = driver.find_element(
                by=By.CSS_SELECTOR, value='input#birthdate'
            )
            input_data_nasc.send_keys(self.data_nascimento)

            input_prazo = driver.find_element(
                by=By.CSS_SELECTOR, value='input#financing_term'
            )
            input_prazo.send_keys(self.prazo)

            label_input_seguradora_itau = driver.find_element(
                by=By.XPATH, value="//label[@for='insurer-ITAU']"
            )
            label_input_seguradora_itau.click()

            input_prazo.submit()
            driver.save_screenshot('screenshot2.png')
            print('Aguardando resultado da simulação...')
            h2_resultado = WebDriverWait(driver, timeout=20).until(
                lambda d: d.find_element(
                    by=By.CSS_SELECTOR, 
                    value='form#simulation-result div.simulation-result-container div.form-container h2'
                )
            )

            if h2_resultado.text.lower() != 'resultado da simulação':
                # TODO: disparar erro?
                print('Não encontrou resultado da simulação')
                return False
            
            divs_result = driver.find_elements(
                by=By.CSS_SELECTOR, 
                value='li#data-result-0 div.item-body div.detail'
            )

            ps_primeira_parcela = divs_result[1].find_elements(
                by=By.TAG_NAME, value='p'
            )
            ps_ultima_parcela = divs_result[2].find_elements(
                by=By.TAG_NAME, value='p'
            )
            ps_taxa_juros = divs_result[3].find_elements(
                by=By.TAG_NAME, value='p')
            ps_cet = divs_result[4].find_elements(by=By.TAG_NAME, value='p')
            ps_somatorio_parcelas = divs_result[5].find_elements(
                by=By.TAG_NAME, value='p'
            )

            # clicar botão pra exibir div extra
            button_mais_possibilidades = driver.find_element(
                by=By.CSS_SELECTOR, 
                value='li#data-result-0 div.item-control button'
            )
            button_mais_possibilidades.click()

            divs_result_extra0 = driver.find_elements(
                by=By.CSS_SELECTOR, 
                value='li#data-result-0 div.item-extra'
            )[0].find_elements(by=By.CSS_SELECTOR, value='div.detail')

            ps_total_financiado = divs_result_extra0[0].find_elements(
                by=By.TAG_NAME, value='p'
            )
            ps_cesh = divs_result_extra0[1].find_elements(
                by=By.TAG_NAME, value='p'
            )

            # definir dados (itens)
            return SimulacaoResultadoItau.a_partir_de_p(
                l=[
                    ps_primeira_parcela, 
                    ps_ultima_parcela, 
                    ps_taxa_juros,
                    ps_cet, 
                    ps_somatorio_parcelas, 
                    ps_total_financiado, 
                    ps_cesh,
                ]
            )


class SimulacaoResultadoItau(SimulacaoResultadoBase):
    def __init__(self, primeira_parcela: 'SimulacaoResultadoItemItau', 
            ultima_parcela: 'SimulacaoResultadoItemItau', 
            taxa_juros: 'SimulacaoResultadoItemItau',
            cet: 'SimulacaoResultadoItemItau', 
            somatorio_parcelas: 'SimulacaoResultadoItemItau', 
            total_financiado: 'SimulacaoResultadoItemItau',
            cesh: 'SimulacaoResultadoItemItau') -> None:
        
        super().__init__()
    
        self.primeira_parcela = primeira_parcela
        self.ultima_parcela = ultima_parcela
        self.taxa_juros = taxa_juros
        
        cet.descricao = cet.descricao.replace('\n', ' ')
        self.cet = cet

        self.somatorio_parcelas = somatorio_parcelas
        self.total_financiado = total_financiado
        self.cesh = cesh

    @classmethod
    def a_partir_de_valores_l(cls, v: dict) -> 'SimulacaoResultadoItau':
        """Retorna um objeto a partir dos valores do resultado da API do
        Loft.

        Args:
            v (dict): dict contendo os campos a serem extraídos.

        Returns:
            SimulacaoResultadoItau: retorna objeto com simulação.
        """
        primeira_parcela = SimulacaoResultadoItemItau(
            'Primeira parcela', v['firstPaymentValue']
        )
        ultima_parcela: 'SimulacaoResultadoItemItau', 
        taxa_juros: 'SimulacaoResultadoItemItau',
        cet: 'SimulacaoResultadoItemItau', 
        somatorio_parcelas: 'SimulacaoResultadoItemItau', 
        total_financiado: 'SimulacaoResultadoItemItau',
        cesh: 'SimulacaoResultadoItemItau'        

    @classmethod
    def a_partir_de_p(cls, l: list[list[WebElement]]):
        """Inicia a partir dos parágrafos do selenium contendo uma lista
        com dois itens: descrição e valor.
        """
        l_itens_res: list['SimulacaoResultadoItemItau'] = [        
            SimulacaoResultadoItemItau(
                descricao=i[0].text,
                valor=i[1].text
            )
            for i in l
        ]
        return cls(*l_itens_res)

    def __str__(self):
        s = self
        return (
            'Resultado da Simulação Itaú\n'
            '-----------------------------------\n'
            f'{s.primeira_parcela.descricao}: {s.primeira_parcela.valor}\n'
            f'{s.ultima_parcela.descricao}: {s.ultima_parcela.valor}\n'
            f'{s.taxa_juros.descricao}: {s.taxa_juros.valor}\n'
            f'{s.cet.descricao}: {s.cet.valor}\n'
            f'{s.somatorio_parcelas.descricao}: {s.somatorio_parcelas.valor}\n'
            f'{s.total_financiado.descricao}: {s.total_financiado.valor}\n'
            f'{s.cesh.descricao}: {s.cesh.valor}'
        )


class SimulacaoResultadoItemItau:
    def __init__(self, descricao: str, valor: str):
        self.descricao = descricao
        self.valor = valor


def test1() -> bool:
    cpf: str = '02328269192'
    nome: str = 'Blase Pascal'
    email: str = 'blasep318@gmail.com'
    celular: str = '62998757234'
    tipo_imovel: TipoImovel = TipoImovel.RESIDENCIAL
    valor_imovel: str = '200000'
    valor_entrada: str = '40000'
    data_nascimento: str = '03/04/1996'
    #prazo_financiamento: str = '30 anos'
    prazo_financiamento: int = 30

    sim_itau = SimuladorItau.a_partir_de_dados_financiamento(
        cpf, nome, email, celular, tipo_imovel, valor_imovel, valor_entrada,
        data_nascimento, prazo_financiamento
    )
    sim_resultado: SimulacaoResultadoItau = sim_itau.simular()

    print()
    print(sim_resultado)   
    return True 


def test2() -> bool:
    nome: str = 'Blase Pascal'
    email: str = 'blasep318@gmail.com'
    #celular: str = '62998757234'
    #tipo_imovel: TipoImovel = TipoImovel.RESIDENCIAL
    valor_imovel: str = '200000'
    valor_entrada: str = '40000'
    data_nascimento: str = '03/04/1996'
    prazo: int = 30
    renda_familiar: str = '6422'

    sim_itau = SimuladorItauL.a_partir_de_dados_financiamento(
        nome, email, valor_imovel, valor_entrada,
        data_nascimento, prazo, renda_familiar
    )
    sim_resultado: SimulacaoResultadoItau = sim_itau.simular()

    print()
    print(sim_resultado)   
    return True 


if __name__ == '__main__':
    import locale
    locale.setlocale(locale.LC_MONETARY, 'pt_BR.utf8')

    test2()
