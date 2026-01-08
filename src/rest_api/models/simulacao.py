"""Modelos das tabelas do simulador
"""
__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.9'


from rest_api.db import db
from decimal import Decimal
from simovel.util import csv_pra_lista_de_dic
from datetime import date, datetime
from simovel.config.geral import Parametros

UFS_CSV = Parametros.UFS_CSV


class BaseModel(db.Model):
    __abstract__ = True
    
    def inserir(self):
        """Insere informações no banco de dados.
        """
        db.session.add(self)
        db.session.commit()
    
    def adicionar(self):
        """Alias pra inserir.
        """
        self.inserir()

    def excluir(self):
        """Exclui registro do banco de dados.
        """
        db.session.delete(self)
        db.session.commit()
    
    def atualizar(self):
        """Quando alterar um registro é preciso efetuar o commit.
        """
        db.session.commit()

    def descartar(self):
        """Descarta alterações
        """
        db.session.rollback()


class PessoaModel(BaseModel):
    __tablename__ = 'pessoa'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), index=True)
    cpf = db.Column(db.String(11), index=True)
    fone = db.Column(db.String(14), index=True)
    data_nasc = db.Column(db.Date)
    data_nasc_conjuge = db.Column(db.Date)                  # brad.
    possui_imovel_cidade = db.Column(db.Boolean)
    tres_anos_fgts = db.Column(db.Boolean)
    mais_de_um_comprador_dependente = db.Column(db.Boolean) # brad. = somar renda cônjuge
    servidor_publico = db.Column(db.Boolean)
    estado_id   = db.Column(db.Integer, db.ForeignKey('estado.id'))
    cidade_id   = db.Column(db.Integer, db.ForeignKey('cidade.id'))
    estado      = db.relationship('EstadoModel', uselist=False)
    cidade      = db.relationship('CidadeModel', uselist=False)
    simulacoes  = db.relationship('SimulacaoModel', backref=db.backref('pessoa'), 
                        order_by='desc(SimulacaoModel.id)')
    # relacionamento da integração com o bot multi360
    multi360    = db.relationship('Multi360Model', back_populates='pessoa',
                                  uselist=False)

    def __init__(self, nome: str, cpf: str):
        self.nome = nome
        self.cpf = cpf

    def __repr__(self):
        return (
            f'Nome: {self.nome}'
            f'CPF: {self.cpf}'
            f'Fone: {self.nome}'
            f'UF: {self.estado.uf}'
            f'Cidade: {self.cidade.nome}'
            f'Cód. Cidade Caixa: {self.cidade.cod_caixa}'
            f'Data nasc.: {self.data_nasc}'
        )

    def json(self):
        return {
            'nome': self.nome, 
            'cpf': self.cpf, 
            'fone': self.nome, 
            'uf': self.estado.uf,
            'cod_cidade_caixa': self.cidade.cod_caixa, 
            'data_nasc': self.data_nasc,
        }

    @classmethod
    def buscar_por_cpf(cls, cpf: str) -> object:
        return cls.query.filter(cls.cpf == cpf).first()

    @classmethod
    def buscar_por_fone(cls, fone: str) -> object:
        #return cls.query.filter_by(cls.fone == fone).first()
        return cls.query.filter(cls.fone == fone).first()


class SimulacaoModel(BaseModel):
    __tablename__ = 'simulacao'
    
    id = db.Column(db.Integer, primary_key=True)
    # value enum banco corresp.
    banco = db.Column(db.Integer)
    # TODO:  implementar outros bancos além da Caixa
    # Caixa: RESIDENCIAL = 1, COMERCIAL 2
    # Bradesco idem a Caixa, porém tem o RESIDENCIAL_POUPANCA = 14
    # Itaú S: implementar com os msms códigos da Caixa
    tipo_imovel = db.Column(db.Integer)
    tipo_financiamento = db.Column(db.Integer)
    # brad. (situação imóvel): cód. dif.
    tipo_financiamento_bradesco = db.Column(db.Integer)
    renda_bruta = db.Column(db.Float(precision=2, asdecimal=True))
    # brad. = valor_financiamento
    valor_imovel = db.Column(db.Float(precision=2, asdecimal=True))
    # itaú e santander api L
    valor_entrada = db.Column(db.Float(precision=2, asdecimal=True))
    opcao_financiamento = db.Column(db.String(9))
    data = db.Column(db.DateTime, index=True, default=datetime.now)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'))
    
    @classmethod
    def a_partir_de_banco(cls, banco: int) -> 'SimulacaoModel':
        sim_model: SimulacaoModel = cls()
        sim_model.banco = banco
        return sim_model

    @classmethod
    def a_partir_tipo_financiamento(cls, tipo_financiamento: int) -> 'SimulacaoModel':
        sim_model: SimulacaoModel = cls()
        sim_model.tipo_financiamento = tipo_financiamento
        return sim_model

    @classmethod
    def a_partir_tipo_financiamento_bradesco(cls,
                    tipo_financiamento_brad: int) ->  'SimulacaoModel':
        sim_model: SimulacaoModel = cls()
        sim_model.tipo_financiamento_bradesco = tipo_financiamento_brad
        return sim_model
    

    #@classmethod
    #def get_ult_registro(cls, pessoa_id: int) -> object:
    #    return cls.query.filter(cls.pessoa_id == pessoa_id).first().order_by(SimulacaoModel.id.desc())

    def __repr__(self):
        return (
            f'Tipo Financiamento: {self.tipo_financiamento}\n'
            f'Renda Familiar: {self.renda_bruta}\n'
            f'Valor do imóvel: {self.valor_imovel}\n'
            f'Opção de financiamento: {self.opcao_financiamento}\n'
            f'Data: {self.data}'
        )
    
    def json(self):
        return {
            'tipo_financiamento': self.tipo_financiamento,
            'renda_familiar': self.renda_bruta,
            'valor_imovel': self.valor_imovel,
            'opcao_financiamento': self.opcao_financiamento,
            'data': self.data
        }
    
    @classmethod
    def filtrar_por_intervalo_data(cls, dt_inicial: date, dt_final: date) -> list[object]:
        # TODO:  é preciso converter data pra str no formato yyyy-mm-dd
        # ou já receber os parâmetros nesse formato
        return cls.query.filter(cls.data.between(dt_inicial, dt_final))
    

