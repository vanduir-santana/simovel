#!/usr/bin/env python
# coding: utf-8
"""Funções úteis como por exemplo validar_cpf ou remover_acentos.
"""
__version__ = '0.22'
__author__ = 'Vanduir Santana Medeiros'

from exc import ErroCPF, ErroEmail
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from enum import Enum
import re
import unidecode
import locale
import os, csv
from random import randint

def remover_acentos(s: str, maiusc: bool=True) -> str:
    """Remover acentos de uma string.

    Args:
        s (str): a string com acentos.
        maiusc (bool, optional): converter para maiúsculas. Defaults to True.

    Returns:
        str: retorna string sem acentos.
    """
    palavra_acentuada = s.upper() if maiusc else s
    return unidecode.unidecode(palavra_acentuada)

def ajustar_esc_char(s: str) -> str:
    """Remove os caracteres desnecessários quando retorna uma string javascript, 
    retira as barras invertidas que não são usadas.""

    Args:
        s (str): string javascript

    Returns:
        str: retorna uma string sem os caracteres.
    """
    return s.replace('\\r', '\r').replace('\\n', '\n').replace('\\"', r'"').replace('\\t', '\t').replace("\\\'", "'")

def ajustar_unicode_esc_char(s: str) -> str:
    """Remove os caracteres de escape pra strings unicodes que não foram convertidas corretamente,
    retornadas de uma string javascritp, por

    Args:
        s (str): string que será retirada os caracteres

    Returns:
        str: retorna string sem os caracteres de escape.
    """
    return s.encode().decode('unicode_escape')

def data_eh_valida(s:str) -> bool:
    if not str:
        raise ValueError('É preciso preencher a data.')

def data_eh_valida(sdata: str, formatos: tuple[str], conv_date: bool=True) -> date:
    """Verifica através de uma str se data é válida.

    Args:
        sdata (str): string contendo a data a ser verificada.
        formatos (tuple[str]): tupla ou lista com os formatos a serem verificados. 
        conv_date (bool): se True converte pro tipo date, caso contrário retorna
        como tipo datetime

    Returns:
        datetime: retorna um datetime quando data estiver dentro de ao menos um dos formatos.
        caso contrário retorna None.
    """
    if type(sdata) is date or type(sdata) is datetime:
        return sdata

    if not type(sdata) is str:
        raise ValueError('sdata precisa ser str!')

    for formato in formatos:
        try:
            data = datetime.strptime(sdata, formato)
            if conv_date: data = date(data.year, data.month, data.day)
            return data
        except ValueError as erro:
            pass
    else:
        return None

def csv_pra_lista_de_dic(arq: str, nomes_campos: str) -> list:
    """Lê arquivo CSV e retorna lista de dicionários com os estados: nome e UF.
    A primeira linha é ignorada, pode ser colocado nela os nomes dos campos.
    Útil para inserir dados através do SQLAlchemy em massa.

    Args:
        nomes_campos (str): nomes dos campos, aparecem na primeira linha do
            arquivo.
    
    Returns:
        list[dict]: retorna uma lista de dicionários com as linhas.
    """
    if not os.path.exists(arq):
        raise Exception(f'Não encontrou o arquivo {arq}.')

    lista_dic: list = []
    with open(arq, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file, fieldnames=nomes_campos, delimiter=',')
        for i, dic_linha in enumerate(csv_reader):
            if i == 0: 
                continue
            lista_dic.append(dic_linha)
    return lista_dic


