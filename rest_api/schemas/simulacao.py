from flask_sqlalchemy import model
from rest_api.ma import ma
from rest_api.models.simulacao import PessoaModel, EstadoModel, CidadeModel, SimulacaoModel
#from rest_api.models.integracao import Multi360Model

class CidadeSchema(ma.SQLAlchemySchema):
    class Meta:
        model = CidadeModel
        ordered = True
        load_instance = True

    id = ma.auto_field()
    cod_caixa = ma.auto_field()
    nome = ma.auto_field()        


class EstadoSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = EstadoModel
        ordered = True
        load_instance = True

    cidades = ma.Nested(CidadeSchema, many=True)


class SimulacaoSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SimulacaoModel
        load_instance = True
    
