#!/usr/bin/env python
# coding: utf-8
"""Testes Simulador de Crédito Imobiliário
"""
from enum import Enum, EnumMeta
from typing import Iterable
from simovel.exceptions import (
    ErroCPF,
    ErroCelular,
    ErroCidadeNaoSelecionada,
    ErroDataNascimento,
    ErroRendaFamiliar,
    ErroRendaFamiliarInsuficente,
    ErroTipoFinanciamento,
    ErroTipoImovel,
    ErroValorImovel,
    ErroValorImovelAbaixoMin
)
from simovel.sims.caixa import (
    OpcaoFinanciamento, SimuladorCaixa, TipoImovel, SimulacaoResultadoCaixa
)
from simovel.util import Decimal2

__version__ = '0.38'
__author__ = 'Vanduir Santana Medeiros'


class Menu(Enum):
    UF = '1'
    LISTAR_CIDADES = '2'
    PROCURAR_CIDADE = '3'
    LER_DADOS = '4'
    PREENCHER_AUTO = '5'
    SIMULAR = '6'
    SAIR = '0'


class Ler(Enum):
    TIPO_IMOVEL = 0
    VALOR_IMOVEL = 1
    CPF = 2
    CELULAR = 3
    RENDA_FAMILIAR = 4
    DATA_NASCIMENTO = 5
    OPCAO_FINANCIAMENTO = 6
    VOLTAR = 7


