from flask import Blueprint
from flask_restx import Api

from rest_api.apis.ns_v1 import api as ns_v1

blueprint = Blueprint('api', __name__, url_prefix='/api/v1')
api = Api(blueprint,
    title='Simóvel API',
    version='1.1',
    description='API para efetuar processo de simulação de crédito imobiliário.'
)

api.add_namespace(ns_v1)
