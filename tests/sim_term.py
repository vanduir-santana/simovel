#!/usr/bin/env python
# coding: utf-8
"""Testes Simulador de Crédito Imobiliário
"""
from enum import Enum, EnumMeta
from exc import ErroCPF, ErroCelular, ErroCidadeNaoSelecionada, ErroDataNascimento, ErroOpcaoFinanciamento, ErroRendaFamiliar, ErroTipoFinanciamento, ErroValorImovel, ErroValorImovelAbaixoMin
import sim
from util import Decimal2

__version__ = '0.22'
__author__ = 'Vanduir Santana Medeiros'

class Ler(Enum):
    TIPO_IMOVEL = 0
    VALOR_IMOVEL = 1
    CPF = 2
    CELULAR = 3
    RENDA_FAMILIAR = 4
    DATA_NASCIMENTO = 5
    OPCAO_FINANCIAMENTO = 6
    VOLTAR = 7

class TesteSimulador(sim.Simulador):
    _prim_item = 0
    _TAM_PAG=10
    _ult_item = _TAM_PAG
    _opcao_menu = "1"

    def __init__(self):
        super().__init__()

    def _ler_uf(self) -> str:
        """Lê UF do usuário até q ele digite corretamente

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
        print('*' * 100)
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
            print('*' * 44)
            s = input('Entre com o número da cidade ou 0 pra voltar: ')
            if not s.isdigit():
                print('Digite um número')
                continue

            n = int(s)
            if not n in intervalo:
                print('Favor digitar um número entre: 0-{}'.format(total_cidades_filtro))
                continue
        
            if n == 0:
                return n
            
            return n

    def menu_principal(self) -> str:
        while True:
            print('*' * 44)
            t = """\
