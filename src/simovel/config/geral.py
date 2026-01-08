# coding: utf-8
"""Configurações gerais do simulador
"""
__version__ = '0.16'
__author__ = 'Vanduir Santana Medeiros'


from enum import Enum
from decimal import Decimal


class ItauTipoSimulacao(Enum):
    SEL = 1
    LOF = 2


class Parametros:
    BANCOS_ACEITOS = {
        'caixa': True,
        'bradesco': False,
        'itau': False,
        'santander': False
    }
    SELECIONAR_AUTO_QUANDO_APENAS_UM_BANCO_HABILITADO = True
    UF_PADRAO = 'GO'
    VALOR_IMOVEL_MIN = 10000.
    CELULAR_CAIXA_DEFAULT = '(62)99843-2122'
    RENDA_FAMLIAR_MIN = 1100.
    DATA_FORMATOS: tuple = (
        '%d/%m/%Y',
        '%d %m %Y',
        '%d-%m-%Y',
        '%d/%m/%y',
        '%d %m %y',
        '%d-%m-%y',
        '%d%m%Y',
        '%d%m%y'
    )
    FONE_TAM_MIN = 8
    DDD_PADRAO = 62
    IDADE_MIN = 18
    DATABASE_URI = 'sqlite:///sim.db'
    UFS_CSV = 'rest_api/ufs.csv'
    VALOR_ENTRADA_MIN_PERC = {
        'caixa': None,      # não precisa
        'bradesco': None,   # não precisa
        'itau': Decimal(10),
        'itau_l': Decimal(10),
        'santander': Decimal(20)
    }
    VALOR_ENTRADA_MAX_PERC = Decimal(90)
    TAM_TRACEJADO = 35      # tracejado q aparece no resultado da simulação
                            # ou pra separar linhas


class SiteImobiliaria:
    URL = 'https://itamarzinimoveis.com.br/imovel?operacao=1&tipoimovel=&imos_codigo=&empreendimento=&destaque=false&vlini={}&vlfim={}&exclusivo=false&cidade=&pais=1&filtropais=false&order=minval&limit=9&page=0&ttpr_codigo=1'
    VALOR_IMOVEL_PERC_VARIACAO = 40
    EXIBIR_URL_FILTRO_IMOVEIS = True


class Api:
    #URL = 'http://sim.itamarzinimoveis.com.br:8080'
    URL_PREFIX_MULTI_360 = '/api/multi360'


class Caixa:
    # não pergunta pra marcar se Possui Relacionamento Caixa
    PERGUNTAR_CLIENTE_CAIXA = False
    # corresponde a marcar a opção Possui Relacionamento Caixa
    CLIENTE_CAIXA = False
    # se for True a configuração OPCOES_FINANCIAMENTO_ACEITAS passa
    # a NÃO ter efeito
    PERMITIR_TODAS_OPCOES_FINANCIAMENTO = True
    # Se a lista tiver vazia aceita todas as opções de financiamento, 
    # senão apenas os códigos dentro dela
    OPCOES_FINANCIAMENTO_ACEITAS = [
        #### RESIDÊNCIAL
        100301129,  # SBPE (TR, IPCA ou Tx FIXA): Débito em conta na CAIXA
        100301130,  # SBPE (Crédito Imobiliário Poupança CAIXA): Débito em conta na CAIXA
        100501103,  # Programa Casa Verde e Amarela
        105801121,  # SBPE (Crédito Imobiliário Poupança CAIXA): Débito em conta na CAIXA (imóvel usado)
        105801120,  # SBPE (TR, IPCA ou Tx FIXA): Débito em conta na CAIXA (imóvel usado)
        106001102,  # Programa Casa Verde e Amarela (imóvel usado)
        103401100,  # SBPE Relacionamento Caixa (Terreno)
        107501106,  # SBPE (TR ou Tx FIXA): Débito em conta na CAIXA (Construção)
        107501107,  # SBPE (Crédito Imobiliário Poupança CAIXA): Débito em conta na CAIXA (Construção)
        107701100,  # Programa Casa Verde e Amarela: Construção em Terreno Próprio
        107701105,  # Programa Casa Verde e Amarela: Compra de Terreno e Construção
        108701106,  # CRÉDITO REAL FÁCIL CAIXA (TR, IPCA ou Tx FIXA): Setor Privado - Garantia Imóvel Residencial
        108701131,  # CRÉDITO REAL FÁCIL POUPANÇA CAIXA: Setor Privado - Garantia Imóvel Residencial
        # confirmar com o Itamar se é pra manter essas abaixo
        100501101,  # Programa Minha Casa, Minha Vida - Recursos FGTS: Imóvel vinc. a Empreendimento financiado na CAIXA
        # 100301131, SBPE (TR): Imóvel Vinc. Empreend. Financiado na CAIXA - Relacionamento
        #### COMERCIAL
        100301103,  # SBPE: Relacionamento (Novo)
        105801102,  # SBPE: Relacionamento (Usado)
        108701118,  # CRÉDITO REAL FÁCIL CAIXA (TR, IPCA ou Tx FIXA): Setor Privado - Garantia Imóvel Comercial
        108701134,  # CRÉDITO REAL FÁCIL POUPANÇA CAIXA: Setor Privado - Garantia Imóvel Comercial
    ]
    
    class ObservacaoSistemaAmortizacao:
        EXIBIR_OBS_SISTEMA_AMORTIZACAO = True
        OBS_SISTEMA_AMORTIZACAO_PRICE = '*Dica: Você pode optar por parcelas decrescentes alterando o sistema de amortização para SAC, com isso as prestações ficam maiores*'
        OBS_SISTEMA_AMORTIZACAO_SAC = '*Dica: Você pode optar por parcelas fixas alterando o sistema de amortização para PRICE com isso as prestações ficam menores*'


class Bradesco:
    PRAZO_MIN = 90  # meses
    # prazo máximo é extraído da própria simulação


class Itau:
    PRAZO_MAX = 30                          # anos
    TIPO_SIMULACAO = ItauTipoSimulacao.LOF  # tipo de simulação, SEL simula direto no simulador do Itaú
                                            # como as vezes pd falhar, é possível fazer a mudança

class Santander:
    PRAXO_MAX = 30 # anos, na vdd são 35 anos, mas por compatibilidade é melhor deixar 30 anos (por enquanto)