class TesteSimulador(SimuladorCaixa):
    _prim_item = 0
    _TAM_PAG=10
    _ult_item = _TAM_PAG
    _opcao_menu: Menu = Menu.UF

    def __init__(self):
        super().__init__()

    def _ler_uf(self) -> str:
        """Lê UF do usuário até que ele digite corretamente

        Returns:
            str: retorna a UF lida.
        """
        self._prim_item = 0
        self._ult_item = self._TAM_PAG

        uf = ''
        while True:
            uf = input("Entre com a UF: ")
            try:
                self.uf = uf
                return self.uf
            except Exception as erro:
                print(f'{erro}')

    def _filtrar_cidades_por_nome(self) -> None:
        print('-' * 100)
        if not self._cidades:
            print('Não existem cidades carregadas!')
            return
        texto = "Entre com o nome da cidade ou pelo menos uma parte do nome: "
        while True:
            s = input(texto) 
            if len(s) >= 3:
                break
            print('Nome muito curto, digite ao menos 3 caracteres')

        cidades_lista = self.obter_cidades_nomes()
        cidades_filtro = self.procurar(s, cidades_lista, max_res=5)
        j = 0
        for i, nome in enumerate(cidades_filtro):
            j = i + 1
            print(f'{j} - {nome}')

    def menu_cidades(self, cidades: list[str] = []) -> int:
        if not cidades:
            if not self.cidades_filtro: return 0
            cidades = self.cidades_filtro
        
        total_cidades_filtro = len(cidades) + 1
        intervalo = range(0, total_cidades_filtro)
        while True:
            print('-' * 60)
            s = input('Entre com o número da cidade ou 0 pra voltar: ')
            if not s.isdigit():
                print('Digite um número')
                continue

            n = int(s)
            if not n in intervalo:
                print(
                    f'Favor digitar um número entre: 0-{total_cidades_filtro}'
                )
                continue
        
            if n == 0:
                return n
            
            return n

    def menu_principal(self) -> Menu:
        while True:
            print('-' * 60)
            texto_input = ( 
                '1 - ler UF\n'
                '2 - listar cidades/mais cidades\n'
                '3 - procurar cidade\n'
                '4 - ler tipo imóvel, valor imóvel, CPF, celular,\n'
                '    renda familiar bruta, data nascimento\n'
                '5 - preencher auto (exceto cidade e opção financ.)\n'
                '6 - simular\n'
                '0 - sair\n'
                f'Padrão ({self._opcao_menu.value}): '
            )
            s: str = input(texto_input)
            if s in Menu:
                if s:
                    self._opcao_menu = Menu(s)
                return self._opcao_menu
            else:
                print('Opção inválida!')
                continue


    def _listar_cidades(self):
        if len(self._cidades) == 0:
            print('Favor primeiro selecionar UF!')
            return False

        for i in range(self._prim_item, self._ult_item):
            codigo = self.cidades[i]['cod_caixa']
            cidade = self.cidades[i]['nome']
            print(f'{codigo} - {cidade}')
        
        total_cidades = len(self._cidades)
        self._prim_item += self._TAM_PAG

        if self._ult_item + self._TAM_PAG <= total_cidades:
            self._ult_item = self._prim_item + self._TAM_PAG
        else:
            self._ult_item = total_cidades

        return True

    def _enum_para_lista(self, enum: Iterable[Enum]) -> list[Enum]:
        return list(enum)

    def _ler_enum(
        self,
        titulo: str,
        enum_cls_ou_lista: list | Iterable[Enum],
        opcao_voltar: bool = True,
        campo_padrao: str = ''
    ) -> Enum | str | int | TipoImovel | None:
        eh_enum: bool = False
        valores: list = []
        if isinstance(enum_cls_ou_lista, (Enum, EnumMeta)):
            eh_enum = True
            valores = self._enum_para_lista(enum_cls_ou_lista)
        elif isinstance(enum_cls_ou_lista, list):
            valores = enum_cls_ou_lista
            
        opcoes = [
            f'{str(i + 1)} - {str(valor)}' for i, valor in enumerate(valores)
        ]

        if opcao_voltar:
            opcoes += ['0 - Voltar\n']

        titulo = '\n'.join(opcoes) + f'\n{titulo} ({campo_padrao})'

        print()
        print('-' * 70)
        while True:
            r = input(f'{titulo} ')
            if r == '' and campo_padrao is not None:
                return campo_padrao
            elif r == '0':
                return None
            elif not r.isdigit() or not int(r) - 1 in range(len(valores)):
                print(
                    'Opção inválida, digite uma opção válida ou 0 pra '
                    'voltar'
                )
                continue
            return valores[int(r) - 1] if eh_enum else int(r) - 1

    def _ler_lista(self, titulo: str, lista: list) -> int:
        ret = self._ler_enum(titulo, lista)
        if type(ret) is int:
            return ret
        else:
            return -1
        
    def _ler_texto(self, titulo: str, tam_min: int = 4) -> str:
        print()
        r: str = ''
        titulo += f' (mínimo {tam_min} caracteres) ou 0 pra sair: '
        while r != '0' and len(r) < tam_min:
            r = input(titulo)
        
        return r

    def menu_campos(
        self,
        titulo: str,
        campo_padrao: Ler = Ler.VOLTAR
    ) -> Ler | None:
        ret = self._ler_enum(
            titulo,
            Ler,
            opcao_voltar=False,
            campo_padrao=f'{campo_padrao.name} - {campo_padrao.value + 1}'
        )

        if isinstance(ret, Ler):
            return ret

        return None


    def ler_dados(self, ler: Ler | None = Ler.TIPO_IMOVEL) -> None:
        """Lê dados do cliente pra fazer a simulação.
        """
        match ler:
            case Ler.TIPO_IMOVEL:
                try:
                    tipo_imovel = self._ler_enum(
                        'Entre com o tipo do imóvel:', TipoImovel
                    )
                    if isinstance(tipo_imovel, TipoImovel):
                        self.tipo_imovel = tipo_imovel
                        print(f'Selecionado: {self.tipo_imovel}')
                    else:
                        print('Precisa ser instância de TipoImovel')
                except ErroTipoFinanciamento as erro:
                    print(f'{erro=}')
                except ErroTipoImovel as erro:
                    print(f'{erro=}')
            
            case Ler.VALOR_IMOVEL:
                try:
                    self.valor_imovel = self._ler_texto(
                        'Qual o valor do imóvel?', tam_min=2
                    )
                except ErroValorImovel as erro:
                    print(f'Problema com o valor do imóvel: {erro}')
                except ErroValorImovelAbaixoMin as erro:
                    print(f'{erro}')

            case Ler.CPF:
                try:
                    self.cpf = self._ler_texto('Digite o CPF', tam_min=11)
                except ErroCPF as erro:
                    print(f'{erro}')

            case Ler.CELULAR:
                try:
                    self.celular = self._ler_texto(
                        'Digite o celular', tam_min=8
                    )
                    print(f'Formatado: {self.celular}')
                except ErroCelular as erro:
                    print(f'{erro}')

            case Ler.RENDA_FAMILIAR:
                try:
                    self.renda_familiar = self._ler_texto(
                        'Entrar com a renda familiar bruta', tam_min=2
                    )
                except ErroRendaFamiliar as erro:
                    print(f'{erro}')

            case Ler.DATA_NASCIMENTO:
                try:
                    self.data_nascimento = self._ler_texto(
                        'Entrar com a data de nascimento'
                    )
                except ErroDataNascimento as erro:
                    print(f'{erro}')

            case Ler.OPCAO_FINANCIAMENTO:        
                try:
                    opcoes_financiamento = self.obter_opcoes_financiamento()
                    opcoes_financiamento_desc = [
                        opcao.descricao for opcao in opcoes_financiamento
                    ]
                    indice = self._ler_lista(
                        'Entre com a opção de financiamento:',
                        lista=opcoes_financiamento_desc
                    )

                    self.opcao_financiamento = opcoes_financiamento[indice]
                except Exception as erro:
                    print(f'Erro ao obter opções de financiamento {erro=}')
                    _aguardar_enter()
                    return

                print(f'Selecionado: {self.opcao_financiamento}')

            case Ler.VOLTAR:
                return
            
            case _:
                print()
                input(
                    'Nenhuma opção selecionada (pressione enter pra '
                    'continuar): '
                )
                _aguardar_enter()
                return

        print('-' * 70)

        campo_padrao: Ler = Ler.VOLTAR

        if ler != Ler.VOLTAR:
            campo_padrao = Ler(ler.value + 1)

        ler_campo = self.menu_campos(
            "Escolha o campo que deseja:", campo_padrao
        )

        if ler_campo == Ler.VOLTAR:
            return
        else:
            self.ler_dados(ler_campo)
                

