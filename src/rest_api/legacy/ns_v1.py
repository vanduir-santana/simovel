__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.5'

from flask import Blueprint, jsonify

from simovel.db.models.simulacao import CidadeModel
from rest_api.db import get_session

api_v1 = Blueprint('simulador', __name__)


@api_v1.get('/teste')
def teste():
    return jsonify({'olá': 'mundão'})


@api_v1.get("/uf/<string:uf>/cidades")
def obter_cidades_por_uf(uf: str): 
    """
    Obtem todas as cidades de uma determinada UF.
    """
    with get_session() as session:
        cidades: list[CidadeModel] = CidadeModel.obter_cidades_por_uf(
            session,
            uf
        )

        if not cidades:
            return jsonify([]), 200

    return jsonify(CidadeModel.cidades_to_list(cidades))