class EstadoModel(BaseModel):
    __tablename__ = 'estado'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(20), index=True, nullable=False, unique=True)
    uf = db.Column(db.String(2), index=True, nullable=False, unique=True)
    cidades = db.relationship('CidadeModel', backref=db.backref('estado'))

    def __init__(self) -> None:
        # não precisa add estado, são adicionados de uma vez, já q não mudam
        pass

    @classmethod
    def contar(cls) -> int:
        return cls.query.count()

    @classmethod
    def buscar_por_uf(cls, uf: str) -> object:
        uf = uf.upper()
        return cls.query.filter(cls.uf == uf).first()

    @classmethod
    def inserir_estados(cls, lista_estados: list | None=None) -> bool:
        """
        Insere estados a partir de uma lista de dicionários. Caso não
        seja passado uma lista com os estados serão importados de um
        arquivo csv.
        """
        if not lista_estados:
            nomes_campos = ('nome', 'uf')
            lista_estados = csv_pra_lista_de_dic(
                UFS_CSV, 
                nomes_campos=nomes_campos
            )

            if not lista_estados:
                return False

        db.session.bulk_insert_mappings(cls, lista_estados)
        db.session.commit()

        return True
    
    @classmethod
    def obter_id_por_uf(cls, uf: str) -> int:
        """Obtém id a partir da UF.
        """
        if not uf:
            return 0
        
        uf = uf.upper()
        return db.session.query(EstadoModel.id).filter(EstadoModel.uf == uf).first()[0]

    @classmethod
    def obter_cidades(cls, uf: str='GO', lista_dicts: bool=True) -> list:
        """
        Obtém cidades como uma lista de dicionários.
        Se :lista_dicts True retorna uma lista de dicionários, caso
        contrário retorna uma lista de tuplas (útil pra usar com a lib
        NGram).

        Args:
            uf (str, optional): UF de onde serão obtidas as cidades.
              Defaults to 'GO'.
            lista_dicts (bool, optional): quando True retonra uma lista
              dicionário se for False retorna uma lista de tuplas.
              Defaults to True.

        Returns:
            list: retorna uma lista de dicionários ou de tuplas,
              depende do parâmetro lista_dicts
        """
        if not uf:
            print('Precisa setar UF pra obter cidades.')
            return []
    
        uf = uf.upper()
        estado_model = cls.query.filter(cls.uf == uf).first()

        if not estado_model:
            print(f'Não encontrou cidades pra UF: {uf}')
            return []

        if lista_dicts:
            return [cidade.json() for cidade in estado_model.cidades]
        else:
            return [cidade.tupla() for cidade in estado_model.cidades]


class CidadeModel(BaseModel):
    __tablename__ = 'cidade'

    id = db.Column(db.Integer, primary_key=True)
    cod_caixa = db.Column(db.Integer, unique=True)
    nome = db.Column(db.String(150), index=True, nullable=False)
    nome_sem_aspa = db.Column(db.String(150), index=True, nullable=False)
    estado_id = db.Column(db.Integer, db.ForeignKey('estado.id'), nullable=False)

    def __init__(self, cod_caixa: int, nome: str) -> None:
        self.cod_caixa = cod_caixa
        self.nome = nome

    def json(self):
        return {
            'id': self.id,
            'cod_caixa': self.cod_caixa,
            'nome': self.nome,
            'nome_sem_aspa': self.nome_sem_aspa
        }
    
    def tupla(self):
        """Retorna campos em formato de tupla pra ser utilizado com NGram."""
        return (
            self.id,
            self.cod_caixa,
            self.nome,
            self.nome_sem_aspa
        )

    @classmethod
    def contar(cls) -> int:
        return cls.query.count()

    @classmethod
    def buscar_por_nome(cls, nome: str) -> object:
        # TODO: talvez seja preciso testar o estado pois pd existir
        # cidades com mesmo nome em estados diferentes
        return cls.query.filter(cls.nome == nome).first()

    @classmethod
    def buscar_por_id(cls, id: int) -> object:
        """Busca cidade a partir do id."""
        return cls.query.filter(cls.id == id).first()
    
    @classmethod
    def inserir_cidades(cls, lista_cidades: list[dict]) -> bool:
        """Insere cidades a partir de uma lista de dicionários.
        """
        if not lista_cidades:
            return False

        db.session.bulk_insert_mappings(cls, lista_cidades)
        db.session.commit()

        return True
