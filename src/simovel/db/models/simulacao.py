"""Modelos das tabelas do simulador
"""
from __future__ import annotations

from simovel.exceptions import ErroResultadoCampoNaoRetornado

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.11'

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING, Self
import warnings

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Integer,
    String,
    Date,
    DateTime,
    Boolean,
    Numeric,
    ForeignKey,
    desc,
    select,
    func
)

from simovel.config.geral import Parametros
from simovel.util import csv_pra_lista_de_dic
from simovel.db.base import Base
from simovel.db.types import SessionType

if TYPE_CHECKING:
    from simovel.db.models.integracao import Multi360Model

UFS_CSV = Parametros.UFS_CSV


class BaseModel(Base):
    __abstract__ = True

    # def inserir(self):
    #     """Insere informações no banco de dados.
    #     """
    #     db.session.add(self)
    #     db.session.commit()
    #
    # def adicionar(self):
    #     """Alias pra inserir.
    #     """
    #     self.inserir()
    #
    # def excluir(self):
    #     """Exclui registro do banco de dados.
    #     """
    #     db.session.delete(self)
    #     db.session.commit()
    #
    # def atualizar(self):
    #     """Quando alterar um registro é preciso efetuar o commit.
    #     """
    #     db.session.commit()


class PessoaModel(BaseModel):
    __tablename__ = 'pessoa'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), index=True)
    cpf: Mapped[str] = mapped_column(String(11), index=True)
    fone: Mapped[str] = mapped_column(String(14), index=True)
    data_nasc: Mapped[date] = mapped_column(Date)
    data_nasc_conjuge: Mapped[date] = mapped_column(Date)    # brad.
    possui_imovel_cidade: Mapped[bool] = mapped_column(Boolean)
    tres_anos_fgts: Mapped[bool] = mapped_column(Boolean)
    # brad. = somar renda cônjuge
    mais_de_um_comprador_dependente: Mapped[bool] = mapped_column(Boolean)
    servidor_publico: Mapped[bool] = mapped_column(Boolean)
    estado_id: Mapped[int] = mapped_column(Integer, ForeignKey('estado.id'))
    cidade_id: Mapped[int] = mapped_column(Integer, ForeignKey('cidade.id'))
    estado: Mapped["EstadoModel"] = relationship('EstadoModel', uselist=False)
    cidade: Mapped["CidadeModel"] = relationship('CidadeModel', uselist=False)

    simulacoes: Mapped[List["SimulacaoModel"]] = relationship(
        'SimulacaoModel',
        back_populates='pessoa',
        order_by=lambda: desc(SimulacaoModel.id)
    )
    
    # relacionamento da integração com o bot multi360
    multi360: Mapped[Optional["Multi360Model"]] = relationship(
        'Multi360Model',
        back_populates='pessoa',
        uselist=False
    )

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
    def buscar_por_cpf(cls, session: SessionType, cpf: str) -> object:
        return session.query(cls).filter(cls.cpf == cpf).first()

    @classmethod
    def buscar_por_fone(cls, session: SessionType, fone: str) -> object:
        return session.query(cls).filter(cls.fone == fone).first()


