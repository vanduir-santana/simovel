"""Modelos de tabelas de integrção
"""

__version__ = 0.6
__author__ = 'Vanduir Santana Medeiros'

from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey

from simovel.db.models.simulacao import PessoaModel
from simovel.db.types import SessionType
from simovel.db.base import Base


class Multi360Model(Base):
    __tablename__ = 'multi360'

    # campos específicos das requisições do bot
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # WHATSAPP, FACEBOOK, SITE
    type: Mapped[str] = mapped_column(String(8), nullable=False)
    # núm. fone ou cód. canal do cliente
    key: Mapped[str] = mapped_column(String(14), index=True, nullable=False)

    pessoa_id: Mapped[int] = mapped_column(Integer, ForeignKey('pessoa.id'))
    pessoa: Mapped['PessoaModel'] = relationship(back_populates='multi360')

    def __init__(self, type: str, key: str):
        self.type = type
        self.key = key

    @classmethod
    def buscar_por_key(cls, session: SessionType, key: str) -> Optional['Multi360Model']:
        return session.query(cls).filter(cls.key == key).first()
