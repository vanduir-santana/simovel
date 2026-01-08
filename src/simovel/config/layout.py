# coding: utf-8
"""Configuação do layout da página de resultados
"""
__version__ = '0.16'
__author__ = 'Vanduir Santana Medeiros'


class CaixaResultado:
    TXT_SISTEMA_AMORTIZACAO_INI = 'Sistema de amortização'
    TXT_SUBSIDIO_CASA_VERDE_AMARELA_INI = 'Subsídio'
    SIMULACAO_RESULTADO_CAIXA_CAMPOS: dict = {
        'Valor do imóvel': 'valor_imovel',
        'Prazo máximo': 'prazo_max',
        'Prazo escolhido': 'prazo',
        'Cota máxima do financiamento': 'cota_max',
        'Valor da entrada': 'valor_entrada',
        TXT_SUBSIDIO_CASA_VERDE_AMARELA_INI: 'subsidio_casa_verde_amarela',  # implementar
        'Valor do financiamento': 'valor_financiamento',
        TXT_SISTEMA_AMORTIZACAO_INI: 'sistema_amortizacao'
    }
    PRIMEIRA_PRESTACAO = (3, '1ª Prestação')        # indíce linha, descrição
    ULTIMA_PRESTACAO = (4, 'Última Prestação')      # indíce linha, descrição
    T_MSG_ERRO_RENDA_INSUFICIENTE = 'ATENÇÃO!  RENDA INSUFICIENTE PARA REALIZAR A OPERAÇÃO.'


class CaixaObterOpcoesFinanciamento:
    #VERSAO = '3.21.69.0.1'     # agora obtem através de função implementada no módulo caixa.py
    T_OBTER_OPCOES_FINANCIAMENTO_JS = 'simuladorInternet.simular('
    T_OBTER_OPCOES_FINANCIAMENTO_SEP1 = ';jQuery('