class SimulacaoModel(BaseModel):
    __tablename__ = 'simulacao'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # value enum banco corresp.
    banco: Mapped[int] = mapped_column(Integer)
    # TODO:  implementar outros bancos além da Caixa
    # Caixa: RESIDENCIAL = 1, COMERCIAL 2
    # Bradesco idem a Caixa, porém tem o RESIDENCIAL_POUPANCA = 14
    # Itaú S: implementar com os msms códigos da Caixa
    tipo_imovel: Mapped[int] = mapped_column(Integer)
    tipo_financiamento: Mapped[int] = mapped_column(Integer)
    # brad. (situação imóvel): cód. dif.
    tipo_financiamento_bradesco: Mapped[int] = mapped_column(Integer)
    renda_bruta: Mapped[Decimal] = mapped_column(Numeric(precision=2, scale=2))
    # brad. = valor_financiamento
    valor_imovel: Mapped[Decimal] = mapped_column(
        Numeric(precision=2, scale=2)
    )
    # itaú e santander api L
    valor_entrada: Mapped[Decimal] = mapped_column(
        Numeric(precision=2, scale=2)
    )
    opcao_financiamento: Mapped[str] = mapped_column(String(9))
    data: Mapped[datetime] = mapped_column(
        DateTime,
        index=True,
        default=datetime.now
    )
    pessoa_id: Mapped[int] = mapped_column(Integer, ForeignKey('pessoa.id'))

    pessoa: Mapped["PessoaModel"] = relationship(
        "PessoaModel",
        back_populates="simulacoes"
    )
    
    @classmethod
    def a_partir_de_banco(cls, banco: int) -> 'SimulacaoModel':
        sim_model: SimulacaoModel = cls()
        sim_model.banco = banco
        return sim_model

    @classmethod
    def a_partir_tipo_financiamento(
        cls,
        tipo_financiamento: int
    ) -> 'SimulacaoModel':
        sim_model: SimulacaoModel = cls()
        sim_model.tipo_financiamento = tipo_financiamento
        return sim_model

    @classmethod
    def a_partir_tipo_financiamento_bradesco(
        cls,
        tipo_financiamento_brad: int
    ) ->  'SimulacaoModel':
        sim_model: SimulacaoModel = cls()
        sim_model.tipo_financiamento_bradesco = tipo_financiamento_brad
        return sim_model
    
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
    def filtrar_por_intervalo_data(
        cls, session: SessionType,
        dt_inicial: date,
        dt_final: date
    ) -> list[Self]:
        # TODO:  é preciso converter data pra str no formato yyyy-mm-dd
        # ou já receber os parâmetros nesse formato
        #return cls.query.filter(cls.data.between(dt_inicial, dt_final))
        return (
            session.query(cls)
            .filter(cls.data.between(dt_inicial, dt_final))
            .all()
        )
    

class EstadoModel(BaseModel):
    __tablename__ = 'estado'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False,
        unique=True
    )
    uf: Mapped[str] = mapped_column(
        String(2),
        index=True,
        nullable=False,
        unique=True
    )
    cidades = relationship('CidadeModel', back_populates='estado')

    def __init__(self) -> None:
        # não precisa add estado, são adicionados de uma vez, já q não mudam
        pass

    @classmethod
    def contar(cls, session: SessionType) -> int:
        return session.query(cls).count()

    @classmethod
    def buscar_por_uf(cls, session: SessionType, uf: str) -> Self | None:
        warnings.warn(
            "Essa função está depreciada, utilize 'Cidade.obter_cidades_por_uf'.",
            category=DeprecationWarning,
            stacklevel=2
        )
        uf = uf.upper()
        return session.query(cls).filter(cls.uf == uf).first()


    @classmethod
    def inserir_estados(
        cls,
        session: SessionType,
        lista_estados: list | None=None
    ) -> bool:
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

        session.bulk_insert_mappings(cls.__mapper__, lista_estados)
        session.commit()

        return True
    
    @classmethod
    def obter_id_por_uf(cls, session: SessionType, uf: str) -> int:
        """
        Obtém id a partir da UF.
        """
        if not uf:
            return 0
        
        uf = uf.upper()
        estado_id = (
            session
            .query(cls.id)
            .filter(cls.uf == uf)
            .scalar()
        )

        return estado_id or 0

    # @classmethod
    # def obter_cidades(
    #     cls,
    #     session: SessionType,
    #     uf: str='GO',
    #     lista_dicts: bool=True
    # ) -> list[CidadeModel]:
    #     """
    #     Obtém cidades como uma lista de dicionários.
    #     Se :lista_dicts True retorna uma lista de dicionários, caso
    #     contrário retorna uma lista de tuplas (útil pra usar com a lib
    #     NGram).
    #
    #     Args:
    #         uf (str, optional): UF de onde serão obtidas as cidades.
    #           Defaults to 'GO'.
    #         lista_dicts (bool, optional): quando True retorna uma lista
    #           de dicionários, se for False retorna uma lista de tuplas.
    #           Defaults to True.
    #
    #     Returns:
    #         list: retorna uma lista de dicionários ou de tuplas,
    #           depende do parâmetro lista_dicts
    #     """
    #     warnings.warn(
    #         "Depracated. Esse método será mantido por compatibilidade. Uma "
    #         "versão mais moderna é 'CidadeModel.obter_cidades_por_uf'.",
    #         DeprecationWarning,
    #         stacklevel=2
    #     )
    #
    #     if not uf:
    #         print('Precisa setar UF pra obter cidades.')
    #         return []
    #
    #     uf = uf.upper()
    #     estado_model = session.query(cls).filter(cls.uf == uf).first()
    #
    #     if not estado_model:
    #         print(f'Não encontrou cidades pra UF: {uf}')
    #         return []
    #
    #     if lista_dicts:
    #         return [cidade.to_dict() for cidade in estado_model.cidades]
    #     else:
    #         return [cidade.tupla() for cidade in estado_model.cidades]