class Decimal2(Decimal):
    RS = 'R$ '
    CASAS_DECIMAIS = 2

    def __init__(self, valor: str | float | int | Decimal):
        self._valor = valor

    @property
    def valor(self) -> Decimal:
        return self._valor

    @classmethod
    def from_cur_str(cls, v: str | float | int | Decimal) -> 'Decimal2':
        """Obsoleto. Utilizar Decimal2.a_partir_de_valor"""
        return cls.a_partir_de_valor(v)

    @classmethod
    def a_partir_de_valor(cls, v: str | float | int | Decimal) -> 'Decimal2':
        """Converte um valor v pra Decimal2. Converte string com valor
        decimal formatado pt-BR como no exemplo: R$ 122.496,40 para um
        valor decimal. Se v tiver pontuada no sistema USA, com ponto no
        lugar da vírgula, faz o ajuste de acordo com o número de casas
        decimais. Converte também int, float e strings com números sem o 
        R$.

        Args:
            v: contem o valor, pode ser formatado com R$.

        Returns:
            Decimal2: return um Decimal2 contendo o valor.
        """
        if type(v) is float or type(v) is int:
            return cls(v)
        elif type(v) is Decimal:
            return cls(v)
        elif type(v) is str:
            if not v:
                return cls('0.0')
            try:
                v = v.strip().capitalize() # capitalize pra colocar R$ maiúsculo
                if not v:
                    raise ValueError('É preciso definir algum valor pra Decimal2.')

                if v.startswith(cls.RS):
                    v = v[len(cls.RS): ].strip()
                
                tam, pos_virg, pos_ponto = len(v), v.rfind(','), v.rfind('.')
                eh_padrao_br  = lambda: (pos_virg  > pos_ponto and (1 <= pos_virg  <= tam - 2)) or \
                                        (pos_virg == -1)       and (1 <= pos_ponto <  tam - cls.CASAS_DECIMAIS - 1)
                eh_padrao_usa = lambda: (pos_ponto > pos_virg  and (1 <= pos_ponto <= tam - 2))
                
                if eh_padrao_br():
                    v = v.replace('.', '').replace(',', '.')
                elif eh_padrao_usa():
                    v = v.replace(',', '')

                return cls(Decimal(v))
            except InvalidOperation as erro:
                raise InvalidOperation(f'O valor "{v}" é inválido!')
            except Exception as erro:
                print(f'{v} não é um valor aceito!')
                raise ValueError(f'{erro}')
        else:
            raise TypeError(f'Tipo do valor não aceito para Decimal2: {type(v)}.')

    def __str__(self) -> str:
        return self.__to_str()
    
    def __repr__(self) -> str:
        return self.__to_str()

    def __to_str(self) -> str:
        return f'Decimal2({str(self.valor)})'

    @staticmethod
    def setar_local_pt_br():
        """Defini o locale como pt-br pra que o decimal seja formatado corretamente pro estilo moeda.
        """
        locale.setlocale(locale.LC_MONETARY, 'pt_BR.utf8')
    
    def formatar_moeda(self, retirar_rs: bool = False) -> str:
        """Formata decimal pro estilo moeda no padrão pt_BR. É preciso no
        iníco da aplicação executar Decimal2().setar_local_pt_br.

        Returns:
            str: retorna string no formato R$ NNN.NNN.NNN,MM
        """
        try:
            r = locale.currency(self, grouping=True)
        except ValueError as erro:
            print('Problema ao formatar_moeda. Rodar Decimal2.self.setar_local_pt_br')
            raise
        
        return r if not retirar_rs else r.replace('R$ ', '')
    
    def inteiro(self) -> int:
        """Retira a parte fracionada."""
        return round(self)

    def str_inteiro(self) -> str:
        """Converte pra inteiro e retorna uma str."""
        return str(self.inteiro())


class FoneFormato(Enum):
    CAIXA_SIMULADOR = '({}){}-{}'
    COMUM = '({}) {}-{}'
    DDI_DDD_PREF_SUF = '{}({}){}-{}'
    DDI_DDD_PREF_SUF_SEM_FMT = '{}{}{}{}'
    DDD_PREF_SUF_SEM_FMT = '{}{}{}'


class FoneTam(Enum):
    CELULAR_CURTO_OU_FIXO_SEM_DDD = 8               # 9843 9775
    CELULAR_NORMAL_SEM_DDD = 9                      # 99843 9775
    DDD_CELULAR_CURTO_OU_FIXO = 10                  # 62 9843 9775
    DDD_CELULAR_NORMAL = 11                         # 62 99843 9775
    DDI_2_DIG_DDD_CELULAR_CURTO_OU_FIXO = 12        # 55 62 3375 9775
    DDI_2_DIG_DDD_CELULAR_NORMAL = 13               # 55 62 99843 9775
    DDI_3_DIG_DDD_CELULAR_NORMAL = 14               # 055 62 99843 9775
    
    MIN = CELULAR_CURTO_OU_FIXO_SEM_DDD
    MAX = DDI_3_DIG_DDD_CELULAR_NORMAL


