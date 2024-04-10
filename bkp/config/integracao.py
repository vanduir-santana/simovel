"""Configurações das integrações ligadas ao Simóvel
"""

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.18'


class Multi360:
    MAX_RES_MENU_CIDADES = 6
    DPTO_UUID = '204205b6-1f75-45c0-a631-5b87f1adc49c'
    class Questao:
        """Configurações dos textos das questões."""
        UF = 'Antes de continuar é preciso que vc entre com algumas informações. Favor digitar a UF:'
        UF_INVALIDA = '"{uf}" é uma UF inválida! Favor digitar uma UF válida como GO, SP, RJ, MG, etc.'
        CIDADE = """Digite a *cidade*. Vc pd entrar com apenas parte do nome que iremos exibir opções aproximadas.
        Por exemplo: Aparecida de Goiânia, vc pode digitar: aparec
        ou: Alto Paraíso de Goiás, digite: Paraíso"""
        CIDADE = """Informe a cidade onde pretende comprar seu imóvel. 

        Você pode digitar apenas parte do nome que iremos exibir as opções 
        Por exemplo: Goiânia, você pode digitar: Goian
        """
        CIDADE2 = "Tente digitar novamente o nome da cidade ou parte do nome."
        CIDADE_INVALIDA = 'A cidade precisa ter pelo menos 3 caracteres!'
        CIDADE_PESQUISA_VAZIA = '*Não* encontrou nenhum resultado para a pesquisa *{}*. Digite novamente o nome ou parte do nome da *cidade*'
        VALOR_IMOVEL = 'Qual o valor do imóvel?'
        CPF = '''Digitar *CPF*.
        Os grupos podem ser separados por espaço, somentes números, exemplos:
        234.567.890-12
        234 567 890 12
        23456789012'''
        CPF_INVALIDO = '*CPF inválido*, digite novamente:'
        CELULAR = '''Digitar o *celular*. Aqui pode ser digitado também só os números, separar por espaços, formatos aceitos:
        (62) 9 9912-3456
        62 9 9912 3456
        62999123456'''
        CELULAR_INVALIDO = 'Celular inválido, digite novamente o *número do celular:*'
        RENDA_FAMILIAR = 'Você pode *somar a sua renda* com a renda de outro integrante da sua família, como por exemplo sua(eu) esposa(o). *Entrar com a renda familiar bruta:*'
        RENDA_FAMILIAR_INSUFICIENTE = 'ATENÇÃO! Renda familiar insuficiente: {}. Você pode *somar a sua renda* com a renda de outro integrante da sua família, como por exemplo sua(eu) esposa(o). *Digite um novo valor pra renda familiar:*'
        DATA_NASCIMENTO = '''Qual a sua data de nascimento?
        Formatos aceitos:
        09/05/1992
        09 05 1992
        09-05-1992
        9 5 92'''
        ALTERAR_VALOR_ENTRADA = 'Entrada atual: {}. Digite o novo *Valor da Entrada (R$):*'
        ALTERAR_PRAZO = 'Digite o número de parcelas que você deseja. Prazo máximo: {}. *Digite o novo prazo:*'
        ALTERAR_PRAZO_BAIXO = 'Prazo parece estar muito baixo. Prazo atual: {}; Prazo Máximo: {}. Entre com um *prazo maior:*'
        ALTERAR_PRESTACAO_MAX = 'Prestação máxima atual: {}. Digite o valor da *prestação máxima:*'
        ALTERAR_PRESTACAO_MAX_ABAIXO = 'Provavelmente você digitou uma prestação máxima abaixo do aceito. Digite novamente a *prestação máxima:*'
        ALTERAR_RENDA = '*Renda atual: {}*. Você pode somar a renda de outro integrante da família a sua, por exemplo, sua renda é R$ 1.400,00 e a da sua(eu) esposa(o) também, então você pode digitar 2.800. Digite a nova *renda familiar bruta:*'


    class Menu:
        """Configurações dos textos dos menus."""
        CIDADES = 'Digite o número da cidade que deseja selecionar:'
        CIDADE_ITEM_BUSCAR_NOVAMENTE = 'PESQUISAR CIDADE NOVAMENTE'
        ID_BUSCAR_NOVAMENTE = -1
        TIPO_FINANCIAMENTO = 'Qual o tipo de imóvel deseja financiar?'
        TRES_ANOS_FGTS = 'Você possui mais de 3 anos de FGTS somando todos os períodos trabalhados?'
        MAIS_DE_UM_COMPRADOR_DEPENDENTE = 'Mais de um comprador e/ou possui dependente?'
        OPCOES_FINANCIAMENTO = 'Selecione uma opção de financiamento:'
        OPCOES_FINANCIAMENTO_ERRO = 'Erro ao obter informações de financiamento, agradecemos a compreensão. O erro foi relatado e será corrigido em breve.'
        OPCOES_FINANCIAMENTO_ERRO2 = 'Erro ao definir opções de financiamento, o erro foi reportado e em breve será corrigido, agradecemos a compreensão.'
        ITEM_ALTERAR_RENDA = 'Alterar Renda Familiar'
        ITEM_ALTERAR_PRAZO = 'Alterar Prazo'
        RESULTADO_OBS = 'Você pode *ajustar o financiamento* de acordo com suas necessidades e assim encontrar as melhores condições. É possível diminuir o prazo, aumentar o valor da entrada e a renda familiar. Se quiser pode também *alterar seus dados ou do imóvel* como cidade, tipo financiamento (novo, usado, terreno), valor do imóvel, etc. Digite a opção:'
        ALTERAR_DADOS = 'Percebemos que *você já esteve por aqui antes*. Pra facilitar sua vida esses são os dados da sua última simulação. Digite o número ou selecione o campo que deseja alterar pra efetuar outra simulação.'
        ALTERAR_DADOS2 = 'Digite o número ou selecione o campo que deseja alterar pra efetuar outra simulação.'
        FINALIZAR_SIMULACAO = 'A Simulação foi como você esperava?'
        # TODO: melhorar msg adicionando explicação sobre indexador?
        SISTEMA_AMORTIZACAO = 'Sistema de Amortização/Indexador atual: {}. No Sistema *SAC* (Sistema de Amortização Constante) as prestações começam com um valor mais alto e vão diminuindo com o passar do tempo. No sistema *PRICE* as prestações são mais baixas. Escolha um *Sistema de Amortização/Indexador:*'
        DICAS = 'Selecione uma dica para ver mais detalhes.'
    

    class Informacao:
        """Configurações das mensagens de informação."""
        SIMULACAO_ERRO = 'Erro ao efetuar simulação. O erro foi reportado e em breve será corrigido. Agradecemos a compreensão!'


    class MenuDicas:
        """Menu com dicas sobre como melhorar a simulação de 
        financiamento. As dicas precisam seguir o seguinte padrão:
        palavra DICA seguido do número sequencial começando em 1.
        """
        DICA1 = (
            '🤑Dica 1: Renda Familiar Bruta',
            '''A renda familiar é correspondente a soma de todas as rendas dos integrantes da família. 
            Portanto se você é casado(a), pode somar a renda dos dois e assim fazer um ajuste mais fino na simulação.'''
        )
        DICA2 = (
            '💰Dica 2: FGTS',
            '''Caso possua mais de 3 anos de FGTS é recomendável que responda sim para essa pergunta.'''
        )
        DICA3 = (
            '👨‍👨‍👧‍👧Dica 3: Mais de um comprador e/ou dependente ',
            '''Quando houver mais de um comprador ou possuir um dependente, como filho, por exemplo, é importante responder
            sim pra essa questão pois nesses casos o simulador oferece melhores condições de financiamento.'''
        )
        DICA4 = (
            '💱Dica 4: Sistema de amortização',
            '''A amortização nada mais é que a diminuição da dívida através do parcelamento. Os sistemas de amortização mais comuns são SAC e PRICE.
            *SAC:* no Sistema de Amortização Constante a parcela no começo é mais alta e vai diminuindo com o passar do tempo.
            *PRICE:* nesse sistema as parcelas são mais baixas e constantes.'''
        )
        DICA5 = (
            '💹Dica 5: Indexador',
            '''O indexador é utilizado pro reajuste mensal do saldo devedor. Na Caixa o cliente seleciona o indexador.
            *TR:* a Taxa Referencial tem menor variação de um mês pra outro.
            *IPCA:* Índice de Preço ao Consumidor Amplo, esse índice acompanha a inflação e geralmente tem uma menor taxa de juros. Pode ter uma variação maior de um mês pra outro.
            A CAIXA também oferece opções com a taxa de juros fixa, onde o cliente sabe previamente qual será o valor que irá pagar mensalmente até o final da operação.'''

        )