class CidadeModel(BaseModel):
    __tablename__ = 'cidade'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cod_caixa: Mapped[int] = mapped_column(Integer, unique=True)
    nome: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    nome_sem_aspa: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False
    )
    estado_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('estado.id'),
        nullable=False
    )

    estado: Mapped["EstadoModel"] = relationship(
        back_populates="cidades"
    )

    def __init__(self, cod_caixa: int, nome: str) -> None:
        self.cod_caixa = cod_caixa
        self.nome = nome

    def json(self):
        warnings.warn(
            "Depreciado. Em vez disso usar 'to_dict'.",
            category=DeprecationWarning,
            stacklevel=2
        )
        return self.to_dict()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'cod_caixa': self.cod_caixa,
            'nome': self.nome,
            'nome_sem_aspa': self.nome_sem_aspa
        }

    @staticmethod
    def cidades_to_list(cidades: list[CidadeModel]) -> list[dict]:
        """
        Retorna lista de cidades no formato de dicionário.
        """
        return [cidade.to_dict() for cidade in cidades]
    
    def tupla(self):
        """Retorna campos em formato de tupla pra ser utilizado com NGram."""
        return (
            self.id,
            self.cod_caixa,
            self.nome,
            self.nome_sem_aspa
        )

    @classmethod
    def contar(cls, session: SessionType) -> int:
        """Conta todas as cidades existentes."""
        return session.query(cls).count()

    @classmethod
    def contar_pof_uf(cls, session: SessionType, uf: str) -> int:
        """Contar cidades por UF."""
        # nos novos métodos usar o padrão do sqlalchemy 2.0
        uf = uf.upper()
        if not uf:
            print('É preciso definir UF antes de chamar contar_por_uf()')
            return 0

        stmt = (
            select(func.count())
            .select_from(cls)
            .join(EstadoModel, cls.estado_id == EstadoModel.id)
            .where(EstadoModel.uf == uf)
        )

        return session.scalar(stmt) or 0

    @classmethod
    def buscar_por_nome(cls, session: SessionType, nome: str) -> Self | None:
        # TODO: talvez seja preciso testar o estado pois pd existir
        # cidades com mesmo nome em estados diferentes
        return session.query(cls).filter(cls.nome == nome).first()


    @classmethod
    def buscar_por_id(cls, session: SessionType, id: int) -> Self | None:
        """Busca cidade a partir do id."""
        return session.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def inserir_cidades(
        cls,
        session: SessionType,
        lista_cidades: list[dict]
    ) -> bool:
        """Insere cidades a partir de uma lista de dicionários.
        """
        if not lista_cidades:
            return False

        session.bulk_insert_mappings(
            cls.__mapper__,
            lista_cidades
        )
        session.commit()

        return True

    @staticmethod
    def obter_cidades_por_uf(
        session: SessionType,
        uf: str
    ) -> list[CidadeModel]:
        """
        Obtem cidades por UF.

        Esse método traz todas as cidades a partir de uma UF. Ele
        substitui o método
        """
        uf = uf.upper()

        if not uf:
            print(
                'Não é possível obter cidades por UF se a UF não for '
                'passada como parâmetro!'
            )
            return []

        cidades: list[CidadeModel] = (
            session
            .query(CidadeModel)
            .join(CidadeModel.estado)
            .filter(EstadoModel.uf == uf)
            .all()
        )

        if not cidades:
            return []

        return cidades