class Fone:
    """Trata telefones, separa as partes em grupos (ver propriedade grupos) e formata.

    Raises:
        ValueError: padrao precisa ser uma string com a regex a ser analisada.
        ValueError: formato tem que ser do tipo FoneFormato.
        ValueError: o valor do fone tem que ser do tipo str.
        ValueError: fone com a quantidade de números inferior ao tamanho mínimo.
        ValueError: idem ao ValueError anterior.
        ValueError: aceita DDI apenas do Brasil.
        ValueError: idem ao anterior.
        ValueError: fone maior que o tamanho máximo permitido.
        ValueError: fone inválido.

    Returns:
        [type]: [description]
    """
    #PADRAO_NUM = '(\+\d{3})?([1-9]{1}\d{1})?(\d{4,5})(\d{4})'
    PADRAO_NUM_MAIOR = '(\+\d{3})?([1-9]{1}\d{1})?(\d{5})(\d{4})'
    PADRAO_NUM_MENOR = '(\+\d{3})?([1-9]{1}\d{1})?(\d{4})(\d{4})'
    DDI_BRASIL = '55'    
    DDD_PADRAO = '62'
    DDI_PADRAO = DDI_BRASIL

    def __init__(self, valor:str, 
                 formato: FoneFormato=FoneFormato.CAIXA_SIMULADOR, 
                 ddd_obg: bool=True) -> None:
        self._grupos: dict = {}
        self._padrao: str = ''
        self._valor: str  = ''
        self._formato: FoneFormato = formato
        self._ddd_obg = ddd_obg
        if valor:
            self.valor = valor

    @classmethod
    def a_partir_de_fmt_comum(cls, valor: str):
        return cls(valor=valor, formato=FoneFormato.COMUM)

    @classmethod
    def a_partir_de_fmt_caixa(cls, valor: str):
        return cls(valor=valor, formato=FoneFormato.CAIXA_SIMULADOR)

    @classmethod
    def a_partir_de_fmt_somente_numeros(cls, valor: str):
        return cls(valor=valor, formato=FoneFormato.DDI_DDD_PREF_SUF_SEM_FMT)

    @classmethod
    def a_partir_de_fmt_somente_numeros_sem_ddi(cls, valor: str):
        return cls(valor=valor, formato=FoneFormato.DDD_PREF_SUF_SEM_FMT)

    @property
    def padrao(self):
        return self._padrao

    @padrao.setter
    def padrao(self, v: str):
        if type(v) is not str:
            raise ValueError('Padrão precisa ser str.')
        self._padrao = v

    @property
    def formato(self):
        return self._formato
    
    @formato.setter
    def formato(self, v):
        if type(v) is not FoneFormato:
            raise ValueError('Formato do fone precisa ser do tipo FoneFormato.')
        
        self._formato = v

    @property
    def valor(self) -> str:
        return self._valor
    
    @valor.setter
    def valor(self, v: str):
        self._valor = ''
        if type(v) is not str:
            raise ValueError('O fone precisa ser str.')

        CELULAR_CURTO_OU_FIXO_SEM_DDD = FoneTam.CELULAR_CURTO_OU_FIXO_SEM_DDD.value
        if not self._ddd_obg and len(v) < CELULAR_CURTO_OU_FIXO_SEM_DDD:
            raise ValueError(f'Fone "{v}" precisa ter pelo menos {CELULAR_CURTO_OU_FIXO_SEM_DDD} números.')
        
        valor_nums: str = ''.join([c for c in v if c.isdigit()])
        tam_nums = len(valor_nums)
        if not self._ddd_obg and tam_nums < CELULAR_CURTO_OU_FIXO_SEM_DDD:
            raise ValueError(f'Fone "{v}" precisa ter pelo menos {CELULAR_CURTO_OU_FIXO_SEM_DDD} números.')
        
        DDD_CELULAR_CURTO_OU_FIXO = FoneTam.DDD_CELULAR_CURTO_OU_FIXO.value
        if self._ddd_obg and tam_nums < DDD_CELULAR_CURTO_OU_FIXO:
            raise ValueError(f'Fone "{v}" precisa ter pelo menos {DDD_CELULAR_CURTO_OU_FIXO} números, incluindo o DDD.')
        
        if (tam_nums == FoneTam.DDI_2_DIG_DDD_CELULAR_CURTO_OU_FIXO.value
            or tam_nums == FoneTam.DDI_2_DIG_DDD_CELULAR_NORMAL.value):
            # TODO: implementar tratamento de números DDI de outros países?
            if not valor_nums.startswith(self.DDI_BRASIL):
                raise ValueError(f'Aceito apenas DDI do Brasil: {self.DDI_BRASIL}.')
            else:
                valor_nums = '+0' + valor_nums

        elif tam_nums == FoneTam.DDI_3_DIG_DDD_CELULAR_NORMAL.value:
            # TODO: implementar tratamento de números DDI de outros países?
            if not valor_nums.startswith('+0' + self.DDI_BRASIL):
                raise ValueError(f'Aceito apenas DDI do Brasil: {self.DDI_BRASIL}.')
            else:
                valor_nums = "+" + valor_nums

        elif tam_nums > FoneTam.DDI_3_DIG_DDD_CELULAR_NORMAL.value:
            raise ValueError(f'Fone "{v}" precisa ser menor que o tamanho máximo com o código do país.')
        
        DDI_2_DIG_DDD_CELULAR_CURTO_OU_FIXO = FoneTam.DDI_2_DIG_DDD_CELULAR_CURTO_OU_FIXO.value

        padrao: str = ''
        if self.padrao:
            padrao = self.padrao
        elif tam_nums in (
            CELULAR_CURTO_OU_FIXO_SEM_DDD,
            DDD_CELULAR_CURTO_OU_FIXO,
            DDI_2_DIG_DDD_CELULAR_CURTO_OU_FIXO,
        ):
            padrao = self.PADRAO_NUM_MENOR
        else:
            padrao = self.PADRAO_NUM_MAIOR

        r = re.search(padrao, valor_nums)
        if not r:
            raise ValueError(f'O fone "{v}" é inválido.')

        grupo_ddi: str = ''
        grupo_ddd: str = ''

        if not r.group(1):
            #print(f'DDI não encontrado no fone "{v}" deixar vazio.')
            grupo_ddi = ''
        else:
            grupo_ddi = r.group(1)

        if not r.group(2):
            #print(f'DDD não encontrado no fone "{v}", colocando DDD padrão. {self.DDD_PADRAO}')
            grupo_ddd = self.DDD_PADRAO
        else:
            grupo_ddd = r.group(2)
        
        self._grupos['ddi'] = grupo_ddi
        self._grupos['ddd'] = grupo_ddd
        self._grupos['pref'] = r.group(3)
        self._grupos['suf'] = r.group(4)

        self._valor = valor_nums
    
    @property
    def grupos(self) -> dict:
        return self._grupos

    def remover_mais_ddi(self, ddi='') -> str:
        if not ddi: ddi = self.grupos['ddi']

        if ddi and ddi.startswith('+'):
            ddi = ddi[1:]
        
        return ddi
    
    def remover_zero_esq(self, ddi='') -> str:
        if not ddi: ddi = self.grupos['ddi']
            
        if ddi.startswith('+'):
            if len(ddi) > 1:
                ddi = '+' + str(int(ddi[1:]))
        elif len(ddi) > 0:
                ddi = str(int(ddi))

        return ddi

    def formatar(self, retirar_mais_ddi: bool = False, 
                retirar_zero_esq: bool = False) -> str:
        ddi = self.grupos['ddi']
        if retirar_mais_ddi: ddi = self.remover_mais_ddi(ddi)
        if retirar_zero_esq: ddi = self.remover_zero_esq(ddi)

        ddd =  self.grupos['ddd']
        pref = self.grupos['pref']
        suf = self.grupos['suf']

        match self._formato:
            case FoneFormato.CAIXA_SIMULADOR | FoneFormato.COMUM:
                return self._formato.value.format(ddd, pref, suf)
            case FoneFormato.DDI_DDD_PREF_SUF:
                if not ddi: ddi = self.DDI_PADRAO
                return self._formato.value.format(ddi, ddd, pref, suf)
            case FoneFormato.DDI_DDD_PREF_SUF_SEM_FMT:
                if not ddi: ddi = self.DDI_PADRAO
                return self._formato.value.format(ddi, ddd, pref, suf)
            case FoneFormato.DDD_PREF_SUF_SEM_FMT:
                return self._formato.value.format(ddd, pref, suf)


