#!/usr/bin/env python
from decimal import InvalidOperation
from simovel.sims.caixa import SimuladorCaixa, TipoFinanciamento, OpcaoFinanciamento
from simovel.util import Decimal2
import simovel.config.layout
from simovel.exceptions import *


def test_obter_cidades():
    sim = SimuladorCaixa()
    assert(sim.total_cidades == 0)
    sim.obter_cidades()
    assert(sim.total_cidades > 100)
    sim.uf = 'go'
    assert(sim.uf.lower() == 'go')


def test_simulacao() -> None:
    simulador = SimuladorCaixa()
    Decimal2.setar_local_pt_br()
    assert(simulador.uf == 'GO')
    simulador.obter_cidades()
    assert(len(simulador.cidades) > 10)
    print('#' * 70)
    print("Selecionando cidade:")
    cod = simulador.obter_cod_cidade_por_nome('ITABERAI')
    #cod = simulador.obter_cod_cidade_por_nome('ABADIANIA')
    print(cod)
    assert(cod != 0)
    assert(simulador.cidade_chave != '')

    simulador.tipo_imovel = TipoFinanciamento.NOVO
    try:
        simulador.valor_imovel = 'abc'
    except ErroValorImovel as erro:
        print('Erro1 ao setar valor_imovel:')
        print(erro)
    except ErroValorImovelAbaixoMin as erro:
        print('Erro2 ao setar valor_imovel')
        print(erro)

    print()

    try:
        simulador.valor_imovel = '80000'
        print(simulador.valor_imovel)
    except ErroValorImovel as erro:
        print(f'{erro}')
    except ErroValorImovelAbaixoMin as erro:
        print(f'{erro}')

    print()

    try:
        simulador.cpf = '12345678901'
    except ErroCPF as erro:
        print('Erro ao setar CPF.')
        print(erro)
    
    print()
    try:
        #simulador.cpf = '968.944.890-09'
        simulador.cpf = '023.282.691-92'
        print(simulador.cpf)
    except ErroCPF as erro:
        print(f'Erro ao setar CPF: {erro}')
        print(erro)

    print()
    
    try:
        simulador.celular = '62 923-4567'
    except ErroCelular as erro:
        print(f'Erro ao setar celular: {erro}')
    
    print()
    
    try:
        simulador.celular = '62-99843-2122'
        #simulador.celular = '(62)99843-2122'
        print(simulador.celular)
    except ErroCelular as erro:
        print(f'Erro ao setar fone: {erro}')

    print()

    try:
        simulador.renda_familiar = 'R$ 822,00'
    except ErroRendaFamiliar as erro:
        print(f'{erro}')
    
    print('Tentantado com outro valor...')
    try:
        simulador.renda_familiar = '1.100'
        print(f'{simulador.renda_familiar=}')
    except ErroRendaFamiliar as erro:
        print(f'{erro}')

    print()

    try:
        simulador.data_nascimento = '32/08/1999'
    except ErroDataNascimento as erro:
        print(f'Erro ao definir data: {erro}')
    
    print()
    
    try:
        #simulador.data_nascimento = '25 02 83'
        simulador.data_nascimento = '08 02 1987'
        print(f'Data nasc. definida: {simulador.data_nascimento}')
    except ErroDataNascimento as erro:
        print(f'Erro ao definir data de nasc.: {erro}')

    print()

    try:
        simulador.opcao_financiamento = 'bla'
    except ErroOpcaoFinanciamento as erro:
        print(f'Erro ao setar opção de financiamento: {erro}')

    print()

    try:
        print('Setando Opção Financiamento')
        print(f'Anterior: {simulador.opcao_financiamento=}')
        #simulador.opcao_financiamento = OpcaoFinanciamento.SBPE_CRED_IMOB_POUP_CAIXA
        simulador.opcao_financiamento = OpcaoFinanciamento.PROGRAMA_CASA_VERDE_AMARELA
        print(f'Setada: {simulador.opcao_financiamento=}')
    except ErroOpcaoFinanciamento as erro:
        print(f'Erro ao setar opção de financiamento: {erro}')

    print() 
    #try:
    sim_resultado = simulador.simular()
    if sim_resultado.msg_erro:
        print(sim_resultado.msg_erro)
        print()
        print('Tentando com um valor maior pra renda familiar...')
        if sim_resultado.msg_erro == config.layout.CaixaResultado.T_MSG_ERRO_RENDA_INSUFICIENTE:
            #simulador.renda_familiar = 2200
            simulador.renda_familiar = 1800
            print(simulador.renda_familiar)
            sim_resultado = simulador.simular()
            if sim_resultado.msg_erro:
                print('VERIFICAR!')
            else:
                print('OPA, DEU CERTO!')
                print(sim_resultado)
                print()
                input('Pressione enter pra fazer mais uma simulação. ')
    
    try:
        simulador.valor_imovel = 'R$ 80.000,00'
        simulador.renda_familiar = '1800'
        simulador.opcao_financiamento = OpcaoFinanciamento.PROGRAMA_CASA_VERDE_AMARELA_FAIXA_1_5
        print()
        print('TENTANDO OS SEGUINTES VALORES:')
        print(f'{simulador.valor_imovel=}')
        print(f'{simulador.renda_familiar=}')
        print(f'{simulador.opcao_financiamento=}')
        if sim_resultado.msg_erro:
            print()
            print(sim_resultado.msg_erro)
            print()
        else:
            print()
            sim_resultado = simulador.simular()
            print(sim_resultado)
            print()
            print('TUDO OK')            
            print()
    except Exception as erro:
        print(f'{erro=}')

    print()
    print()
    opcoes_financiamento = simulador.obter_opcoes_financiamento()
    for opcao in opcoes_financiamento:
        print(f'{opcao.value=}\n{opcao.versao=}\n{opcao.descricao=}')
        print('*' * 80)


if __name__ == '__main__':
    test_simulacao()
