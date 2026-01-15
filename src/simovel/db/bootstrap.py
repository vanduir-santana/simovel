"""
Contém inicializações necessárias para banco de dados.
Aqui é verificado se existe ao menos uma UF no BD e suas respectivas
cidades. Inicialmente será populado apenas dados da UF GO.

Será usado pela cli db. Verificar docstring de simovel.cli.db.
"""

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.5'

from sqlalchemy.orm import Session

from simovel.db.models.simulacao import EstadoModel, CidadeModel
from simovel.sims.caixa import SimuladorCaixa


CIDADES_UF = ('GO', 'MG', 'SP', 'RS', 'SC', 'ES', 'MT', 'MS', 'TO', 'PR')


def bootstrap_db(session: Session):
    # separar responsabilidades: banco será criado por outro comando
    # em produção rodar com comando alembic (estudar mais a respeito)
    # cria banco de dados
    #db.create_all()

    # popular tabela de estados se estiver vazia
    #if session.query(EstadoModel).count() == 0: # poderia tb ser dessa forma
    if EstadoModel.contar(session) == 0:
        print(
            'Não encontrou registros de estados, criando a partir do csv...'
        )
        EstadoModel.inserir_estados(session)
    else:
        print('Já existem registros de UFs em EstadoModel!')
    
    # popular cidades com dados obtidos do simulador da caixa
    # por enquanto popula apenas cidades para UFs em CIDADES_UF
    for UF in CIDADES_UF:
        if CidadeModel.contar_pof_uf(session, UF) > 0:
            print(f"Já existem cidades pra UF: {UF}.")
            continue

        print(f"Não existem cidades pra UF: {UF}, obter da Caixa...")
        estado_id: int = EstadoModel.obter_id_por_uf(session, UF)
        sim = SimuladorCaixa()
        cidades: list[dict] | None = sim.obter_cidades(UF)

        if not cidades:
            raise Exception('Não encontrou cidades no endpoint Caixa!')

        print(f'Inserindo cidades pra UF -> {UF} no banco de dados')
        for cidade in cidades:
            cidade['estado_id'] = estado_id

        CidadeModel.inserir_cidades(session, cidades)