def _aguardar_enter():
    input("Pressione enter pra continuar: ")


def preencher_auto1(sim: TesteSimulador):
    print('-' * 44)
    print('Preenchendo com valores auto...')
    print('-' * 44)
    sim.tipo_imovel = TipoImovel.RESIDENCIAL
    sim.valor_imovel = Decimal2(257000)
    sim.cpf = '00080287107'
    sim.celular = '62998992244'
    sim.renda_familiar = 3500
    sim.data_nascimento = '25/02/1983'

    try:
        opcoes_financiamento: list[OpcaoFinanciamento] = \
            sim.obter_opcoes_financiamento()

        opcoes_financiamento_desc = \
            [opcao.descricao for opcao in opcoes_financiamento]

        indice = sim._ler_lista(
            'Entre com a opção de financiamento:',
            lista=opcoes_financiamento_desc
        )

        sim.opcao_financiamento = opcoes_financiamento[indice]
    except Exception as erro:
        print(f'Erro ao obter opções de financiamento {erro=}')
        _aguardar_enter()
        return

    print(f'Selecionado: {sim.opcao_financiamento}')


def main():
    Decimal2.setar_local_pt_br()
    sim = TesteSimulador()
    sim.obter_cidades_db(uf='GO')

    while True:
        opcao: Menu = sim.menu_principal()
        if opcao == Menu.SAIR:
            return
        elif opcao == Menu.UF:
            print('Lendo UF...')
            uf = sim._ler_uf()
            print('Obtendo cidades...')
            #if not sim.obter_cidades(uf):
            if not sim.obter_cidades_db(uf):
                _aguardar_enter()
        elif opcao == Menu.LISTAR_CIDADES:
            if not sim._listar_cidades():
                _aguardar_enter()
        elif opcao == Menu.PROCURAR_CIDADE:
            sim._filtrar_cidades_por_nome()
            if sim.cidades_filtro:
                opcao2 = sim.menu_cidades()
                if opcao2 == 0:
                    continue
                i = opcao2 - 1
                cidade = sim.cidades_filtro[i]
                cod = sim.obter_cod_cidade_por_nome(cidade)
                print('-' * 60)
                print('Cidade escolhida: {} - {}'.format(cod, cidade))
        elif opcao == Menu.LER_DADOS:
            ler_campo = sim.menu_campos("Escolha o campo q deseja preencher: ")
            sim.ler_dados(ler_campo)
        elif opcao == Menu.PREENCHER_AUTO:
            # faz simulação com valores gerados automaticamente
            # escrever outras funções de testes
            preencher_auto1(sim)
        elif opcao == Menu.SIMULAR:
            # simula e trata resultado da simulação
            simular(sim)


def simular(sim: TesteSimulador):
    cidade_dict: dict = sim.cidades[sim.cidade_indice]
    cod_cidade: int = cidade_dict['cod_caixa']
    cidade: str = cidade_dict['nome']

    print('-' * 44)
    print('Efetuando simulação com as seguintes opções:')
    print('-' * 44)
    print(f'{cod_cidade=} - {cidade=}')
    print(f'{sim.tipo_imovel=}')
    print(f'{sim.valor_imovel=}')
    print(f'{sim.cpf=}')
    print(f'{sim.celular=}')
    print(f'{sim.renda_familiar=}')
    print(f'{sim.opcao_financiamento}')
    print('Simulando...')

    try:
        sim_resultado: SimulacaoResultadoCaixa = sim.simular()
        if sim_resultado.msg_erro:
            print(sim_resultado.msg_erro)
        else:
            larg_tracejado = len(sim_resultado.titulo) + 4
            print('-' * larg_tracejado)
            cabecalho = 'R E S U L T A D O    D A    S I M U L A Ç Ã O'
            print(f'{cabecalho:^{larg_tracejado}}')
            print('-' * larg_tracejado)
            sim_resultado._negrito_abertura = '\033[1m'
            sim_resultado._negrito_fechamento = '\033[0m'
            sim_resultado._largura_tracejado = larg_tracejado
            sim_resultado._exibir_obs_sistema_amortizacao = False
            print(sim_resultado)
    except ErroCidadeNaoSelecionada as erro:
        print(f'{erro}')
        _aguardar_enter()
    except ErroValorImovel as erro:
        print(f'{erro}')
        _aguardar_enter()
        sim.ler_dados(Ler.VALOR_IMOVEL)
    except ErroCPF as erro:
        print(f'{erro}')
        sim.ler_dados(Ler.CPF)
    except ErroCelular as erro:
        print(f'{erro}')
        sim.ler_dados(Ler.CELULAR)
    except ErroRendaFamiliar as erro:
        print(f'{erro}')
        sim.ler_dados(Ler.RENDA_FAMILIAR)
    except ErroDataNascimento as erro:
        print(f'{erro}')
        sim.ler_dados(Ler.DATA_NASCIMENTO)
    except ErroRendaFamiliarInsuficente as erro:
        print(f'{erro}')
        _aguardar_enter()


if __name__ == '__main__':
    main()
