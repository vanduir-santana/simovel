__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.4'

from flask_restx import Namespace, Resource

api = Namespace('simulador', 'Namespace de Simóvel API v1')

cidades_lista = [
    {'cod': 1, 'nome': 'goiania'}, 
    {'cod': 2, 'nome': 'abadiania'},
    {'cod': 3, 'nome': 'itaberai'}
]

@api.route('/teste')
class Teste(Resource):
    def get(self,):
        return {'olá': 'mundão'}

@api.route('/cidades')
class CidadeLista(Resource):
    def get(self):
        return cidades_lista