1 - ler UF
2 - listar cidades/mais cidades
3 - procurar cidade
4 - ler tipo imóvel, valor imóvel, CPF, celular, renda familiar bruta, data nascimento
5 - simular
0 - sair
Padrão ({})
""".format(self._opcao_menu)
            s = input(t)
            opcoes = ['', '1', '2', '3', '4', '5', '0']
            if not s in opcoes:
                print('Opção inválida!')
                continue
            else:
                if s:
                    self._opcao_menu = s
                return self._opcao_menu

    def _listar_cidades(self):
        if len(self._cidades) == 0:
            print('Favor primeiro selecionar UF!')
            return False

        itens = list(self._cidades.items())
        for i in range(self._prim_item, self._ult_item):
            codigo = itens[i][1][0]
            cidade = itens[i][1][1]
            print('{} - {}'.format(cidade, codigo))
        
        total_cidades = len(self._cidades)
        self._prim_item += self._TAM_PAG
        self._ult_item = self._prim_item + self._TAM_PAG \
                         if self._ult_item + self._TAM_PAG <= total_cidades else total_cidades

        return True

    def _ler_enum(self, titulo: str, enum_cls_ou_lista: Enum, opcao_voltar: bool = True,
                  campo_padrao: str = '') -> Enum:

        eh_enum: bool = False
        if type(enum_cls_ou_lista) is Enum or type(enum_cls_ou_lista) is EnumMeta:
            eh_enum = True
            valores = list(enum_cls_ou_lista)
        else:
            valores = enum_cls_ou_lista
            
        opcoes = [f'{str(i + 1)} - {str(valor)}' for i, valor in enumerate(valores)] 
        if opcao_voltar: opcoes += ['0 - Voltar\n']
        titulo = '\n'.join(opcoes) + f'\n{titulo} ({campo_padrao})'

        print()
        print('*' * 70)
        while True:
            r = input(f'{titulo} ')
            if r == '' and campo_padrao is not None:
                return campo_padrao
            elif r == '0':
                return None
            elif not r.isdigit() or not int(r) - 1 in range(len(valores)):
                print('Opção inválida, digite uma opção válida ou 0 pra voltar')
                continue
            return valores[int(r) - 1] if eh_enum else int(r) - 1

    def _ler_lista(self, titulo: str, lista: list) -> int:
        return self._ler_enum(titulo, lista)
        
    def _ler_texto(self, titulo: str, tam_min: int = 4) -> str:
        print()
        r: str = ''
        titulo += f' (mínimo {tam_min} caracteres) ou 0 pra sair: '
        while r != '0' and len(r) < tam_min:
            r = input(titulo)
        
        return r

    def menu_campos(self, titulo: str, campo_padrao: Ler = Ler.VOLTAR) -> Ler:
        return self._ler_enum(titulo, Ler, opcao_voltar=False, campo_padrao=campo_padrao)

    def ler_dados(self, ler: Ler = Ler.TIPO_IMOVEL) -> None:
        """Lê dados do cliente pra fazer a simulação.
        """
        match ler:
            case Ler.TIPO_IMOVEL:
                try:
                    self.tipo_imovel = self._ler_enum('Entre com o tipo do imóvel:', sim.TipoFinanciamento)
                    print(f'Selecionado: {self.tipo_imovel}')
                except ErroTipoFinanciamento as erro:
                    print(f'{erro=}')
            
            case Ler.VALOR_IMOVEL:
                try:
                    self.valor_imovel = self._ler_texto('Qual o valor do imóvel?', tam_min=2)
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
                    self.celular = self._ler_texto('Digite o celular', tam_min=8)
                    print(f'Formatado: {self.celular}')
                except ErroCelular as erro:
                    print(f'{erro}')

            case Ler.RENDA_FAMILIAR:
                try:
                    self.renda_familiar = self._ler_texto('Entrar com a renda familiar bruta', tam_min=2)
                except ErroRendaFamiliar as erro:
                    print(f'{erro}')

            case Ler.DATA_NASCIMENTO:
                try:
                    self.data_nascimento = self._ler_texto('Entrar com a data de nascimento')
                except ErroDataNascimento as erro:
                    print(f'{erro}')

            case Ler.OPCAO_FINANCIAMENTO:        
                try:
                    opcoes_financiamento: list = self.obter_opcoes_financiamento()
                    opcoes_financiamento_desc = [opcao.descricao for opcao in opcoes_financiamento]
                    indice = self._ler_lista('Entre com a opção de financiamento:', lista=opcoes_financiamento_desc)

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
                input('Nenhuma opção selecionada (pressine enter pra continuar): ')
                _aguardar_enter()
                return

        print('*' * 70)

        campo_padrao: Ler = Ler(ler.value + 1) if ler != Ler.VOLTAR else Ler.VOLTAR

        ler_campo = self.menu_campos("Escolha o campo que deseja:", campo_padrao)
        if ler_campo == Ler.VOLTAR:
            return
        else:
            self.ler_dados(ler_campo)
                

def _aguardar_enter():
    input("Pressione enter pra continuar: ")

def main():
    Decimal2.setar_local_pt_br()
    sim = TesteSimulador()

    while True: 
        opcao = sim.menu_principal()
        if opcao == '0':
            return
        elif opcao == '1':
            print('Lendo UF...')
            uf = sim._ler_uf()
            print('Obtendo cidades...')
            if not sim.obter_cidades(uf):
                _aguardar_enter()
        elif opcao == '2':
            if not sim._listar_cidades():
                _aguardar_enter()
        elif opcao == '3':
            sim._filtrar_cidades_por_nome()
            if sim.cidades_filtro:
                opcao2 = sim.menu_cidades()
                if opcao2 == 0:
                    continue
                i = opcao2 - 1
                cidade = sim.cidades_filtro[i]
                cod = sim.obter_cod_cidade_por_nome(cidade)
                print('*' * 44)
                print('Cidade escolhida: {} - {}'.format(cod, cidade))
        elif opcao == '4':
            ler_campo = sim.menu_campos("Escolha o campo q deseja preencher: ")
            sim.ler_dados(ler_campo)
        elif opcao == '5':
            try:
                sim_resultado = sim.simular()
                if sim_resultado.msg_erro:
                    print(sim_resultado.msg_erro)
                else:
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

            print()
            print()

if __name__ == '__main__':
    main()