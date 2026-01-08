"""
Contém inicializações necessárias para banco de dados.
Aqui é verificado se existe ao menos uma UF no BD e suas respectivas
cidades.
"""

__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.2'

from rest_api.db import db
from rest_api.models.simulacao import EstadoModel, CidadeModel
from simovel.sims.caixa import SimuladorCaixa

def bootstrap_database():
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
            raise Exception('Não retornou id UF, nem cidades!')

        print('Inserindo cidades no banco de dados...')
        cidades: list[dict] = sim.cidades
        for cidade in cidades:
            cidade['estado_id'] = estado_id

        CidadeModel.inserir_cidades(cidades)


