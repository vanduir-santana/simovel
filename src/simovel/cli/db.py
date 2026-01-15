"""
Executa funções ligadas ao banco de dados via CLI.
Para fazer bootstrap do banco de dados contendo UF e cidades, execute:

    $ uv run -m simovel.cli.db bootstrap
"""

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.1'

import sys

from simovel.db.session import SessionLocal
from simovel.db.bootstrap import bootstrap_db


def bootstrap() -> None:
    with SessionLocal() as session:
        bootstrap_db(session)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso:')
        print('uv run -m simovel.cli.db bootstrap')
        sys.exit(1)

    comando = sys.argv[1]

    if comando == 'bootstrap':
        bootstrap()
    else:
        print(f'Comando desconhecido: {comando}')

