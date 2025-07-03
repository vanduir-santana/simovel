#!/usr/bin/env python
# coding: utf-8
"""API Simulador de Crédito Imobiliário
"""
__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.7'

from flask import Flask
from flask_migrate import Migrate
from config.geral import Parametros
from rest_api.api_v1 import blueprint as api_v1
from rest_api.api_multi360 import blueprint as api_multi360
from rest_api.models.simulacao import PessoaModel, EstadoModel, CidadeModel
from rest_api.models.integracao import Multi360Model
from sims.caixa import SimuladorCaixa
from rest_api.db import db, migrate
from rest_api.ma import ma
import locale


app = Flask(__name__)
app.register_blueprint(api_v1)
app.register_blueprint(api_multi360)

app.config['SQLALCHEMY_DATABASE_URI'] = Parametros.DATABASE_URI
app.config['PROPAGATE_EXCEPTION'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


#@app.before_first_request
@app.before_request
def antes_primeira_req():
    # a linha seguinte ira remover este handler, fazendo ele executar
    # somente uma vez
    # cria banco de dados
    db.create_all()

    # popular tabela de estados se estiver vazia
    if EstadoModel.contar() == 0:
        print('Não encontrou registros de estados, criando a partir do csv...')
        EstadoModel.inserir_estados()
    
    # popular cidades com dados obtidos do simulador da caixa
    if CidadeModel.contar() == 0:
        print('Não encontrou nenhuma cidade no banco de dados, criando...')
        # por enquanto popula cidades somente do estado de Goiás
        uf: str = 'GO'
        estado_id: int = EstadoModel.obter_id_por_uf(uf)
        sim = SimuladorCaixa()
        sim.obter_cidades(uf)
        if estado_id == 0 and not sim.cidades:
            # TODO: implementar tratamento de erros
            pass
        else:
            cidades: list[dict] = sim.cidades
            for cidade in cidades:
                cidade['estado_id'] = estado_id
            CidadeModel.inserir_cidades(cidades)


def habilitar_fk_sqlite():
    """Pro sqlite é preciso habilitar o uso de FOREIGN KEY toda vez no
    início (quando vai conectar no DB).
    """
    def _fk_pragma_on_connect(dbapi_con, con_record):  # noqa
        dbapi_con.execute('PRAGMA foreign_keys=ON')

    with app.app_context():
        from sqlalchemy import event
        event.listen(db.engine, 'connect', _fk_pragma_on_connect)


def main() -> Flask:
    """Função  de  início  do  Flask.  Retorna  um objeto Flask pra ser
    chamado   pelo  gunicorn.  Usado  também  pra  iniciar  através  do
    webserver de testes do flask.

    Returns:
        Flask: retorna objeto a ser consumido pelo gunicorn.
    """
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    habilitar_fk_sqlite()
    locale.setlocale(locale.LC_MONETARY, 'pt_BR.utf8')
    return app


if __name__ == '__main__':
    main().run('0.0.0.0', 8080)
