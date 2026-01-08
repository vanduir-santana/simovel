"""
Esse módulo retorna um app para ser usado em app.py ou fora, através,
por exemplo de um script de terminal.
"""

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.2'


from flask import Flask
from sqlalchemy import event
import locale

from simovel.config.geral import Parametros
from rest_api.db import db, migrate
from rest_api.ma import ma


def habilitar_fk_sqlite(app: Flask):
    """
    Pro sqlite é preciso habilitar o uso de FOREIGN KEY toda vez no
    início (quando vai conectar no DB).
    """
    def _fk_pragma_on_connect(dbapi_con, con_record):
        dbapi_con.execute('PRAGMA foreign_keys=ON')

    event.listen(db.engine, 'connect', _fk_pragma_on_connect)


def create_app() -> Flask:
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = Parametros.DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PROPAGATE_EXCEPTION'] = True

    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)

    # imports tardios para evitar circular import
    from rest_api.api_v1 import blueprint as api_v1
    from rest_api.api_multi360 import blueprint as api_multi360

    app.register_blueprint(api_v1)
    app.register_blueprint(api_multi360)

    with app.app_context():
        habilitar_fk_sqlite(app)

    locale.setlocale(locale.LC_MONETARY, 'pt_BR.utf8')
    return app