class Cpf:
    """Essa classe contêm as funções pra validação e formatação de CPF.
    """

    def __init__(self, cpf: str):
        """Construtor

        Args:
            cpf (str): string contendo CPF
        """
        self.cpf = cpf
        self._cpf_l = []
        self.validado = False

    @property
    def cpf_lista(self) -> list:
        return self._cpf_l

    def __str__(self):
        """Converte pra string sem formatação.

        Returns:
            [type]: retorna o CPF em formato string sem formatação.
        """
        return self.sem_formatacao

    def to_str(self) -> str:
        """Obsoleto, usar propriedade Cpf.sem_formatacao. Converte o CPF
        de lista pra string.

        Returns:
            str: retorna string com o CPF, sem formatação.
        """
        return self.sem_formatacao
    
    @property
    def sem_formatacao(self) -> str:
        """Str contendo o CPF sem formatação.

        Returns:
            str: retorna o CPF sem formatação.
        """
        if not self._cpf_l:
            return ''
        
        return ''.join([str(i) for i in self._cpf_l])

    def erro(self, msg: str, disparar: bool):
        if disparar:
            raise ErroCPF(msg)
        else:
            print(msg)

    def validar(self, disparar_erro: bool=True) -> bool:
        """Verifica se CPF é válido.

        Args:
            cpf (str): CPF a ser verificado
            disparar_erro (bool, optional): Quando True dispara erro, se falso
            mostra mensagem com o erro. Defaults to True.

        Raises:
            ValueError: CPF vazio
            ValueError: quando total de números menor que 11
            ValueError: todos os números iguais
            ValueError: falha primeiro dígito verificador
            ValueError: falha segundo dígito verificador

        Returns:
            bool: retorna True quando válido; guarda em self._cpf_l o CPF, apenas com números 
            no formato lista, caso disparar_erro=False retorna False
        """
        self.validado = False
        cpf = self.cpf
        self._cpf_l = []
        if not cpf:
            self.erro('Favor digitar CPF.', disparar_erro)
            return False
        
        cpf_l = [int(c) for c in cpf if c.isdigit()]

        tam_cpf = len(cpf_l)
        if tam_cpf != 11:
            self.erro('CPF precisa ter 11 números.', disparar_erro)
            return False

        for num in cpf_l:
            if num != cpf_l[0]: break
        else:
            self.erro('CPF não pode ter todos os números iguais.', disparar_erro)
            return False
            
        mult = lambda num1, num2: num1 * num2

        seq_10_2 = list(range(10, 1, -1))
        soma = sum(map(mult, cpf_l, seq_10_2))
        resto = (soma * 10) % 11
        if resto == 10: resto = 0
        if resto != cpf_l[9]:
            self.erro(f'CPF {cpf} inválido, verifique se o número está correto.', disparar_erro)
            return False
        
        seq_11_2 = list(range(11, 1, -1))
        soma = sum(map(mult, cpf_l, seq_11_2))
        resto = (soma * 10) % 11
        if resto == 10: resto = 0
        if resto != cpf_l[10]:
            self.erro(f'CPF {cpf} inválido, verifique os números do CPF', disparar_erro)
            return False
        
        self._cpf_l = cpf_l
        self.validado = True
        return True
        
    def formatar(self) -> str:
        """Retorna o CPF formatado como str. Primeiro é preciso validar o CPF através do método validar().

        Returns:
            str: retorna uma str contendo o CPF formatado
        """
        if not self.validado:
            self.validar()

        if not self._cpf_l:
            return ''

        cpf_l = self._cpf_l
        cpf = ''
        for i, c in enumerate(cpf_l):
            cpf += str(c)
            match i:
                case 2 | 5:
                    cpf += '.'
                case 8:
                    cpf += '-'

        return cpf


