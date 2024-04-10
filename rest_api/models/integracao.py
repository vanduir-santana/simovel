"""Modelos de tabelas de integrção
"""

__version__ = 0.4
__author__ = 'Vanduir Santana Medeiros'

from rest_api.db import db
from rest_api.models.simulacao import BaseModel

class Multi360Model(BaseModel):
    __tablename__ = 'multi360'

    # campos específicos das requisições do bot
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(8), nullable=False)              # WHATSAPP, FACEBOOK, SITE
    key = db.Column(db.String(14), index=True, nullable=False)  # núm. fone ou cód. canal do cliente

    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'))
    pessoa = db.relationship('PessoaModel', back_populates='multi360')

    def __init__(self, type: str, key: str):
        self.type = type
        self.key = key

    @classmethod
    def buscar_por_key(cls, key: str) -> object:
        return cls.query.filter(cls.key == key).first()