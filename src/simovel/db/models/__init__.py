from simovel.db.base import Base

from simovel.db.models.simulacao import (
    PessoaModel,
    EstadoModel,
    CidadeModel,
    SimulacaoModel,
)

from simovel.db.models.integracao import Multi360Model

__all__ = [
    "PessoaModel",
    "EstadoModel",
    "CidadeModel",
    "SimulacaoModel",
    "Multi360Model",
]


# força a configuração dos mappers
Base.registry.configure()
