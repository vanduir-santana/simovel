#!/usr/bin/env python
# coding: utf-8

__version__ = '0.9'
__author__ = 'Vanduir Santana Medeiros'


class Erro(Exception):
    """Classe base de erros.
    """
    pass

class ErroBancoInvalido(Erro):
    """Não existe banco ou não é no tipo banco.
    """
    pass

class ErroTipoImovel(Erro):
    """Erro acontece quando tipo imóvel não for setado ou for inválido.
    Funciona pra banco Bradesco.
    """

class ErroSituacaoImovel(Erro):
    """Situação do imóvel inválida: de um tipo não aceito.
    Bancos: Bradesco (semelhante ao ErroOpcaoFinanciamento da caixa)
    """

#class OpcaoFinanciamentoInvalida(Erro):
class ErroOpcaoFinanciamento(Erro):
    """Opção de financiamento inválida. Não faz parte da Enum.
    """
    def __init__(self, valor, message='A opção de financiamento {} é inválida.'):
        self.message = message.format(valor)
        super().__init__(self.message)

class ErroTipoImovel(Erro):
    """Tipo de imóvel inválido."""
    pass

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
    """Valor do imóvel inválido. Não conseguiu converter o valor do imóvel em Decimal."""

class ErroValorImovelAbaixoMin(Erro):
    """Valor do imóvel abaixo do mínimo configurado ou abaixo do mínimo aceito pelo banco."""
    pass


class ErroValorEntradaAcimaPermitido(Erro):
    """Valor da entrada acima do permitido ou acima do valor do imóvel."""
    pass


class ErroValorEntradaAbaixoPermitido(Erro):
    """Valor da entrada menor que o permitido."""
    pass


class ErroCPF(Erro):
    """CPF não é válido, possui algum erro, não passou no teste de dígito verificador, etc."""
    pass

class ErroCelular(Erro):
    """Celular inválido ou celular não preenchido."""
    pass

class ErroRendaFamiliar(Erro):
    """Erro da renda familiar inválida ou abaixo da renda familiar bruta mínima."""
    pass

class ErroRendaFamiliarInsuficente(Erro):
    """Disparado quando vai efetuar a simulação e a Caixa retorna uma mensagem de renda insuficiente."""
    pass 

class ErroValorFinanciamentoInferior(Erro):
    """
    Disparado quando vai efetuar a simulação e a Caixa retorna a
    mensagem: VALOR DE FINANCIAMENTO CALCULADO É INFERIOR AOS LIMITES
    DO PROGRAMA.
    """
    pass

class ErroValorFinanciamentoInferior2(Erro):
    """Igual a ErroValorFinanciamentoInferior porém quando seleciona a
    tipo de finaciamento 'Emprestimo Garantido por Imóvel'.
    """
    pass


class ErroValorFinanciamento(Erro):
    """Acontece quando existe algum problema ao setar o valor do financiamento. Bancos: Bradesco"""
    pass

class ErroValorMaxFinanciamento(Erro):
    """Erro acontece quando não está definido o valor máximo do financiamento. Bancos: Bradesco."""
    pass

class ErroFinanciarDespesas(Erro):
    """Acontece quando setar o attributo com um valor que não seja bool. Bancos: Bradesco."""
    pass

class ErroDataNascimento(Erro):
    """Disparado quando for colocada uma data de nascimento inválida. Ver o módulo util.data_eh_valida()."""
    pass

class ErroSistemaAmortizacaoInvalido(Erro):
    """Disparado quando tentar setar a taxa de amortização de outro tipo. Bancos: Bradesco."""
    pass

class ErroDataNascimentoConjuge(Erro):
    """
    Disparado quando for colocada uma data de nascimento de cônjuge 
    inválida. Ver o módulo util.data_eh_valida(). Específico pro módulo
    do Bradesco.
    """
    pass

class ErroFormaPagamentoInvalida(Erro):
    """
    Disparado quando tenta setar a partir de um tipo diferente de FormaPagamento.
    Bancos: Bradesco.
    """
    pass

class ErroSeguradoraInvalida(Erro):
    """
    Disparado quando tenta setar a partir de um tipo diferente de Seguradora.
    Bancos: Bradesco.
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
    pass

class ErroOpcaoFinanciamentoVersao(Erro):
    """Disparado quando não tiver sido definida uma versão pra opção do financiamento.
    Bancos: Caixa.
    """
    pass


class ErroResultadoTituloInvalido(Erro):
    """Disparado quando não existir título."""
    pass

class ErroResultadoCampoNaoRetornado(Erro):
    """Acontece quando um campo esperado não é retornado na simulação, por exemplo, valor do financiamento."""
    pass


class ErroNomeCurto(Erro):
    """Exceção gerada pelo simulador Itaú quando o nome é pequeno ou não tem sobrenome"""
    pass


class ErroEmail(Erro):
    """Exceção gerado pelo simulador Itaú quando o email for inválido."""
    pass


class ErroResultadoSimulacao(Erro):
    """Ocorre quando não consegue obter o resultado da simulação."""