def test():
    cpfs = ('529.982.247-25', '529.982.247-22', '000/802;871;07', '111.111.111-11', '222.222.222-22')

    for s_cpf in cpfs:
        cpf = Cpf(s_cpf)
        b = cpf.validar(disparar_erro=False)
        print(f'CPF válido ? {b=}')
        print(f'{cpf.cpf_lista=}')
        print()


    try:
        print(f"{Cpf('777.777.777-77').validar(disparar_erro=True)=}")
    except ValueError as erro:
        print(f'{erro}')

    try:
        print(f"{Cpf('32sad12fa3 458789s').validar()=}")    
    except ValueError as erro:
        print(f'{erro}')


def email_valido(email: str) -> bool:
    """Verifica se e-mail é válido, caso contrário dispara um erro.

    Args:
        email (str): endereço de e-mail.

    Raises:
        TypeError: tipo de email precisa ser str.
        ErroEmail: detectado espaços no email.
        ErroEmail: não tem arroba em email.
        ErroEmail: email curto.
        ErroEmail: sem sinal de ponto.
        ErroEmail: email inválido.

    Returns:
        bool: retorna True se e-mail for válido.
    """
    if type(email) != str:
        raise TypeError('Tipo e-mail precisa ser str.')
    
    if ' ' in email:
        raise ErroEmail('E-mail não contém espaços')

    email = email.lower()
    l_email: list = email.split('@')
    if len(l_email) != 2:
        raise ErroEmail('Favor digitar um sinal de @ no endereço de e-mail')
    if len(l_email[0]) < 3:
        raise ErroEmail('E-mail muito curto.')
    
    l_email_parte2: list = l_email[1].split('.')
    if len(l_email_parte2) < 2:
        raise ErroEmail(
            'Favor digitar um sinal de ponto na segunda parte do e-mail.')
    if len(l_email_parte2[0]) < 3 or len(l_email_parte2[1]) < 2:
        raise ErroEmail('E-mail inválido.')

    return True


