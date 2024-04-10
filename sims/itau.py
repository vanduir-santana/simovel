#!/usr/bin/env python
# coding: utf-8
"""Simulador de Crédito Imobiliário Itaú
"""

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.9'


from datetime import date
from enum import Enum
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException
from sims.base import Banco, SimuladorBase, SimulacaoResultadoBase
from sims.base import SimuladorBaseL
from util import Cpf, Decimal2, Fone
from exc import ErroResultadoSimulacao, ErroTipoImovel
from selenium.webdriver.common.keys import Keys
from time import sleep
from config.geral import Parametros


class TipoImovel(Enum):
    RESIDENCIAL = 'RESIDENCIAL'
    COMERCIAL = 'COMERCIAL'


TITULO = 'Resultado da Simulação Itaú'
#TITULO_01 = 'Resultado da Simulação Itaú L'
TITULO_01 = TITULO
#TITULO_02 = 'Resultado da Simulação Itaú S'
TITULO_02 = TITULO


class SimuladorItauL(SimuladorBaseL):
    """Implementação simulador de crédito imobiliário Itaú baseado na API
    do sistema Loft.
    """
    def __init__(self, nome: str, email: str, 
            valor_imovel: str | Decimal2, valor_entrada: str | Decimal2,
            data_nascimento: str, prazo: int, 
            renda_familiar: str | Decimal2) -> None:
        
        super().__init__(
            Banco.ITAU_L, nome, email, valor_imovel, valor_entrada,
            data_nascimento, prazo, renda_familiar
        )

    def simular(self) -> 'SimulacaoResultadoItau':
        """Executa simulação e extrai resultado.

        Raises:
            ErroResultadoSimulacao: erro ao extrari resultado da simulação.

        Returns:
            SimulacaoResultadoItau: resultado da simulação Itaú.
        """
        try:
            resultados: list = self._extrair_simulacao()
        except ErroResultadoSimulacao:
            raise
        res_itau: dict = resultados[0]['simulation']
        return SimulacaoResultadoItau.a_partir_de_valores_l(
            self,
            TITULO_01,
            res_itau
        )


class SimuladorItauS(SimuladorBase):
    """Simulador crédito imobiliário Itaú baseado no Selenium."""
    URL = 'https://credito-imobiliario.itau.com.br/'

    def __init__(self) -> None:
        super().__init__(Banco.ITAU)

        self._tipo_imovel: TipoImovel = TipoImovel.RESIDENCIAL

        # selenium
        self._chrome_options = None
        self._service = None

    @classmethod
    def a_partir_de_dados_financiamento(cls, cpf: str | Cpf, nome: str, 
            email: str, celular: str | Fone, tipo_imovel: TipoImovel, 
            valor_imovel: str | Decimal2, valor_entrada: str | Decimal2, 
            data_nascimento: str | date, prazo: int
        ) -> 'SimuladorItauS':

        sim_itau: SimuladorItauS = cls()
        sim_itau.cpf = cpf
        sim_itau.nome = nome
        sim_itau.email = email
        sim_itau.celular = celular
        sim_itau.tipo_imovel = tipo_imovel
        sim_itau.valor_imovel = valor_imovel
        sim_itau.valor_entrada = valor_entrada
        sim_itau.data_nascimento = data_nascimento
        sim_itau.prazo = prazo

        sim_itau._setar_opcoes_navegador()

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
        self._chrome_options.add_argument('--incognito')

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
            #driver.save_screenshot('screenshot.png')

            for i in range(1, 4):
                print(f'Aguardando carregamento formulário #3. Tentativa {i}...')
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
            #driver.save_screenshot('screenshot2.png')
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
                self,
                TITULO_02,
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
    _cet: Decimal2 = ''
    _cesh: Decimal2 = ''

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def a_partir_de_p(cls, obj_simulador: SimuladorBase, titulo: str,
                                            l: list[list[WebElement]]):
        """Inicia a partir dos parágrafos do selenium contendo uma lista
        com dois itens: descrição e valor.
        """
        l_itens_res: list = [i[1].text for i in l]

        sri: SimulacaoResultadoItau = cls()
        sri.obj_simulador = obj_simulador
        sri.titulo = titulo

        sri.primeira_parcela, \
        sri.ultima_parcela, \
        sri.taxa_juros, \
        sri.cet, \
        sri.somatorio_parcelas,\
        sri.total_financiado, \
        sri.cesh = l_itens_res

        return sri

    @property
    def cet(self) -> str:
        """Custo Efetivo Total."""
        return '' if not self._cet else f'{self._cet.formatar_moeda(True)}% ao ano'
    
    @cet.setter
    def cet(self, v: str | Decimal2 | float):
        self._cet = self._validar_decimal(v)

    @property
    def cesh(self) -> str:
        """Custo Efetivo Seguro Habitacional."""
        return '' if not self._cesh else f'{self._cesh.formatar_moeda(True)}% ao ano'

    @cesh.setter
    def cesh(self, v: str | Decimal2 | float):
        self._cesh = self._validar_decimal(v)

    def __str__(self):
        TAM_TRACEJADO = Parametros.TAM_TRACEJADO
        b: str = '' if not self._negrito_resultado else '*'
        s = self
        t: str = (
            f'{b}{s.titulo}{b}\n'
            f'{"-" * TAM_TRACEJADO}\n'
        )
        if self._obj_simulador:
            t += (
                f'{b}Valor do Imóvel:{b} {s._obj_simulador.valor_imovel}\n'
                f'{b}Valor de Entrada:{b} {s._obj_simulador.valor_entrada}\n'
                f'{b}Prazo:{b} {s._obj_simulador.prazo}\n'
            )
        t += (
            f'{b}Primeira Parcela:{b} {s.primeira_parcela}\n'
            f'{b}Última Parcela:{b} {s.ultima_parcela}\n'
            f'{b}Taxa de Juros:{b} {s.taxa_juros}\n'
        )
        if self.cet:
            t += f'{b}CET (Custo Efetivo Total):{b} {s.cet}\n'
        t += (
            f'{b}Somatório das Parcelas:{b} {s.somatorio_parcelas}\n'
            f'{b}Total Financiado:{b} {s.total_financiado}\n'
        )
        if self.cesh:
            t += f'{b}CESH (Custo Efetivo Seguro Habitacional):{b} {s.cesh}'
        return t


def test1() -> bool:
    cpf: str = '76709347001'
    nome: str = 'Guido Vanderval'
    email: str = 'guidov22@ymail.com'
    celular: str = '62 99245 7121'
    tipo_imovel: TipoImovel = TipoImovel.RESIDENCIAL
    valor_imovel: str = '145.000'
    valor_entrada: str = '50000'
    data_nascimento: str = '18/08/1994'
    prazo_financiamento: int = 30

    sim_itau = SimuladorItauS.a_partir_de_dados_financiamento(
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
    valor_imovel: str = '200000'
    valor_entrada: str = '40000'
    data_nascimento: str = '08/10/1999'
    prazo: int = 30
    renda_familiar: str = '6422'

    sim_itau = SimuladorItauL(
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

    test1()
    #test2()
