#!/usr/bin/env python
# coding: utf-8

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.4'

from flask import Flask, Blueprint
from flask_restx import Api

class Server:
    def __init__(self):
        self.app = Flask(__name__)
        self.blueprint = Blueprint('api', __name__, url_prefix='/api')
        self.api = Api(self.blueprint,
            version='1.2', 
            title='Simóvel API',
            Description='API para efetuar processo de simulação de crédito imobiliário.',
            doc='/docs'
        )
        self.app.register_blueprint(self.blueprint)

    def run(self):
        self.app.run('0.0.0.0', 8080)

server = Server()

#ns = api.namespace('integracao', description='Integração do bot com o simulador.')
#
#@ns.route('/ola')
#class Ola(Resource):
#    def get(self):
#        return {'ola': 'mundo'}


#def main():
#    app.run('0.0.0.0', 8080)

#if __name__ == '__main__':
#    main()