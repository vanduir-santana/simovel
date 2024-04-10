#!/usr/bin/env python
# coding: utf-8

__version__ = '0.8'
__author__ = 'Vanduir Santana Medeiros'


class Erro(Exception):
    """Classe base de erros.
    """
    pass

class ErroBancoInvalido(Erro):
    """Não existe banco ou não é no tipo banco.
    """
    pass


#class OpcaoFinanciamentoInvalida(Erro):
class ErroOpcaoFinanciamento(Erro):
    """Opção de financiamento inválida. Não faz parte da Enum.
    """
    def __init__(self, valor, message='A opção de financiamento {} é inválida.'):
        self.message = message.format(valor)
        super().__init__(self.message)


class ErroTipoFinanciamento(Erro):
    """Tipo de financiamento inválido.
    """
    pass


class ErroValorPrimeiraPrestacao(Erro):
    """Disparado quando a primeira prestação tiver com mais de três casas decimais e no formato EUA.
    """
    def __init__(self, valor, message='Valor da 1ª prestação inválido "{}": sistema EUA e também tem mais de 2 casas decimais. Verificar param2 em obj.simular.'):
        self.message = message.format(valor)
        super().__init__(self.message)


class ErroValorImovel(Erro):
    """Valor do imóvel inválido. Não conseguiu converter o valor do imóvel em Decimal.
    """

class ErroValorImovelAbaixoMin(Erro):
    """Valor do imóvel abaixo do mínimo configurado ou abaixo do mínimo aceito pelo banco.
    """
    pass


class ErroCPF(Erro):
    """CPF não é válido, possui algum erro, não passou no teste de dígito verificador, etc.
    """
    pass

class ErroCelular(Erro):
    """Celular inválido ou celular não preenchido.
    """
    pass


class ErroRendaFamiliar(Erro):
    """Erro da renda familiar inválida ou abaixo da renda familiar bruta mínima.
    """
    pass


class ErroRendaFamiliarInsuficente(Erro):
    """Disparado quando vai efetuar a simulação e a Caixa retorna uma mensagem de renda insuficiente.
    """

class ErroValorFinanciamentoInferior(Erro):
    """Disparado quando vai efetuar a simulação e a Caixa retorna a
    mensagem: VALOR DE FINANCIAMENTO CALCULADO É INFERIOR AOS LIMITES
    DO PROGRAMA.
    """

class ErroDataNascimento(Erro):
    """Disparado quando for colocada uma data de nascimento inválida. Ver o módulo util.data_eh_valida().
    """
    pass


class ErroUF(Erro):
    """UF inválida.
    """
    pass


class ErroCidadeNaoSelecionada(Erro):
    """É preciso selecionar uma cidade.
    """
    pass


class ErroObterOpcaoFinanciamento(Erro):
    """Não consegue extrair as opções de financiamento.
    """
    pass


class ErroPrazo(Erro):
    """Não conseguiu definir prazo em meses."""
    pass

class ErroValorEntrada(Erro):
    """Erro valor de entrada inválido ou abaixo do esperado.
    """
    pass


class ErroPrestacaoMax(Erro):
    """Erro disparado quando valor da prestação máxima tiver errado.
    """


class ErroOpcaoFinanciamentoVersao(Erro):
    """Disparado quando não tiver sido definida uma versão pra opção do financiamento.
    """