def sobrenome_aleatorio(nome: str) -> str:
    """Retorna um sobrenome aleatório a partir de uma lista.

    Args:
        nome (str): nome a ser verificado se tem

    Returns:
        str: nome com o sobrenome caso não tenha.
    """
    nome = nome.strip()
    if ' ' in nome:
        ns = nome.split(' ')
        if len(ns) == 2:
            if len(ns[1]) > 1:
                return nome
        if len(ns) == 3:
            if len(ns[2]) > 1:
                return nome
            
    sobrenomes: tuple = (
        'Souter', 'Vanderbouer', 'Lian', 'Cardoso', 'Santana', 'Moura', 
        'Antunes', 'Aurora', 'Roma', 'Conde', 'Brito', 'Cordeiro'
    )
    ind: int = randint(0, len(sobrenomes)-1)
    return f'{nome} {sobrenomes[ind]}'


def email_aleatorio() -> str:
    nomes: tuple = (
        'chiriro', 'kobaiashi', 'artenusa', 'roberta', 'maris', 'augustino',
        'mooureira', 'martal'
    )
    nomes_comp: tuple = (
        '_78', '', 'jky', '984', '.abc', '.1598', '2228', '_tom321', '.kp15', '_5xy'
    )
    provedores: tuple = (
        'gmail.com', 'hotmail.com', 'yahoo.com', 'uol.com.br'
    )
    
    ind_nome: int = randint(0, len(nomes)-1)
    ind_nome_comp: int = randint(0, len(nomes_comp)-1)
    ind_provedores: int = randint(0, len(provedores)-1)

    return f'{nomes[ind_nome]}{nomes_comp[ind_nome_comp]}@{provedores[ind_provedores]}'

def test2():
    n = '62 99987 4322'
    
    print(f'{Fone.a_partir_de_fmt_somente_numeros(n).formatar()=}')
    print(f'{Fone.a_partir_de_fmt_somente_numeros_sem_ddi(n).formatar()=}')    
    print(f'{Fone.a_partir_de_fmt_caixa(n).formatar()=}')
    print(f'{Fone.a_partir_de_fmt_comum(n).formatar()=}')


if __name__ == '__main__':
    #test()
    test2()