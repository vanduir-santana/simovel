"""Engloba todo o namespace do bot Multi 360, os retornos com questões, 
menus e informações. Toda a documentação da parte de comunicação com 
Bot tá inclusa no documento PDF com o título "Documentação de Integração v.15".
"""
__author__ = 'Vanduir Santana Medeiros'
__version__ = '1.34'

from ast import Param
from datetime import date, datetime
from enum import Enum, auto
from flask import request, url_for
from flask_restx import Namespace, Resource, fields
from exc import ErroCPF, ErroCelular, ErroDataNascimento, ErroPrazo, ErroResultadoCampoNaoRetornado, ErroResultadoSimulacao, ErroTipoFinanciamento, ErroValorEntradaAbaixoPermitido, ErroValorEntradaAcimaPermitido
from exc import ErroValorFinanciamento, ErroValorMaxFinanciamento
from exc import ErroPrestacaoMax, ErroValorFinanciamentoInferior
from exc import ErroValorFinanciamentoInferior2
from exc import ErroObterOpcaoFinanciamento, ErroRendaFamiliar
from exc import ErroRendaFamiliarInsuficente, ErroValorImovel
from exc import ErroValorImovelAbaixoMin, ErroValorEntrada 
from rest_api.models.integracao import Multi360Model
from rest_api.models.simulacao import CidadeModel, EstadoModel, PessoaModel
from rest_api.models.simulacao import SimulacaoModel
from rest_api.schemas.simulacao import EstadoSchema, SimulacaoSchema
from sims.caixa import OpcaoFinanciamento, SimulacaoResultadoCaixa
from sims.caixa import SimuladorCaixa, TipoFinanciamento as TipoFinanciamentoCaixa
from sims.caixa import TipoImovel as TipoImovelCaixa
from sims.bradesco import SimulacaoResultadoBradesco, SimuladorBradesco
from sims.bradesco import TipoFinanciamento as TipoFinanciamentoBradesco
from sims.bradesco import TipoImovel as TipoImovelBradesco
from sims.itau import SimuladorItauS, SimuladorItauL, SimulacaoResultadoItau
from sims.itau import TipoImovel as TipoImovelItau
from sims.santander import SimuladorSantanderL, SimulacaoResultadoBase
from sims.base import Banco, SimuladorBase, SimuladorBaseL, SiteImobiliaria, TipoFinanciamento
from config.integracao import Multi360 as ConfMulti360
from config.geral import Bradesco, Parametros, SiteImobiliaria as ConfSiteImobliaria
from config.geral import Itau as CfgItau, Santander as CfgSantander
from config.geral import ItauTipoSimulacao
from util import Cpf, Fone, FoneFormato, Decimal2, email_aleatorio
from util import sobrenome_aleatorio


ENDPOINT_MENU_BANCO = 'api_multi360.simulador_menu_banco'
ENDPOINT_MENU_TIPO_IMOVEL = 'api_multi360.simulador_menu_tipo_imovel'
ENDPOINT_QUESTAO_CIDADE = 'api_multi360.simulador_questao_cidade'
ENDPOINT_MENU_CIDADES = 'api_multi360.simulador_menu_cidades'
ENDPOINT_MENU_POSSUI_IMOVEL_CIDADE = 'api_multi360.simulador_menu_possui_imovel_cidade'
ENDPOINT_MENU_TIPO_FINANCIAMENTO = 'api_multi360.simulador_menu_tipo_financ'
ENDPOINT_QUESTAO_VALOR_IMOVEL = 'api_multi360.simulador_questao_valor_imovel'
ENDPOINT_QUESTAO_VALOR_ENTRADA_ITAU_SANTANDER = 'api_multi360.simulador_questao_valor_entrada_itau_santander'
ENDPOINT_QUESTAO_CPF = 'api_multi360.simulador_questao_cpf'
ENDPOINT_QUESTAO_CELULAR = 'api_multi360.simulador_questao_celular'
ENDPOINT_QUESTAO_RENDA_FAMILIAR = 'api_multi360.simulador_questao_renda_familiar'
ENDPOINT_QUESTAO_DATA_NASC = 'api_multi360.simulador_questao_data_nasc'
ENDPOINT_QUESTAO_DATA_NASC_CONJUGE = 'api_multi360.simulador_questao_data_nasc_conjuge'
ENDPOINT_MENU_TRES_ANOS_FGTS = 'api_multi360.simulador_menu_tres_anos_fgts'
ENDPOINT_MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE = 'api_multi360.simulador_menu_mais_comprador'
ENDPOINT_MENU_SERVIDOR_PUBLICO = 'api_multi360.simulador_menu_servidor_publico'
ENDPOINT_MENU_OPCOES_FINANCIAMENTO = 'api_multi360.simulador_menu_opcoes_financ'
ENDPOINT_MENU_RESULTADO = 'api_multi360.simulador_menu_resultado'
ENDPOINT_MENU_ALTERAR_DADOS = 'api_multi360.simulador_menu_alterar_dados'
ENDPOINT_MENU_FINALIZAR_SIMULACAO = 'api_multi360.simulador_menu_finalizar'
ENDPOINT_QUESTAO_ALTERAR_PRAZO = 'api_multi360.simulador_questao_alterar_prazo'
ENDPOINT_QUESTAO_ALTERAR_VALOR_ENTRADA_CAIXA = 'api_multi360.simulador_questao_alterar_valor_entrada_caixa'
ENDPOINT_QUESTAO_ALTERAR_VALOR_ENTRADA_ITAU_SANTANDER = 'api_multi360.simulador_questao_alterar_valor_entrada_itau_santander'
ENDPOINT_MENU_ALTERAR_SISTEMA_AMORTIZACAO = 'api_multi360.simulador_menu_sistema_amortizacao'
ENDPOINT_QUESTAO_ALTERAR_PRESTACAO_MAX = 'api_multi360.simulador_questao_alterar_prestacao_max'
ENDPOINT_QUESTAO_ALTERAR_RENDA = 'api_multi360.simulador_questao_alterar_renda'
ENDPOINT_QUESTAO_ALTERAR_VALOR_FINANCIAMENTO_BRADESCO = 'api_multi360.simulador_questao_alterar_valor_financiamento_brad'
ENDPOINT_MENU_DICAS = 'api_multi360.simulador_menu_dicas'
ENDPOINT_MENU_DICA_ITEM = 'api_multi360.simulador_menu_dica_item'

T_EXIBIR_OBS = 'exibir_obs_resultado'

NS_NOME = 'simulador'
NS_DESCRICAO = 'Métodos para entrada de dados e simulação de crédito imobiliário'

api = Namespace(name=NS_NOME, description=NS_DESCRICAO, )
simulacao_schema = SimulacaoSchema()
#cidades_schema = CidadeSchema(many=True)
estado_schema = EstadoSchema()


class TipoResposta(Enum):
    MENU = 'MENU'
    QUESTAO = 'QUESTION'
    INFORMACAO = 'INFORMATION'
    DIRECIONAR_MENU = 'DIRECT_TO_MENU'
    CRIAR_ATENDIMENTO = 'CREATE_CUSTOMER_SERVICE'


class Entrada(Enum):
    NENHUMA = auto()
    INICIO = auto()
    CHECAR_CAMPOS = auto()
    MENU_BANCO = auto()
    MENU_TIPO_IMOVEL = auto()
    CIDADE = auto()
    MENU_CIDADES = auto()
    TIPO_FINANCIAMENTO = auto()
    MENU_POSSUI_IMOVEL_CIDADE = auto()
    VALOR_IMOVEL = auto()
    VALOR_ENTRADA_ITAU_SANTANDER = auto()           # itaú e santander
    CPF = auto()
    CELULAR = auto()
    RENDA_FAMILIAR = auto()
    DATA_NASCIMENTO = auto()
    DATA_NASCIMENTO_CONJUGE = auto()                # bradesco
    MENU_TRES_ANOS_FGTS = auto()
    MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE = auto()   # bradesco: somar renda cônjuge
    MENU_SERVIDOR_PUBLICO = auto()
    OPCAO_FINANCIAMENTO = auto()
    MENU_RESULTADO_SIMULACAO = auto()
    MENU_RESULTADO_SIMULACAO_BRADESCO = auto()
    MENU_RESULTADO_SIMULACAO_ITAU_SANTANDER = auto()
    MENU_ALTERAR_DADOS = auto()
    MENU_ALTERAR_DADOS2 = auto()
    MENU_FINALIZAR_SIMULACAO = auto()
    ALTERAR_PRAZO = auto()
    ALTERAR_VALOR_ENTRADA_CAIXA = auto()
    ALTERAR_VALOR_ENTRADA_ITAU_SANTANDER = auto()
    MENU_SISTEMA_AMORTIZACAO = auto()
    ALTERAR_PRESTACAO_MAX = auto()
    ALTERAR_RENDA_FAMILIAR = auto()
    ALTERAR_VALOR_FINANCIAMENTO_BRADESCO = auto()
    ATENDIMENTO_SIMULACAO_OK = auto()
    MENU_DICAS = auto()
    MENU_DICA_ITEM = auto()


# ordem de entradas de acordo com o banco
ENTRADA_BANCO: dict[tuple] = {
    Banco.CAIXA: (
        Entrada.MENU_BANCO,
        Entrada.MENU_TIPO_IMOVEL,
        Entrada.CIDADE,
        Entrada.MENU_CIDADES,
        Entrada.TIPO_FINANCIAMENTO,
        Entrada.MENU_POSSUI_IMOVEL_CIDADE,
        Entrada.VALOR_IMOVEL,
        Entrada.CPF,
        Entrada.CELULAR,
        Entrada.RENDA_FAMILIAR,
        Entrada.DATA_NASCIMENTO,
        Entrada.MENU_TRES_ANOS_FGTS,
        Entrada.MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE,
        Entrada.MENU_SERVIDOR_PUBLICO,
        Entrada.OPCAO_FINANCIAMENTO,
        Entrada.MENU_RESULTADO_SIMULACAO
    ),
    Banco.BRADESCO: (
        Entrada.MENU_BANCO,
        Entrada.TIPO_FINANCIAMENTO,
        Entrada.VALOR_IMOVEL,
        Entrada.CPF,
        Entrada.DATA_NASCIMENTO,
        Entrada.MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE,
        Entrada.DATA_NASCIMENTO_CONJUGE,
    ),
    Banco.ITAU: (   # selenium
        Entrada.MENU_BANCO,
        Entrada.VALOR_IMOVEL,
        Entrada.VALOR_ENTRADA_ITAU_SANTANDER,
        Entrada.CPF,
        Entrada.CELULAR,
        Entrada.DATA_NASCIMENTO,
    ),
    Banco.ITAU_L: (
        Entrada.MENU_BANCO,
        Entrada.VALOR_IMOVEL,
        Entrada.VALOR_ENTRADA_ITAU_SANTANDER,
        Entrada.DATA_NASCIMENTO,
        Entrada.CELULAR,
        Entrada.RENDA_FAMILIAR,
    ),
    Banco.SANTANDER: (
        Entrada.MENU_BANCO,
        Entrada.VALOR_IMOVEL,
        Entrada.VALOR_ENTRADA_ITAU_SANTANDER,
        Entrada.DATA_NASCIMENTO,
        Entrada.CELULAR,
        Entrada.RENDA_FAMILIAR,
    )
}


class ContactType(Enum):
    WHATSAPP = 'WHATSAPP'
    FACEBOOK = 'FACEBOOK'
    SITE = 'SITE'


wildcard_fields = fields.Wildcard(fields.String(description='Campos passados pelo Bot.'))

modelo_req_padrao = api.model(
    'req_padrao',
    {
        'clienteId': fields.Integer(),
        'id': fields.Integer(example=215123, required=True),
        'text': fields.String(description='Texto que o contato digitou', default='GO', required=True),
        'contact': fields.Nested(
            api.model(
                'contact',
                {
                    'uid': fields.Integer(example=15295, required=True),
                    'type': fields.String(default='WHATSAPP', enum=['WHATSAPP', 'FACEBOOK', 'SITE'], required=True),
                    'key': fields.String(example='5513999999999', required=True),
                    'name': fields.String(example='Robson', required=True),
                    'fields': wildcard_fields,
                }
            ), required=True),
        'data': fields.Nested(
            api.model('data', {})
        ),
    }
)


modelo_aninhado_anexos = api.model(
    'resp_anexos',
    {
        'position': fields.String(description='Posição do anexo', deafault='BEFORE', enum=['BEFORE', 'AFTER'], required=True),
        'type': fields.String(description='Tipo do anexo', default='IMAGE', enum=['IMAGE', 'DOCUMENT', 'TEXT'], required=True),
        'name': fields.String(description='Nome do anexo', required=True),
        'url': fields.String(description='Caminho onde tá o arquivo estático', required=True)
    },
    description='lista de anexos que serão enviados.'
)

modelo_aninhado_callback = api.model(
        'resp_callback',
        {
            'endpoint': fields.String(descrpition='Caminho que será solicitado', required=True),
            'data': fields.Nested(
                api.model(
                    'callback_data',
                    {}
                )
            )
        }
)

modelo_aninhado_itens = api.model(
    'resp_itens',
    {
        'number': fields.Integer(description='Número da opção', example=1, required=True),
        'text': fields.String(description='Texto que será apresentado após o número.', example='Menu 1', required=True),
        'callback': fields.Nested(modelo_aninhado_callback, description='Caminho que será solicitado quando o contato escolher essa opção.', required=True),
    }
)

modelo_resp_menu = api.model(
    'resp_menu',
    {
        'type': fields.String(default=TipoResposta.MENU.value, enum=[TipoResposta.MENU.value], required=True),
        'text': fields.String(descrption='Texto que será enviado para o contato', required=True),
        'attachments': fields.List(fields.Nested(modelo_aninhado_anexos)),
        'items': fields.List(fields.Nested(modelo_aninhado_itens), 
                description='Opções que serão listadas para o contato.', required=True)
    }
)

modelo_resp_questao = api.model(
    'resp_questao',
    {
        'type': fields.String(default=TipoResposta.QUESTAO.value, enum=[TipoResposta.QUESTAO.value], required=True),
        'text': fields.String(description='Texto que será enviado para o contato.', required=True),
        'attachments': fields.List(fields.Nested(modelo_aninhado_anexos), description='Lista de anexos que serão enviados.'),
        'callback': fields.Nested(modelo_aninhado_callback, 
                description='Caminho que será solicitado quando o usuário responder a pergunta.', required=True),

    }
)

modelo_resp_informacao = api.model(
    'resp_informacao',
    {
        'type': fields.String(default=TipoResposta.INFORMACAO.value, enum=[TipoResposta.INFORMACAO.value], required=True),
        'text': fields.String(description='Texto que será enviado para o contato.', required=True),
        'attachments': fields.List(fields.Nested(modelo_aninhado_anexos)),
    }
)

modelo_resp_direcionar_menu = api.model(
    'resp_direcionar_menu',
    {
        'type': fields.String(default=TipoResposta.DIRECIONAR_MENU.value, enum=[TipoResposta.DIRECIONAR_MENU.value], required=True),
        'menuUUID': fields.String(description='uuid do menu que será redirecionado.', required=True),
    }
)

modelo_resp_criar_atendimento = api.model(
    'resp_criar_atendimento',
    {
        'type': fields.String(default=TipoResposta.CRIAR_ATENDIMENTO.value, enum=[TipoResposta.CRIAR_ATENDIMENTO.value], required=True),
        'departmentUUID': fields.String(description='uuid do departamento.', required=True),
        'userUUID': fields.String(description='uuid do atendente.'),
    }
)


@api.route('/cpf/<cpf>')
class Pessoa(Resource):
    def get(self, cpf):
        sim_dados = PessoaModel.buscar_por_cpf(cpf)
        if sim_dados:
            return simulacao_schema.dump(sim_dados), 200
        return {'message': 'CPF não encontrado'}, 404


@api.route('/UF')
class UF(Resource):
    def get(self,):
        """Obtem todas as cidades de um determinado estado.
        """
        return estado_schema.dump(
            EstadoModel.query.filter(EstadoModel.uf == 'GO').first()
        )


# TODO: deixar apenas a rota inicio, manter por enquanto a rota uf_cidade por compatibilidade
#@api.route('/', '/uf_cidade')
@api.route('/', '/inicio')
class Inicio(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_questao, description='Pergunta ao contato e espera uma resposta.')
    @api.response(code=220, model=modelo_resp_menu, description='Envia menu de opções para o contato.')
    @api.response(code=404, description='Campo não passado no payload.')
    def post(self):
        """Endpoint chamado a partir do menu de integração do bot Multi360. Todas as informações - UF,
        cidade, data de nascimento, renda, valor imóvel são coletados a partir da integração.
        Os códigos dos responses são apenas pra fins de documentação pois o Bot aceita apenas code=200.
        Então sempre a resposta ao Bot vai ser com o código de status 200.
        """
        return TratamentoRequisicao().inicio()


@api.route('/menu/banco')
class MenuBanco(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu,
                description='Seleciona banco.')
    def post(self,):
        return TratamentoRequisicao().menu_banco()

    
@api.route('/menu/tipo_imovel')
class MenuTipoImovel(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu,
                description='Tipo Imóvel.')
    def post(self,):
        return TratamentoRequisicao().menu_tipo_imovel()


@api.route('/questao/cidade')
class QuestaoCidade(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, 
                description='Retorna menu com cidades.')
    @api.response(code=221, model=modelo_resp_questao, 
                description='Próxima entrada: tipo financiamento.')
    def post(self,):
        return TratamentoRequisicao().questao_cidade()


@api.route('/menu/cidades')
class MenuCidades(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_questao, description='Pergunta ao contato novamente qual cidade.')
    @api.response(code=220, model=modelo_resp_menu, description='Retorna menu pedindo pro contato escolher o tipo de financiamento.')
    def post(self):
        return TratamentoRequisicao().menu_cidades()


@api.route('/menu/tipo_financ')
class MenuTipoFinanc(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_questao, 
            description='Response próxima entrada: valor do imóvel')
    def post(self,):
        return TratamentoRequisicao().menu_tipo_financ()


@api.route('/menu/possui_imovel_cidade')
class MenuPossuiImovelCidade(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_questao, description='Pergunta se contato tem imóvel na cidade.')
    def post(self):
        return TratamentoRequisicao().menu_possui_imovel_cidade()


@api.route('/questao/valor_imovel')
class QuestaoValorImovel(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_questao, 
                  description='Retorna a próxima entrada: CPF')
    def post(self,):
        return TratamentoRequisicao().questao_valor_imovel()


@api.route('/questao/valor_entrada_itau_santander')
class QuestaoValorEntradaItauSantander(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Trata valor da entrada pra Itaú e Santander.')
    def post(self):
        return TratamentoRequisicao().questao_valor_entrada_itau_santander()


@api.route('/questao/cpf')
class QuestaoCpf(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_questao,
     description='Retorna a próxima entrada: celular ou renda familiar.')
    def post(self,):
        return TratamentoRequisicao().questao_cpf()


@api.route('/questao/celular')
class QuestaoCelular(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_questao,
        description='Retorna próxima entrada: renda familiar.')
    def post(self,):
        return TratamentoRequisicao().questao_celular()


@api.route('/questao/renda_familiar')
class QuestaoRendaFamiliar(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_questao,
        description='Retorna próxima entrada: data nascimento.')
    def post(self,):
        return TratamentoRequisicao().questao_renda_familiar()


@api.route('/questao/data_nasc')
class QuestaoDataNasc(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu,
        description='Retorna próxima entrada: data_nasc_conjuge ou menu possui 3 anos de FGTS.')
    def post(self,):
        return TratamentoRequisicao().questao_data_nasc()


@api.route('/questao/data_nasc_conjuge')
class QuestaoDataNascConjuge(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu,
        description='Retorna próxima entrada: menu possui 3 anos de FGTS.')
    def post(self,):
        return TratamentoRequisicao().questao_data_nasc_conjuge()


@api.route('/menu/tres_anos_fgts')
class MenuTresAnosFgts(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, 
        description='Retorna menu: mais de um comprador ou dependente.')
    def post(self):
        return TratamentoRequisicao().menu_tres_anos_fgts()


@api.route('/menu/mais_comprador')
class MenuMaisComprador(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu,
        description='Retorna próxima resposta: servidor publico.')
    def post(self):
        return TratamentoRequisicao().menu_mais_de_um_comprador_dependente()


@api.route('/menu/servidor_publico')
class MenuServidorPublico(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu,
        description='Retorna próxima resposta opções de financiamento.')
    def post(self):
        return TratamentoRequisicao().menu_servidor_publico()

@api.route('/menu/opcoes_financ')
class MenuOpcoesFinanc(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_informacao, description='Responde com o resultado da simulação')
    def post(self,):
        return TratamentoRequisicao().menu_opcoes_financ()


@api.route('/menu/resultado')
class MenuResultado(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Exibe resultado.')
    def post(self,):
        return TratamentoRequisicao().menu_resultado()

@api.route('/menu/resultado_bradesco')
class MenuResultadoBradesco(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Exibe resultado.')
    def post(self,):
        return TratamentoRequisicao().menu_resultado_bradesco()


@api.route('/menu/alterar_dados')
class MenuAlterarDados(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_questao, description='Retorna item a ser alterado.')
    def post(self,):
        return TratamentoRequisicao().menu_alterar_dados()


@api.route('/menu/finalizar')
class MenuFinalizar(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Retorna menu com opções de finalização simulação.')
    def post(self):
        return TratamentoRequisicao().menu_finalizar_simulacao()


@api.route('/questao/alterar_prazo')
class QuestaoAlterarPrazo(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Retorna simulação com prazo alterado.')
    def post(self,):
        return TratamentoRequisicao().questao_alterar_prazo()


@api.route('/questao/alterar_valor_entrada_caixa')
class QuestaoAlterarValorEntradaCaixa(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Retorna simulação com valor da entrada alterado.')
    def post(self):
        return TratamentoRequisicao().questao_alterar_valor_entrada_caixa()


@api.route('/questao/alterar_valor_entrada_itau_santander')
class QuestaoAlterarValorEntradaItauSantander(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Retorna simulação com valor da entrada alterado.')
    def post(self):
        return TratamentoRequisicao().questao_alterar_valor_entrada_itau_santander()


@api.route('/menu/sistema_amortizacao')
class MenuSistemaAmortizacao(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Retorna simulação com o sist. amortização alterado.')
    def post(self):
        return TratamentoRequisicao().menu_alterar_sistema_amortizacao()


@api.route('/questao/alterar_prestacao_max')
class QuestaoAlterarPrestacaoMax(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Retorna simulação com o valor da prestação máxima alterado')
    def post(self):
        return TratamentoRequisicao().questao_alterar_prestacao_max()


@api.route('/questao/alterar_renda')
class QuestaoAlterarRenda(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Retorna simulação com renda alterada.')
    def post(self,):
        return TratamentoRequisicao().questao_alterar_renda()


@api.route('/questao/alterar_valor_financiamento_brad')
class QuestaoAlterarValorFinanciamentoBrad(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Retornar pro menu de alteração de dados.')
    def post(self):
        return TratamentoRequisicao().questao_alterar_valor_financiamento_bradesco()


@api.route('/menu/dicas')
class MenuDicas(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Exibe dicas de simulação baseada nas configurações.')
    def post(self):
        return TratamentoRequisicao().menu_dicas()


@api.route('/menu/dica_item')
class MenuDicaItem(Resource):
    @api.expect(modelo_req_padrao, validate=False)
    @api.response(code=200, model=modelo_resp_menu, description='Exibe dica de simulação selecionada no menu dicas.')
    def post(self):
        return TratamentoRequisicao().menu_dica_item()


class Requisicao:
    '''Simplifica o tratamento das requisições'''
    class Contato:
        key: str
        type: str
        name: str

    class EntradaSequencia:
        """Organiza entradas não sequenciais e envia no campo data."""
        def __init__(self, entrada_atual=Entrada.NENHUMA, 
                           entrada_retornar=Entrada.NENHUMA) -> None:
            self.entrada_atual: Entrada = entrada_atual
            self.entrada_retornar: Entrada = entrada_retornar

        def json(self) -> dict:
            return {
                'entrada_atual': self.entrada_atual.value,
                'entrada_retornar': self.entrada_retornar.value
            }

        @classmethod
        def from_json(cls, d: dict):
            """Preenche campos a partir de dict json"""
            if not 'entrada_atual' in d:
                d['entrada_atual'] = Entrada.NENHUMA.value
            if not 'entrada_retornar' in d:
                d['entrada_retornar'] = Entrada.NENHUMA.value
            # BUG: estava alterando o valor da classe e não do objeto
            #cls.entrada_atual = Entrada(d['entrada_atual'])
            #cls.entrada_retornar = Entrada(d['entrada_retornar'])
            return cls(
                entrada_atual=Entrada(d['entrada_atual']),
                entrada_retornar=Entrada(d['entrada_retornar'])
            )

    req_json: dict
    text: str
    contact: Contato
    data: dict
    _entrada_seq: EntradaSequencia

    def __init__(self):
        self.req_json = request.get_json()
        self.text = self.req_json['text']
        contact: dict = self.req_json['contact']
        self.contact = self.Contato
        self.contact.key = contact['key']
        self.contact.type = contact['type']
        self.contact.name = contact['name']
        self.data = self.req_json['data']
        self._entrada_seq = self.EntradaSequencia()
        if not self.data: 
            self.data = {}
            self.data['entrada_seq'] = {}
        elif 'entrada_seq' in self.data:
            self._entrada_seq = self.EntradaSequencia.from_json(
                self.data['entrada_seq']
            )
        else:
            self.data['entrada_seq'] = self.EntradaSequencia().json()

    @property
    def entrada_seq(self) -> EntradaSequencia:
        return self._entrada_seq
        
    @property
    def entrada_atual(self) -> Entrada:
        return self._entrada_seq.entrada_atual
    
    @entrada_atual.setter
    def entrada_atual(self, v: Entrada):
        self.data['entrada_seq']['entrada_atual'] = v.value
        self._entrada_seq.entrada_atual = v

    @property
    def entrada_retornar(self) -> Entrada:
        return self._entrada_seq.entrada_retornar

    @entrada_retornar.setter
    def entrada_retornar(self, v: Entrada):
        self.data['entrada_seq']['entrada_retornar'] = v.value
        self._entrada_seq.entrada_retornar = v   


class TratamentoRequisicao:
    req: Requisicao
    entrada: Entrada    
    multi360_model: Multi360Model
    flag_copiar_sim: bool

    def __init__(self,):
        self.req = Requisicao()
        self.entrada = Entrada.NENHUMA
        self.flag_copiar_sim = False
        self.multi360_model = Multi360Model.buscar_por_key(
            self.req.contact.key
        )
    
    @property
    def banco(self) -> Banco:
        if not self.multi360_model:
            return None
        pessoa: PessoaModel = self.multi360_model.pessoa
        if not pessoa.simulacoes:
            return None
        simulacao: SimulacaoModel = pessoa.simulacoes[0]
        if not simulacao:
            return None

        # pro banco itaú vai depender de qual simulador tá configurado
        b: Banco = Banco(simulacao.banco)
        if b == Banco.ITAU or b == Banco.ITAU_L:
            b = Banco.ITAU if CfgItau.TIPO_SIMULACAO ==  ItauTipoSimulacao.SEL \
                else Banco.ITAU_L

        return b

    def _adicionar_pessoa(self, ) -> None:
        estado: EstadoModel
        pessoa = PessoaModel(nome=self.req.contact.name, cpf='')
        if self.req.contact.type == ContactType.WHATSAPP.value:
            # quando for contato via whatsapp o campo key é 
            # telefone (ver doc.)
            pessoa.fone = self.req.contact.key
        estado = EstadoModel.buscar_por_uf(Parametros.UF_PADRAO)
        if estado: pessoa.estado = estado
        self.multi360_model.pessoa = pessoa

    def inicio(self, permitir_copiar_sim: bool=True) -> tuple[dict, int]:
        """Primeira chamada do Bot a integração. Verifica se existe,
        key, ou seja, se já foi feita uma simulação anterior.
        """
        pessoa: PessoaModel
        if not self.multi360_model:
            # salva dados iniciais no DB
            self.multi360_model = Multi360Model(
                type=self.req.contact.type, key=self.req.contact.key
            )
            self._adicionar_pessoa()
            self.multi360_model.adicionar()

            #return self._response_proxima_entrada(Entrada.MENU_BANCO)
        else:
            # verificar o q tá salvo e pedir a partir do ponto q ainda 
            # não foi digitado
            
            # BUG: pessoa retornando None, provavelmente alterou o 
            # registro com o mesmo CPF em outra máquina ou em modo
            # anônimo. CORRIGIDO. Testar comportamento q pd gerar o bug
            if self.multi360_model.pessoa is None:
                print('-' * 30)
                print('NÃO encontrou registro na tabela pessoa ao alterar registro, adicionando...')
                self._adicionar_pessoa()
                self.multi360_model.atualizar()
            
        pessoa = self.multi360_model.pessoa
        simulacao: SimulacaoModel
        banco: Banco = self.banco
        if banco is None:
            if SimuladorBase.apenas_um_banco_habilitado() \
            and Parametros.SELECIONAR_AUTO_QUANDO_APENAS_UM_BANCO_HABILITADO:
                banco = SimuladorBase.obter_primeiro_banco_habilitado()
                return self._salvar_banco(banco)
            else:
                return self._response_proxima_entrada(Entrada.MENU_BANCO)
        
        simulacoes = pessoa.simulacoes
        simulacao = simulacoes[0]
        if banco == Banco.CAIXA:
            # por enquanto tipo_imovel só pra Caixa
            if simulacao.tipo_imovel is None:
                return self._response_proxima_entrada(Entrada.MENU_TIPO_IMOVEL)
            if pessoa.cidade is None:
                return self._response_proxima_entrada(Entrada.CIDADE)
        
        if (banco == Banco.CAIXA and simulacao.tipo_financiamento is None) \
            or (banco == Banco.BRADESCO 
                and simulacao.tipo_financiamento_bradesco is None):
            return self._response_proxima_entrada(
                Entrada.TIPO_FINANCIAMENTO
            )
        
        if banco == Banco.CAIXA:
            if pessoa.possui_imovel_cidade is None:
                return self._response_proxima_entrada(
                    Entrada.MENU_POSSUI_IMOVEL_CIDADE
                )
        
        if simulacao.valor_imovel is None:
            return self._response_proxima_entrada(Entrada.VALOR_IMOVEL)

        if banco == Banco.ITAU or banco == Banco.ITAU_L or banco == Banco.SANTANDER:
            if simulacao.valor_entrada is None:
                return self._response_proxima_entrada(
                    Entrada.VALOR_ENTRADA_ITAU_SANTANDER
                )

        if banco == Banco.CAIXA or banco == Banco.BRADESCO \
        or banco == Banco.ITAU:
            if not pessoa.cpf:
                return self._response_proxima_entrada(Entrada.CPF)
        
        if self.multi360_model.type != ContactType.WHATSAPP.value and \
            not pessoa.fone:
            return self._response_proxima_entrada(Entrada.CELULAR)

        # somente bradesco não precisa definir renda pois é a partir
        # do valor financiamento
        if banco != Banco.BRADESCO and banco != Banco.ITAU \
        and simulacao.renda_bruta is None:
            return self._response_proxima_entrada(Entrada.RENDA_FAMILIAR)

        if pessoa.data_nasc is None:
            return self._response_proxima_entrada(Entrada.DATA_NASCIMENTO)

        if banco == Banco.BRADESCO:
            if pessoa.mais_de_um_comprador_dependente is None:
                return self._response_proxima_entrada(
                    Entrada.MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE
                )
            if pessoa.mais_de_um_comprador_dependente \
                and pessoa.data_nasc_conjuge is None:
                return self._response_proxima_entrada(
                    Entrada.DATA_NASCIMENTO_CONJUGE
                )

        if banco == Banco.CAIXA:
            if pessoa.tres_anos_fgts is None:
                return self._response_proxima_entrada(
                    Entrada.MENU_TRES_ANOS_FGTS
                )
            
            if pessoa.mais_de_um_comprador_dependente is None:
                return self._response_proxima_entrada(
                    Entrada.MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE
                )
            
            if pessoa.servidor_publico is None:
                return self._response_proxima_entrada(
                    Entrada.MENU_SERVIDOR_PUBLICO
                )
            
            if not simulacao.opcao_financiamento:
                # exibir opções de financiamento e salvar opção no DB
                return self._response_proxima_entrada(
                    entrada=Entrada.OPCAO_FINANCIAMENTO,
                )

        # Quando for nova simulação e não tiver concluído, o
        # campo data de simulação fica nulo. Só é preenchido
        # quando o contato finalizar simulação
        if simulacao.data and permitir_copiar_sim:
            self._copiar_ultima_simulacao(simulacao_atual=simulacao)
        else:
            pass
        
        return self._response_proxima_entrada(
            Entrada.MENU_ALTERAR_DADOS
        )

    def menu_banco(self) -> tuple[dict, int]:
        banco: Banco = Banco(self.req.data['valor'])
        return self._salvar_banco(banco)

    def _salvar_banco(self, banco: Banco=None) -> tuple[dict, int]:
        """Salva o banco (CEF, Bradesco, Itaú, Santander) no banco de dados.
        Método usado pra salvar a partir do menu banco e também através do
        método inicio quando estiver habilitado apenas um banco.

        Args:
            banco (Banco, optional): banco a ser salvo. Defaults to None.

        Returns:
            tuple[dict, int]: retorno no padrão flask.
        """
        self.entrada = Entrada.MENU_BANCO

        if banco is None:
            banco = SimuladorBase.obter_primeiro_banco_habilitado()

        if banco == Banco.ITAU \
        and CfgItau.TIPO_SIMULACAO == ItauTipoSimulacao.LOF:
            # verifica se vai simular pelo Selenium ou L
            banco = Banco.ITAU_L

        # salva banco no DB
        # verifica se tá no modo de alteração
        simulacoes = self.multi360_model.pessoa.simulacoes
        if not simulacoes or (simulacoes and simulacoes[0].data):
            self.multi360_model.pessoa.simulacoes.append(
                SimulacaoModel.a_partir_de_banco(banco.value)
            )
        else:
            simulacao: SimulacaoModel = simulacoes[0]
            simulacao.banco = banco.value

        self.multi360_model.atualizar()
        # volta ao início pra ver campos q estão faltando
        return self._checar_campos()

    def menu_tipo_imovel(self) -> tuple[dict, int]:
        # por enquanto implementado só pra Caixa
        self.entrada = Entrada.MENU_TIPO_IMOVEL
        tipo_imovel = TipoImovelCaixa(self.req.data['valor'])

        simulacoes = self.multi360_model.pessoa.simulacoes
        simulacao: SimulacaoModel = simulacoes[0]
        # salvar DB
        simulacao.tipo_imovel = tipo_imovel.value
        simulacao.atualizar()
        # verifica se o tipo de financiamento é compatível com o tipo imóvel
        if simulacao.tipo_financiamento is not None:
            sim = SimuladorCaixa()
            sim.tipo_imovel = tipo_imovel
            try:
                sim.tipo_financiamento = TipoFinanciamentoCaixa(
                    simulacao.tipo_financiamento
                )
            except ErroTipoFinanciamento:
                return self._response_proxima_entrada(Entrada.TIPO_FINANCIAMENTO)

        return self._response_proxima_entrada()

    def _checar_campos(self) -> tuple[dict, int]:
        self.entrada = Entrada.CHECAR_CAMPOS

        # volta ao início pra ver campos q estão faltando
        # fica voltando ao self.inicio até chegar menu_alterar_dados
        # q redefini entrada_retornar em _response_proxima_entrada
        print('self._checar_campos()')
        return self._response_proxima_entrada(
            entrada=Entrada.INICIO,
            entrada_retornar=Entrada.CHECAR_CAMPOS
        )
    
    def questao_cidade(self) -> tuple[dict, int]:
        self.entrada = Entrada.CIDADE

        cidade: str = self.req.text
        uf: str = Parametros.UF_PADRAO

        if not cidade or len(cidade) < 3:
            return self._response_proxima_entrada(
                Entrada.CIDADE,
                ConfMulti360.Questao.CIDADE_INVALIDA
            )

        sim = SimuladorCaixa()
        cidades = EstadoModel.obter_cidades(uf=uf, lista_dicts=False)
        cidades_filtro: list[dict] = sim.procurar2(
            q=cidade,
            l=cidades,
            key=2,
            max_res=ConfMulti360.MAX_RES_MENU_CIDADES
        )

        if not cidades_filtro:
            return self._response_proxima_entrada(
                Entrada.CIDADE,
                ConfMulti360.Questao.CIDADE_PESQUISA_VAZIA.format(cidade)
            )

        # se tiver retornado somente uma cidade então salvar cidade 
        # no db
        if len(cidades_filtro) == 1 and cidades_filtro[0]['rank'] == 1.0:
            id: int = cidades_filtro[0]['id']
            cidade: CidadeModel = CidadeModel.buscar_por_id(id)
            pessoa: PessoaModel = self.multi360_model.pessoa
            pessoa.cidade = cidade
            pessoa.atualizar()
            
            # TODO: detectar modo nova simulação (alteração) e não 
            # pular pois está indo pra tipo financ. deve voltar 
            # pro menu de alteração de dados
            # Retornar próxima coleta de info: tipo financ.
            return self._response_proxima_entrada(
                self._pular_entrada(Entrada.MENU_CIDADES)
            )

        # Adicionar opção pra pesquisar novamente a cidade caso não 
        # esteja no menu
        cidades_filtro.append({
            'id': ConfMulti360.Menu.ID_BUSCAR_NOVAMENTE,
            'nome': ConfMulti360.Menu.CIDADE_ITEM_BUSCAR_NOVAMENTE
        })

        return self._response_proxima_entrada(
            Entrada.MENU_CIDADES,
            opcoes_menu=cidades_filtro
        )

    def menu_cidades(self) -> tuple[dict, int]:
        self.entrada = Entrada.MENU_CIDADES

        # contato selecionou pesquisar novamente?
        cidade_id: int = self.req.data['id']
        if cidade_id == ConfMulti360.Menu.ID_BUSCAR_NOVAMENTE:
            return self._response_proxima_entrada(
                Entrada.CIDADE,
                ConfMulti360.Questao.CIDADE2
            )
        
        # selecionou uma cidade: salvar no DB
        print(f'CIDADE SELECIONADA: {self.req.data["nome"]}')
        self.multi360_model.pessoa.cidade = CidadeModel.buscar_por_id(cidade_id)
        self.multi360_model.pessoa.atualizar()

        # retorna próxima coleta de info: possui imovel cidade.
        return self._response_proxima_entrada()
    
    def menu_tipo_financ(self) -> tuple[dict, int]:
        self.entrada = Entrada.TIPO_FINANCIAMENTO
        tipo_financ: int = self.req.data['valor']
        
        # salva tipo financiamento no DB
        simulacoes = self.multi360_model.pessoa.simulacoes
        simulacao: SimulacaoModel = simulacoes[0]
        banco: Banco = self.banco
        if banco != Banco.BRADESCO:
            simulacao.tipo_financiamento = tipo_financ
        else:
            simulacao.tipo_financiamento_bradesco = tipo_financ
        
        self.multi360_model.atualizar()
        # retorna próxima coleta de info: valor imóvel
        return self._response_proxima_entrada()

    def menu_possui_imovel_cidade(self) -> tuple[dict, int]:
        self.entrada = Entrada.MENU_POSSUI_IMOVEL_CIDADE

        possui_imovel_cidade: str = self.req.data['valor']
        # salvar possui_imovel_cidade no db
        self.multi360_model.pessoa.possui_imovel_cidade = possui_imovel_cidade
        self.multi360_model.pessoa.atualizar()
        # retorna próxima coleta de info: tipo_financ
        # ou dependente
        return self._response_proxima_entrada()

    def questao_valor_imovel(self) -> tuple[dict, int]:
        self.entrada = Entrada.VALOR_IMOVEL

        valor_imovel: str = self.req.text
        sim = SimuladorBase(self.banco)
        try:
            sim.valor_imovel = valor_imovel
        except (ErroValorImovel, ErroValorImovelAbaixoMin) as erro:
            msg = f'{erro} Favor digitar valor do imóvel novamente.'
            return self._response_proxima_entrada(
                Entrada.VALOR_IMOVEL,
                msg
            )
        
        # salvar valor imóvel no DB
        simulacoes = self.multi360_model.pessoa.simulacoes
        simulacao: SimulacaoModel = simulacoes[0]
        simulacao.valor_imovel = sim._valor_imovel
        simulacao.atualizar()

        # retorna próxima coleta de info: cpf
        return self._response_proxima_entrada()

    def questao_valor_entrada_itau_santander(self, alterar: bool=False) -> tuple[dict, int]:
        # itaú e santander
        self.entrada = Entrada.VALOR_ENTRADA_ITAU_SANTANDER \
            if not alterar else Entrada.ALTERAR_VALOR_ENTRADA_ITAU_SANTANDER

        valor_entrada: str = self.req.text
        pessoa: PessoaModel = self.multi360_model.pessoa
        simulacao: SimulacaoModel = pessoa.simulacoes[0]
        sim: SimuladorBaseL = SimuladorBaseL.a_partir_de_obj_limpo()
        sim.banco = self.banco
        sim.valor_imovel = simulacao.valor_imovel
        sim.checar_limite_valor_entrada = True

        try:
            sim.valor_entrada = valor_entrada
        except (
            ErroValorEntrada, ErroValorEntradaAcimaPermitido,
            ErroValorEntradaAbaixoPermitido
        ) as erro:
            msg: str = f'{erro} Favor digitar *Valor da Entrada* novamente:'
            return self._response_proxima_entrada(
                entrada=self.entrada,
                texto=msg
            )
        if not 'opcoes_financ' in self.req.data:
            self.req.data['opcoes_financ'] = {}
        self.req.data['opcoes_financ']['valor_entrada'] = sim.valor_entrada

        simulacao.valor_entrada = sim._valor_entrada
        simulacao.atualizar()
        
        #if not alterar or self.banco == Banco.ITAU_L:
        if not alterar:
            return self._response_proxima_entrada()
        else:
            return self.menu_resultado_itau_santander()
    
    def questao_cpf(self) -> tuple[dict, int]:
        self.entrada = Entrada.CPF

        cpf: str = self.req.text
        key: str = self.req.contact.key
        multi360_model: Multi360Model = Multi360Model.buscar_por_key(key)

        sim = SimuladorBase(self.banco)
        try:
            sim.cpf = cpf
        except ErroCPF as erro:
            return self._response_proxima_entrada(
                Entrada.CPF,
                ConfMulti360.Questao.CPF_INVALIDO
            )
        
        # salvar no DB
        # Testar no bot site digitando um campo cpf q já existe
        # numa janela anônima
        pessoa_model: PessoaModel = PessoaModel.buscar_por_cpf(
            str(sim._cpf)
        )
        if pessoa_model:
            multi360_model.pessoa = pessoa_model
            multi360_model.atualizar()
        else:
            multi360_model.pessoa.cpf = str(sim._cpf)
            multi360_model.pessoa.atualizar()

        # retorna próxima coleta de info: celular ou renda familiar 
        # bruta, depende de req.contact.type
        return self._response_proxima_entrada()

    def questao_celular(self) -> tuple[dict, int]:
        self.entrada = Entrada.CELULAR

        sfone: str = self.req.text
        fone: Fone
        
        try:
            fone = Fone(
                valor=sfone, formato=FoneFormato.DDI_DDD_PREF_SUF_SEM_FMT
            )
            #fone = Fone.de_fmt_somente_numeros(valor=sfone)
        except ValueError as erro:
            return self._response_proxima_entrada(
                Entrada.CELULAR,
                f'{str(erro)} {ConfMulti360.Questao.CELULAR_INVALIDO}'
            )
        
        # salva no DB
        fone_fmt: str = fone.formatar(retirar_mais_ddi=True,
                                      retirar_zero_esq=True)
        self.multi360_model.pessoa.fone = fone_fmt
        self.multi360_model.pessoa.atualizar()

        # retorna próxima coleta de info: renda familiar bruta
        return self._response_proxima_entrada()

    def questao_renda_familiar(self, responder: bool=True) -> tuple[dict, int]:
        self.entrada = Entrada.RENDA_FAMILIAR

        renda_familiar: str = self.req.text
        sim = SimuladorBase()        
        try:
            sim.renda_familiar = renda_familiar
        except ErroRendaFamiliar as erro:
            msg = f'{erro} Favor entrar com a renda famliar novamente.'
            return self._response_proxima_entrada(Entrada.RENDA_FAMILIAR, msg)
        
        # salvar renda familiar no DB
        simulacao: SimulacaoModel = self.multi360_model.pessoa.simulacoes[0]
        simulacao.renda_bruta = sim._renda_familiar
        simulacao.atualizar()

        # Caixa: retorna próxima coleta de info: dt. nasc.
        # Itaú ou Santander: resultado da simulação
        if (self.banco == Banco.ITAU_L or self.banco == Banco.SANTANDER) \
        and self.req.entrada_retornar != Entrada.CHECAR_CAMPOS:
            return self.menu_resultado_itau_santander()
        elif responder:
            return self._response_proxima_entrada()

    def questao_data_nasc(self) -> tuple[dict, int]:
        self.entrada = Entrada.DATA_NASCIMENTO

        data_nascimento: str = self.req.text
        sim = SimuladorBase(self.banco)
        try:
            sim.data_nascimento = data_nascimento
        except ErroDataNascimento as erro:
            msg = f'{erro} Favor digitar novamente a data de nascimento.'
            return self._response_proxima_entrada(
                Entrada.DATA_NASCIMENTO,
                msg
            )

        # salvar data nascimento no DB
        self.multi360_model.pessoa.data_nasc = sim._data_nascimento
        self.multi360_model.pessoa.atualizar()

        # retorna próxima coleta de info: menu "3 anos fgts"
        return self._response_proxima_entrada()
    
    def questao_data_nasc_conjuge(self) -> tuple[dict, int]:
        self.entrada = Entrada.DATA_NASCIMENTO_CONJUGE

        data_nascimento_conjuge: str = self.req.text
        sim = SimuladorBase(self.banco)
        # validação data nascimento cônjuge antes de salvar no DB
        try:
            sim.data_nascimento = data_nascimento_conjuge
        except ErroDataNascimento as erro:
            msg = f'{erro} Favor digitar novamente a data de nascimento do cônjuge.'
            return self._response_proxima_entrada(
                Entrada.DATA_NASCIMENTO_CONJUGE,
                msg
            )

        # salvar data nascimento no DB
        self.multi360_model.pessoa.data_nasc_conjuge = sim._data_nascimento
        self.multi360_model.pessoa.atualizar()

        # retorna próxima coleta de info: menu resultado da simulação"
        #return self._response_proxima_entrada()
        return self.menu_resultado_bradesco()
        
    def menu_tres_anos_fgts(self) -> tuple[dict, int]:
        self.entrada = Entrada.MENU_TRES_ANOS_FGTS
        
        tres_anos_fgts = self.req.data['valor']
        # salvar possui 3 anos fgts no db
        self.multi360_model.pessoa.tres_anos_fgts = tres_anos_fgts
        self.multi360_model.pessoa.atualizar()
        # retorna próxima coleta de info: menu mais de um comprador 
        # ou dependente
        return self._response_proxima_entrada()

    def menu_mais_de_um_comprador_dependente(self) -> tuple[dict, int]:
        # usado apenas para banco caixa e bradesco
        self.entrada = Entrada.MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE

        mais_de_um_comprador_dependente = self.req.data['valor']
        # salvar DB
        self.multi360_model.pessoa.mais_de_um_comprador_dependente = \
            mais_de_um_comprador_dependente
        self.multi360_model.pessoa.atualizar()
        
        if self.banco == Banco.CAIXA or (self.banco == Banco.BRADESCO
        and mais_de_um_comprador_dependente):
            return self._response_proxima_entrada()
        else:
            return self.menu_resultado_bradesco()

    def menu_resultado_bradesco(self, alterar: bool=False
                                            ) -> tuple[dict, int]:
        """Exibe resultado da simulação do banco Bradesco.

        Returns:
            tuple[dict, int]: retorno JSON Flask no formato requerido
                pelo chatbot.
        """
        self.entrada = Entrada.MENU_RESULTADO_SIMULACAO

        # obtem dados do DB
        simulacao: SimulacaoModel = self.multi360_model.pessoa.simulacoes[0]
        pessoa: PessoaModel = self.multi360_model.pessoa

        tipo_financiamento_brad = TipoFinanciamentoBradesco(simulacao.tipo_financiamento_bradesco)
        valor_imovel = simulacao.valor_imovel
        somar_renda_conjuge = bool(pessoa.mais_de_um_comprador_dependente)
        data_nasc = pessoa.data_nasc
        data_nasc_conjuge = None if not somar_renda_conjuge \
             else pessoa.data_nasc_conjuge
        prazo: int
        valor_financiamento: str
        if not alterar:
            prazo = 0
            valor_financiamento = ''
        else:
            prazo = self.req.data['opcoes_financ']['prazo']
            valor_financiamento = self.req.data['opcoes_financ']['valor_financiamento']
        cpf = pessoa.cpf

        sim_brad: SimuladorBradesco = SimuladorBradesco.a_partir_valor_financiamento(
            tipo_imovel=TipoImovelBradesco.RESIDENCIAL_POUPANCA,
            situacao_imovel=tipo_financiamento_brad,
            valor_imovel=valor_imovel,
            somar_renda_conjuge=somar_renda_conjuge,
            data_nascimento=data_nasc,
            data_nascimento_conjuge=data_nasc_conjuge,
            valor_financiamento=valor_financiamento,
            prazo=prazo,
            cpf=cpf
        )
        try:
            sim_brad_res: SimulacaoResultadoBradesco = sim_brad.simular()
        except ErroResultadoCampoNaoRetornado:
            raise
        txt_res: str = str(sim_brad_res)

        self.req.data['opcoes_financ'] = {
            'valor_financiamento': sim_brad.valor_financiamento,
            'valor_max_financiamento': sim_brad._valor_max_financiamento.formatar_moeda(),
            'prazo': sim_brad.prazo,
            'prazo_max': sim_brad.prazo_max
        }

        return self._response_proxima_entrada(
            Entrada.MENU_RESULTADO_SIMULACAO,
            txt_res
        )

    def menu_resultado_itau_santander(self, alterar: bool=False) -> tuple[dict, int]:
        """Exibe resultado da simulação pro banco Itaú ou Santander
        baseado na api L.

        Returns:
            tuple[dict, int]: retorno JSON Flask no formato requerido
                pelo chatbot. 
        """
        self.entrada = Entrada.MENU_RESULTADO_SIMULACAO_ITAU_SANTANDER

        # obtem dados do DB
        simulacao: SimulacaoModel = self.multi360_model.pessoa.simulacoes[0]
        pessoa: PessoaModel = self.multi360_model.pessoa
        
        nome: str = sobrenome_aleatorio(pessoa.nome)
        email: str = email_aleatorio()
        valor_imovel = simulacao.valor_imovel
        valor_entrada = simulacao.valor_entrada
        data_nasc = pessoa.data_nasc
        prazo: int
        renda = simulacao.renda_bruta

        if not alterar:
            prazo = CfgItau.PRAZO_MAX \
                if self.banco == Banco.ITAU or self.banco == Banco.ITAU_L \
                else CfgSantander.PRAXO_MAX
        else:
            prazo = self.req.data['opcoes_financ']['prazo']

        sim: SimuladorBaseL
        sim_res = SimulacaoResultadoBase
        if self.banco == Banco.ITAU:
            cpf: str = pessoa.cpf
            celular: str = pessoa.fone
            tipo_imovel: TipoImovelItau = TipoImovelItau.RESIDENCIAL
            sim = SimuladorItauS.a_partir_de_dados_financiamento(
                cpf, nome, email, celular, tipo_imovel, valor_imovel, 
                valor_entrada, data_nasc, prazo
            )
            sim_res = sim.simular()
        elif self.banco == Banco.ITAU_L:
            sim = SimuladorItauL(
                nome, email, valor_imovel, valor_entrada, 
                data_nasc, prazo, renda
            )
            sim_res = sim.simular()
        elif self.banco == Banco.SANTANDER:
            sim = SimuladorSantanderL(
                nome, email, valor_imovel, valor_entrada,
                data_nasc, prazo, renda
            )
            sim_res = sim.simular()
        txt_res: str = str(sim_res)

        self.req.data['opcoes_financ'] = {
            'entrada': sim.valor_entrada,
            'prazo': sim.prazo,
            'prazo_max': sim.prazo_max
        }

        return self._response_proxima_entrada(
            Entrada.MENU_RESULTADO_SIMULACAO,
            txt_res
        )

    def menu_servidor_publico(self) -> tuple[dict, int]:
        self.entrada = Entrada.MENU_SERVIDOR_PUBLICO

        servidor_publico: str = self.req.data['valor']
        # salvar no db
        self.multi360_model.pessoa.servidor_publico = servidor_publico
        self.multi360_model.pessoa.atualizar()
        # retorna próxima coleta de info: menu opções de financ.
        return self._response_proxima_entrada()

    # apenas pra caixa
    def menu_opcoes_financ(self, alterar_opcoes_financ: bool = False
                                                ) -> tuple[dict, int]:
        return self.menu_resultado_caixa(alterar_opcoes_financ)

    def menu_resultado_caixa(self, alterar_opcoes_financ: bool = False
                                                ) -> tuple[dict, int]:
        """Recebe opção de financiamento selecionada e exibe resultado
        da simulação do banco Caixa.

        Args:
            alterar_opcoes_financ (bool, optional): é alteração de opção
            de financiamento. Defaults to False.

        Returns:
            tuple[dict, int]: retorno Flask nos padrões do chatbot.
        """
        nome: str
        opcao_financ: OpcaoFinanciamento
        versao: str
        if not alterar_opcoes_financ:
            # pega do data do item do menu
            nome = self.req.data['nome']
            opcao_financ = OpcaoFinanciamento(self.req.data['valor'])
            versao = self.req.data['versao']
        else:
            # pega do data passado entre as requisições
            nome = self.req.data['opcoes_financ']['descricao']
            opcao_financ = OpcaoFinanciamento(
                self.req.data['opcoes_financ']['opcao_financ']
            )
            versao = self.req.data['opcoes_financ']['versao']

        sim = SimuladorCaixa()
        try:
            opcao_financ.versao = versao
            opcao_financ.descricao = nome
            sim.opcao_financiamento = opcao_financ
        except Exception as erro:
            # TODO: capturar erro e salvar no log 
            # TODO: enviar notificação desenvolvedor
            print('#' * 100)
            print(f'Erro ao setar opção de financianciamento: {erro=}')
            print('#' * 100)
            return _response_tipo_informacao(
                txt=ConfMulti360.Menu.OPCOES_FINANCIAMENTO_ERRO2
            )

        # obtem dados do DB pra passar pro simulador
        simulacao: SimulacaoModel = self.multi360_model.pessoa.simulacoes[0]
        cod_caixa: int = self.multi360_model.pessoa.cidade.cod_caixa
        nome: str = self.multi360_model.pessoa.cidade.nome
        nome_sem_aspa: str = self.multi360_model.pessoa.cidade.nome_sem_aspa

        sim.adicionar_cidade(cod_caixa, nome, nome_sem_aspa)
        sim.cidade_indice = 0

        sim.tipo_imovel = TipoImovelCaixa(simulacao.tipo_imovel)
        sim.tipo_financiamento = TipoFinanciamentoCaixa(simulacao.tipo_financiamento)
        sim.valor_imovel = simulacao.valor_imovel
        sim.cpf = self.multi360_model.pessoa.cpf
        sim.celular = self.multi360_model.pessoa.fone
        sim.renda_familiar = simulacao.renda_bruta
        sim.data_nascimento = self.multi360_model.pessoa.data_nasc
        sim.tres_anos_fgts = self.multi360_model.pessoa.tres_anos_fgts
        sim.mais_de_um_comprador_dependente = \
            self.multi360_model.pessoa.mais_de_um_comprador_dependente
        if alterar_opcoes_financ:
            sim.prazo = self.req.data['opcoes_financ']['prazo']
            sim.valor_entrada = self.req.data['opcoes_financ']['valor_entrada']
            sim.cod_sistema_amortizacao = \
                self.req.data['opcoes_financ']['cod_sistema_amortizacao']
            sim.prestacao_max = self.req.data['opcoes_financ']['prestacao_max']

        sim_resultado: SimulacaoResultadoCaixa
        try:
            sim_resultado: SimulacaoResultadoCaixa = sim.simular()
            if sim_resultado.msg_erro:
                # TODO: registrar erro no log
                # TODO: emitir alerta pra desenvolvedor com detalhes do erro
                print('#' * 100)
                print(f'Erro ao simular: {sim_resultado.msg_erro}')
                print('#' * 100)
                return _response_tipo_informacao(
                    ConfMulti360.Informacao.SIMULACAO_ERRO
                )
        except ErroRendaFamiliarInsuficente as erro:
            if (self.req.entrada_atual == Entrada.RENDA_FAMILIAR 
             or self.req.entrada_atual == Entrada.ALTERAR_RENDA_FAMILIAR
             or self.req.entrada_atual == Entrada.OPCAO_FINANCIAMENTO):
                msg = ConfMulti360.Questao.RENDA_FAMILIAR_INSUFICIENTE.format(
                    sim._renda_familiar.formatar_moeda()
                )
                return self._response_proxima_entrada(   
                    Entrada.RENDA_FAMILIAR,
                    msg,
                    entrada_retornar=Entrada.OPCAO_FINANCIAMENTO
                )
            elif self.req.entrada_atual == Entrada.ALTERAR_PRESTACAO_MAX:
                return self._response_proxima_entrada(
                    Entrada.ALTERAR_PRESTACAO_MAX,
                    ConfMulti360.Questao.ALTERAR_PRESTACAO_MAX_ABAIXO
                )
            elif self.req.entrada_atual == Entrada.ALTERAR_PRAZO:
                prazo: str = self.req.data['opcoes_financ']['prazo']
                prazo_max: str = self.req.data['opcoes_financ']['prazo_max']
                msg: str = ConfMulti360.Questao.ALTERAR_PRAZO_BAIXO.format(
                    prazo, prazo_max
                )
                return self._response_proxima_entrada(
                    Entrada.ALTERAR_PRAZO,
                    msg
                )
            else:
                msg: str = f'{erro} Tente alterar as informações.'
                return self._response_proxima_entrada(
                    Entrada.MENU_ALTERAR_DADOS,
                    msg,
                )
        except ErroValorFinanciamentoInferior as erro:
            msg: str = f'{erro} Favor digitar o *valor da entrada* novamente:'
            return self._response_proxima_entrada(
                Entrada.ALTERAR_VALOR_ENTRADA_CAIXA,
                texto=msg
            )
        except ErroValorFinanciamentoInferior2 as erro:
            if self.req.entrada_atual == Entrada.ALTERAR_PRAZO:
                return self._response_proxima_entrada(
                    Entrada.ALTERAR_PRAZO,
                    'Prazo abaixo do mínimo, digitar *prazo* novamente'
                )
            else:
                raise
        except Exception as erro:
            # TODO: registrar erro no log
            # TODO: emitir alerta pra desenvolvedor
            print('#' * 100)
            print(f'Erro ao simular: {erro}')
            print('#' * 100)
            return _response_tipo_informacao(txt=str(erro))

        # salvar opção financ. no DB
        simulacao.data = datetime.now()
        simulacao.opcao_financiamento = str(opcao_financ.value)
        simulacao.atualizar()

        # exibir resultado da simulação ao usuário
        TAM_TRACEJADO = Parametros.TAM_TRACEJADO
        txt: str = str(sim_resultado)
        if self._exibir_obs_resultado_simulacao:
            txt += (
                f'{"-" * TAM_TRACEJADO}\n'
                f'{ConfMulti360.Menu.RESULTADO_OBS}'
            )

        # TODO: implementar anexo PDF com o resultado da simulação
        # TODO: link para o site da imobiliária com um filtro
        #       pegando todos os imóveis num intervalo de valor 
        #       aproximado pretendido pelo contato.

        # passar um dicionário no response no campo data pro menu de
        # resultado pra que seja possível fazer a mudança de prazo ou
        # de renda familiar
        self.req.data['opcoes_financ'] = {
            'opcao_financ': opcao_financ.value,
            'descricao': opcao_financ.descricao,
            'versao': opcao_financ.versao,
            'prazo': sim_resultado.prazo,
            'prazo_max': sim_resultado.prazo_max,
            'valor_entrada': sim_resultado.valor_entrada,
            'cod_sistema_amortizacao': sim.cod_sistema_amortizacao,
            'cods_sistema_amortizacao': sim_resultado.cods_sistema_amortizacao,
            'sistema_amortizacao_chave_sel': sim_resultado.sistema_amortizacao_chave_sel,
            'prestacao_max': sim_resultado.prestacao_max,
            'renda_familiar': sim.renda_familiar,
        }
        self._exibir_obs_resultado_simulacao = False
        
        return self._response_proxima_entrada(
            Entrada.MENU_RESULTADO_SIMULACAO,
            txt
        )
    
    def menu_resultado(self) -> tuple[dict, int]:
        self.entrada = Entrada.MENU_RESULTADO_SIMULACAO

        entrada: Entrada = Entrada(self.req.data['valor'])

        texto2: str = ''
        match entrada:
            case Entrada.ALTERAR_PRAZO:
                texto2 = self.req.data['opcoes_financ']['prazo_max']
            case Entrada.ALTERAR_VALOR_ENTRADA_CAIXA:
                sim = SimuladorCaixa()
                sim.valor_entrada = self.req.data['opcoes_financ'] \
                                                 ['valor_entrada']
                texto2 = sim._valor_entrada.formatar_moeda()
            case Entrada.ALTERAR_RENDA_FAMILIAR:
                sim = SimuladorCaixa()
                sim.renda_familiar = self.req.data['opcoes_financ'] \
                                                  ['renda_familiar']
                texto2 = sim._renda_familiar.formatar_moeda()
            case Entrada.MENU_SISTEMA_AMORTIZACAO:
                texto2 = self.req.data['opcoes_financ'] \
                                      ['sistema_amortizacao_chave_sel']
            case Entrada.ALTERAR_PRESTACAO_MAX:
                texto2 = self.req.data['opcoes_financ']['prestacao_max']
            case Entrada.ALTERAR_VALOR_FINANCIAMENTO_BRADESCO:
                texto2 = self.req.data['opcoes_financ']['valor_max_financiamento']
            # case Entrada.VALOR_ENTRADA:     # Itaú e Santander
            #     return self.questao_valor_entrada()

        return self._response_proxima_entrada(
            entrada=entrada,
            texto2=texto2
        )

    def menu_alterar_dados(self) -> tuple[dict, int]:
        """Usuário já fez pelo menos uma simulação anteriormente  e re-
        tornou,  quando  ele  retorna  oferece  as  opções pra  que ele
        altere alguma informação e efetue a simulação outra vez.

        Returns:
            tuple[dict, int]: json com a resposta contendo  o menu  com
                os dados do contato. 
        """
        self.entrada = Entrada.MENU_ALTERAR_DADOS

        entrada: Entrada = Entrada(self.req.data['valor'])
        if entrada == Entrada.MENU_RESULTADO_SIMULACAO_BRADESCO:
            return self.menu_resultado_bradesco()
        elif entrada == entrada.MENU_RESULTADO_SIMULACAO_ITAU_SANTANDER:
            return self.menu_resultado_itau_santander()
        else:
            return self._response_proxima_entrada(
                entrada=entrada,
                entrada_retornar=Entrada.MENU_ALTERAR_DADOS
            )

    def menu_finalizar_simulacao(self):
        self.entrada = Entrada.MENU_FINALIZAR_SIMULACAO

        entrada: Entrada = Entrada(self.req.data['valor'])
        if entrada != Entrada.MENU_RESULTADO_SIMULACAO:
            return self._response_proxima_entrada(entrada=entrada)
        else:
            return self.menu_resultado_caixa(alterar_opcoes_financ=True)
    
    def questao_alterar_prazo(self) -> tuple[dict, int]:
        self.entrada = Entrada.ALTERAR_PRAZO

        prazo: str = self.req.text
        prazo_max: str = self.req.data['opcoes_financ']['prazo_max']
        
        sim = SimuladorBase(banco=self.banco)
        try:
            sim.prazo_max = prazo_max
            sim.prazo = prazo
        except ErroPrazo as erro:
            texto: str = f'{erro} Favor digitar o *prazo novamente:*'
            return self._response_proxima_entrada(Entrada.ALTERAR_PRAZO, texto)

        #self.req.data['opcoes_financ']['prazo'] = sim._prazo
        self.req.data['opcoes_financ']['prazo'] = sim.prazo

        TXT_PRAZO_ABAIXO_MIN: str = 'Prazo abaixo do mínimo permitido. Digite o *prazo* novamente.'
        # por enquanto não precisa salvar prazo no DB
        match self.banco:
            case Banco.CAIXA:
                return self.menu_resultado_caixa(alterar_opcoes_financ=True)
            case Banco.BRADESCO:
                try:
                    return self.menu_resultado_bradesco(alterar=True)
                except ErroResultadoCampoNaoRetornado as erro:
                    return self._response_proxima_entrada(
                        Entrada.ALTERAR_PRAZO, TXT_PRAZO_ABAIXO_MIN
                    )
            case (Banco.ITAU | Banco.SANTANDER):
                try:
                    return self.menu_resultado_itau_santander(alterar=True)
                except ErroResultadoSimulacao as erro:
                    return self._response_proxima_entrada(
                        Entrada.ALTERAR_PRAZO, TXT_PRAZO_ABAIXO_MIN
                    )

    def questao_alterar_valor_entrada_caixa(self) -> tuple[dict, int]:
        # caixa
        self.entrada = Entrada.ALTERAR_VALOR_ENTRADA_CAIXA

        valor_entrada: str = self.req.text
        sim = SimuladorCaixa()
        try:
            sim.valor_entrada = valor_entrada
        except ErroValorEntrada as erro:
            msg: str = f'{erro} Favor digitar *Valor da Entrada* novamente:'
            return self._response_proxima_entrada(
                Entrada.ALTERAR_VALOR_ENTRADA_CAIXA,
                texto=msg
            )
        self.req.data['opcoes_financ']['valor_entrada'] = sim.valor_entrada

        # por enquanto não precisa salvar valor entrada no DB
        return self.menu_resultado_caixa(alterar_opcoes_financ=True)

    def questao_alterar_valor_entrada_itau_santander(self) -> tuple[dict, int]:
        return self.questao_valor_entrada_itau_santander(alterar=True)

    def menu_alterar_sistema_amortizacao(self):
        # somente caixa
        self.entrada = Entrada.MENU_SISTEMA_AMORTIZACAO

        cod_sistema_amortizacao: str = self.req.data['valor']
        self.req.data['opcoes_financ']['cod_sistema_amortizacao'] = \
                                        cod_sistema_amortizacao
        return self.menu_resultado_caixa(alterar_opcoes_financ=True)

    def questao_alterar_prestacao_max(self):
        self.entrada = Entrada.ALTERAR_PRESTACAO_MAX

        prestacao_max: str = self.req.text
        sim = SimuladorCaixa()
        try:
            sim.prestacao_max = prestacao_max
        except ErroPrestacaoMax as erro:
            msg: str = f'{erro} Favor digitar *prestação máxima* novamente:'
            return self._response_proxima_entrada(
                Entrada.ALTERAR_PRESTACAO_MAX,
                texto=msg
            )
        self.req.data['opcoes_financ']['prestacao_max'] = sim.prestacao_max

        # por enquanto não precisa salvar prestação máx no DB
        return self.menu_resultado_caixa(alterar_opcoes_financ=True)

    def questao_alterar_renda(self) -> tuple[dict, int]:
        self.entrada = Entrada.ALTERAR_RENDA_FAMILIAR

        self.questao_renda_familiar(responder=False)
        if self.banco == Banco.CAIXA:
            return self.menu_resultado_caixa(alterar_opcoes_financ=True)
        else:
            return self.menu_resultado_itau_santander(alterar=True)

    def questao_alterar_valor_financiamento_bradesco(self) -> tuple[dict, int]:
        self.entrada = Entrada.ALTERAR_VALOR_FINANCIAMENTO_BRADESCO

        valor_financiamento: str = self.req.text
        valor_max_financiamento: str = self.req.data['opcoes_financ']['valor_max_financiamento']

        sim_brad = SimuladorBradesco()
        sim_brad._setar_valor_max_financiamento(valor_max_financiamento)
        try:
            sim_brad.valor_financiamento = valor_financiamento
        except (ErroValorMaxFinanciamento, ErroValorFinanciamento) as erro:
            msg: str = f'{erro} Favor digitar *valor do financiamento* novamente:'
            return self._response_proxima_entrada(
                Entrada.ALTERAR_VALOR_FINANCIAMENTO_BRADESCO,
                texto=msg
            )
            
        self.req.data['opcoes_financ']['valor_financiamento'] = sim_brad.valor_financiamento
        return self.menu_resultado_bradesco(alterar=True)

    def menu_dicas(self) -> tuple[dict, int]:
        self.entrada = Entrada.MENU_DICAS

        valor = self.req.data['valor']
        if valor == Entrada.MENU_RESULTADO_SIMULACAO.value:
            return self.menu_resultado_caixa(alterar_opcoes_financ=True)
        else:
            return self._response_proxima_entrada(
                entrada=Entrada.MENU_DICA_ITEM,
                texto=valor,
            )
        
    def menu_dica_item(self) -> tuple[dict, int]:
        self.entrada =Entrada.MENU_DICA_ITEM

        valor = self.req.data['valor']
        if valor == Entrada.MENU_RESULTADO_SIMULACAO.value:
            return self.menu_resultado_caixa(alterar_opcoes_financ=True)
        else:
            entrada: Entrada = Entrada(valor)
            return self._response_proxima_entrada(entrada=entrada)

    def _copiar_ultima_simulacao(self, simulacao_atual: SimulacaoModel):
        simulacao_novo: SimulacaoModel = SimulacaoModel()
        simulacao_novo.banco = simulacao_atual.banco
        simulacao_novo.tipo_imovel = simulacao_atual.tipo_imovel
        simulacao_novo.tipo_financiamento = simulacao_atual.tipo_financiamento
        simulacao_novo.tipo_financiamento_bradesco = simulacao_atual.tipo_financiamento_bradesco
        simulacao_novo.renda_bruta = simulacao_atual.renda_bruta
        simulacao_novo.valor_imovel = simulacao_atual.valor_imovel
        simulacao_novo.opcao_financiamento = simulacao_atual.opcao_financiamento

        self.multi360_model.pessoa.simulacoes.append(simulacao_novo)
        self.multi360_model.atualizar()
        # TODO: desativar no banco de dados o preenchimento automático 
        # da data. Forçar data nulo pois preenche automático
        self.multi360_model.pessoa.simulacoes[0].data = None
        self.multi360_model.atualizar()
        self.flag_copiar_sim = True

    def _pular_entrada(self, entrada: Entrada) -> Entrada:
        # verificar se não tá obsoleta
        #return Entrada(entrada.value+1)
        return self._obter_proxima_entrada_por_banco(entrada)

    def _obter_proxima_entrada_por_banco(self, entrada: Entrada=None
                                                            ) -> Entrada:
        """Obtém próxima entrada de acordo com o banco.

        Returns:
            Entrada: retorna próxima entrada.
        """
        if entrada is None:
            entrada = self.entrada
        entradas_banco: tuple = ENTRADA_BANCO[self.banco]
        return entradas_banco[entradas_banco.index(entrada)+1]

    def _response_proxima_entrada(self,
                                  entrada: Entrada=None,
                                  texto: str=None, 
                                  opcoes_menu: list=[dict],
                                  entrada_retornar: Entrada=Entrada.NENHUMA,
                                  texto2: str=None,
                                 ) -> tuple[dict, int]:
        """Responde com  direcionamento pra próxima entrada (endpoint).
        Pode também ser direcionado pra uma entrada específica.

        Args:
            entrada (Entrada, optional):  entrada  específica.  Somente
                quando  não  seguir  o  fluxo normal. Defaults to None.
            texto (str, optional):   texto   que aparecerá  na  próxima
                entrada. Defaults to None.
            opcoes_menu (list[dict], optional):  usado  pra prencher os
                itens  de  entrada  do tipo menu. As opções precisam já
                estar formatadas com uma lista de dicionários.
            entrada_retornar(Entrada, optional): retornar a essa entra-
                da no fim da interação. Por  exemplo  ao chegar ao menu
                opções de financiamento e escolher uma opção pode acon-
                tecer o erro de renda insuficiente, então é preciso  ir
                pra  esse campo e em seguida retornar ao campo anterior.
                Também  será  usado  pra alterar campos e retornar a um 
                menu.
            texto2 (str, optional): texto2  é  usado  nos  casos onde o
                texto  do  arquivo de configuração tem um trecho com {}
                aguardando o método format.

        Returns:
            tuple[dict, int]: json com o response e status code.
        """
        # É retorno de entrada?
        # Foi passado na requisição através do campo data (dict), a 
        # entrada de retorno?
        if self.req.entrada_retornar != Entrada.NENHUMA and entrada is None:
            entrada = self.req.entrada_retornar
            self.req.entrada_retornar = Entrada.NENHUMA

        if not entrada:
            entrada = self._obter_proxima_entrada_por_banco()
            self.entrada = entrada
        else:
            self.entrada = entrada

        # Se tiver definido argumento entrada de retorno guarda no 
        # campo data pra enviar pro response pra ser lido ao executar o
        # próximo response
        self.req.entrada_atual = entrada
        if entrada_retornar != Entrada.NENHUMA:
            self.req.entrada_retornar = entrada_retornar

        match entrada:
            case Entrada.INICIO:
                return self.inicio(permitir_copiar_sim=False)
            case Entrada.CHECAR_CAMPOS:
                return self._checar_campos()
            case Entrada.MENU_BANCO:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.BANCO,
                    opcoes=self._obter_itens_menu_banco(),
                    endpoint=ENDPOINT_MENU_BANCO
                )
            case Entrada.MENU_TIPO_IMOVEL:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.TIPO_IMOVEL,
                    opcoes=self._obter_itens_menu_tipo_imovel(),
                    endpoint=ENDPOINT_MENU_TIPO_IMOVEL
                )
            case Entrada.CIDADE:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.CIDADE,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_CIDADE
                )
            case Entrada.MENU_CIDADES:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.CIDADES,
                    opcoes=self._adicionar_entrada_seq(opcoes_menu),
                    endpoint=ENDPOINT_MENU_CIDADES
                )
            case Entrada.MENU_POSSUI_IMOVEL_CIDADE:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.POSSUI_IMOVEL_CIDADE,
                    opcoes=self._obter_itens_menu_nao_sim(),
                    endpoint=ENDPOINT_MENU_POSSUI_IMOVEL_CIDADE
                )
            case Entrada.TIPO_FINANCIAMENTO:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.TIPO_FINANCIAMENTO,
                    opcoes=self._obter_itens_menu_tipo_financiamento(),
                    endpoint=ENDPOINT_MENU_TIPO_FINANCIAMENTO
                )
            case Entrada.VALOR_IMOVEL:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.VALOR_IMOVEL,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_VALOR_IMOVEL
                )
            case Entrada.VALOR_ENTRADA_ITAU_SANTANDER:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.VALOR_ENTRADA,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_VALOR_ENTRADA_ITAU_SANTANDER
                )
            case Entrada.CPF:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.CPF,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_CPF
                )
            case Entrada.CELULAR:
                # quando for whatsapp não precisa pedir número celular
                if self.req.contact.type == ContactType.WHATSAPP.value:
                    return self._response_proxima_entrada()

                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.CELULAR,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_CELULAR
                )
            case Entrada.RENDA_FAMILIAR:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.RENDA_FAMILIAR,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_RENDA_FAMILIAR
                )
            case Entrada.DATA_NASCIMENTO:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.DATA_NASCIMENTO,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_DATA_NASC
                )
            case Entrada.DATA_NASCIMENTO_CONJUGE:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.DATA_NASCIMENTO_CONJUGE,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_DATA_NASC_CONJUGE
                )
            case Entrada.MENU_TRES_ANOS_FGTS:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.TRES_ANOS_FGTS,
                    opcoes=self._obter_itens_menu_nao_sim(),
                    endpoint=ENDPOINT_MENU_TRES_ANOS_FGTS
                )
            # TODO: pro Bradesco é necessário chamar primeiro essa opção 
            # antes de data nasc. cônjuge
            case Entrada.MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.MAIS_DE_UM_COMPRADOR_DEPENDENTE,
                    opcoes=self._obter_itens_menu_nao_sim(),
                    endpoint=ENDPOINT_MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE
                )
            case Entrada.MENU_SERVIDOR_PUBLICO:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.SERVIDOR_PUBLICO,
                    opcoes=self._obter_itens_menu_nao_sim(),
                    endpoint=ENDPOINT_MENU_SERVIDOR_PUBLICO
                )
            case Entrada.OPCAO_FINANCIAMENTO:
                self._exibir_obs_resultado_simulacao = True
                try:
                    return _response_tipo_menu(
                        txt=texto or ConfMulti360.Menu.OPCOES_FINANCIAMENTO,
                        opcoes=self._obter_itens_menu_opcao_financiamento(),
                        endpoint=ENDPOINT_MENU_OPCOES_FINANCIAMENTO
                    )
                except ErroObterOpcaoFinanciamento as erro:
                    print('#' * 100)
                    print('Erro ao obter opções de financiamento')
                    print(erro)
                    print('#' * 100)
                    return _response_tipo_informacao(
                        txt=ConfMulti360.Menu.OPCOES_FINANCIAMENTO_ERRO
                    )
            case Entrada.MENU_RESULTADO_SIMULACAO:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.RESULTADO_OBS,
                    opcoes=self._obter_itens_menu_resultado(),
                    endpoint=ENDPOINT_MENU_RESULTADO
                )
            case Entrada.MENU_ALTERAR_DADOS:
                self._exibir_obs_resultado_simulacao = True
                msg: str
                if self.flag_copiar_sim:
                    msg = ConfMulti360.Menu.ALTERAR_DADOS
                    self.flag_copiar_sim = False
                else:
                    msg = ConfMulti360.Menu.ALTERAR_DADOS2
                return _response_tipo_menu(
                    txt=texto or msg,
                    opcoes=self._obter_itens_menu_alterar_dados(),
                    endpoint=ENDPOINT_MENU_ALTERAR_DADOS
                )
            case Entrada.MENU_ALTERAR_DADOS2:
                # limpa data pra evitar inserção de outro registro na
                # tabela de simulações
                self.multi360_model.pessoa.simulacoes[0].data = None
                self.multi360_model.atualizar()

                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.ALTERAR_DADOS2,
                    opcoes=self._obter_itens_menu_alterar_dados(),
                    endpoint=ENDPOINT_MENU_ALTERAR_DADOS
                )
            case Entrada.MENU_FINALIZAR_SIMULACAO:
                sugestao_imoveis: str = ''
                txt: str = ConfMulti360.Menu.FINALIZAR_SIMULACAO
                if ConfSiteImobliaria.EXIBIR_URL_FILTRO_IMOVEIS:
                    sugestao_imoveis = ConfMulti360.Menu.SUGESTAO_IMOVEIS.format(
                        self._obter_url_site_imobiliaria()
                    )
                    txt = f'{sugestao_imoveis}\n\n{txt}'
                return _response_tipo_menu(
                    txt=txt,
                    opcoes=self._obter_itens_menu_finalizar_simulacao(),
                    endpoint=ENDPOINT_MENU_FINALIZAR_SIMULACAO,
                )
            case Entrada.ALTERAR_PRAZO:
                txt: str
                if self.banco == Banco.CAIXA or self.banco == Banco.BRADESCO:
                    txt = ConfMulti360.Questao.ALTERAR_PRAZO_MESES.format(texto2)
                else:       # itaú e santander
                    txt = ConfMulti360.Questao.ALTERAR_PRAZO_ANOS.format(texto2)
                return _response_tipo_questao(
                    txt=texto or txt,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_ALTERAR_PRAZO
                )
            case Entrada.ALTERAR_VALOR_ENTRADA_CAIXA:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.ALTERAR_VALOR_ENTRADA.format(texto2),
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_ALTERAR_VALOR_ENTRADA_CAIXA
                )
            case Entrada.ALTERAR_VALOR_ENTRADA_ITAU_SANTANDER:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.VALOR_ENTRADA,
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_ALTERAR_VALOR_ENTRADA_ITAU_SANTANDER
                )
            case Entrada.MENU_SISTEMA_AMORTIZACAO:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.SISTEMA_AMORTIZACAO.format(texto2),
                    opcoes=self._obter_itens_menu_sistema_amortizacao(),
                    endpoint=ENDPOINT_MENU_ALTERAR_SISTEMA_AMORTIZACAO
                )
            case Entrada.ALTERAR_PRESTACAO_MAX:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.ALTERAR_PRESTACAO_MAX.format(texto2),
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_ALTERAR_PRESTACAO_MAX
                )
            case Entrada.ALTERAR_RENDA_FAMILIAR:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.ALTERAR_RENDA.format(texto2),
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_ALTERAR_RENDA
                )
            case Entrada.ALTERAR_VALOR_FINANCIAMENTO_BRADESCO:
                return _response_tipo_questao(
                    txt=texto or ConfMulti360.Questao.ALTERAR_VALOR_FINANCIAMENTO_BRADESCO.format(texto2),
                    dados=self.req.data,
                    endpoint=ENDPOINT_QUESTAO_ALTERAR_VALOR_FINANCIAMENTO_BRADESCO
                )
            case Entrada.ATENDIMENTO_SIMULACAO_OK:
                return _response_tipo_criar_atendimento(
                    dpto_uuid=ConfMulti360.DPTO_UUID,
                )
            case Entrada.MENU_DICAS:
                return _response_tipo_menu(
                    txt=texto or ConfMulti360.Menu.DICAS,
                    opcoes=self._obter_itens_menu_dicas(),
                    endpoint=ENDPOINT_MENU_DICAS
                )
            case Entrada.MENU_DICA_ITEM:
                return _response_tipo_menu(
                    txt=texto,
                    opcoes=self._obter_itens_menu_dica_item(),
                    endpoint=ENDPOINT_MENU_DICA_ITEM
                )

    @property
    def _exibir_obs_resultado_simulacao(self) -> bool:
        # if not 'opcoes_financ' in self.req.data:
        #     return True

        # if not T_EXIBIR_OBS in self.req.data['opcoes_financ'] \
        #    or self.req.data['opcoes_financ'][T_EXIBIR_OBS] == 1:
        #     return True
        # else:
        #     return False

        return (
            not 'opcoes_financ' in self.req.data
            or not T_EXIBIR_OBS in self.req.data['opcoes_financ']
            or self.req.data['opcoes_financ'][T_EXIBIR_OBS] == 1
        )
    
    @_exibir_obs_resultado_simulacao.setter
    def _exibir_obs_resultado_simulacao(self, v: bool) -> None:
        if not 'opcoes_financ' in self.req.data: 
            return
        self.req.data['opcoes_financ'][T_EXIBIR_OBS] = int(v)

    def _obter_itens_menu_banco(self) -> list[dict]:
        """Obtem opções do menu com os bancos aceitos.

        Returns:
            list[dict]: retorna lista de dicionários com os nomes e 
                valores de cada opção.
        """
        BANCOS_ACEITOS: dict = Parametros.BANCOS_ACEITOS
        
        itens_menu: list[dict] = [
            {
                'nome': b.name,
                'valor': b.value,
                'entrada_seq': self.req.entrada_seq.json()
            } for b in Banco if b != Banco.ITAU_L \
                            and b != Banco.ITAU_E_SANTANDER_L \
                            and BANCOS_ACEITOS[b.name.lower()]
        ]
        return itens_menu

    def _obter_itens_menu_tipo_imovel(self) -> list[dict]:
        """Obtem todos os tipos de imóvel. Por enquanto só pra Caixa.
        Residencial, Comercial, será implementado também Rural.

        Returns:
            list[dict]: lista de dicionários com os nomes e valores de
            cada opção.
        """
        tipo_imovel: TipoImovelCaixa
        itens_menu: list[dict] = [
            {
                'nome': tipo_imovel.name,
                'valor': tipo_imovel.value,
                'entrada_seq': self.req.entrada_seq.json()
            } for tipo_imovel in TipoImovelCaixa
        ]
        return itens_menu

    def _adicionar_entrada_seq(self, itens_menu: list[dict]) -> list[dict]:
        """Adiciona entrada_seq em menus que não são carregados a partir 
        de _response_proxima_entrada

        Args:
            itens_menu (list[dict]): lista de dicinoários onde vai ser add.

        Returns:
            list[dict]: retorna a lista de dicionários modificada.
        """
        for d in itens_menu:
            d['entrada_seq'] = self.req.entrada_seq.json()
        return itens_menu

    def _obter_itens_menu_tipo_financiamento(self) -> list[dict]:
        """Obtem opções do menu de tipo de financiamento.

        Returns:
            list[dict]: retorna lista de dicionários com apenas as opções
            novo e usado.
        """
        #TF = TipoFinanciamentoCaixa if self.banco != Banco.BRADESCO else TipoFinanciamentoBradesco

        TF: TipoFinanciamento | tuple[TipoFinanciamentoCaixa]
        if self.banco == Banco.CAIXA:
            # obtem tipo_imovel do DB
            simulacao: SimulacaoModel = self.multi360_model.pessoa.simulacoes[0]

            tipo_imovel = TipoImovelCaixa(simulacao.tipo_imovel)
            if tipo_imovel == TipoImovelCaixa.RESIDENCIAL:
                TF = TipoFinanciamentoCaixa
            elif tipo_imovel == TipoImovelCaixa.COMERCIAL:
                TF = TipoFinanciamentoCaixa.obter_tipos_financiamento_comercial()
            else:   # TODO: implementar RURAL?
                pass
        else:   # Bradesco
            TF = TipoFinanciamentoBradesco

        itens_menu: list[dict] = [
            {
                'nome': tf.name,
                'valor': tf.value,
                'entrada_seq': self.req.entrada_seq.json()
            } for tf in TF
        ]
        return itens_menu
    
    def _obter_itens_menu_nao_sim(self) -> list[dict]:
        itens_menu: list[dict] = [
            {
                'nome': 'NÃO',
                'valor': 0,
                'entrada_seq': self.req.entrada_seq.json()
            },
            {
                'nome': 'SIM',
                'valor': 1,
                'entrada_seq': self.req.entrada_seq.json()
            }
        ]
        return itens_menu

    def _obter_itens_menu_opcao_financiamento(self) -> list[dict]:
        """Obtem  uma  lista de opções de financiamento a partir de  um
        objeto  com   o modelo  da integração e transforma em itens pra
        retornar pro menu. Apenas banco Caixa.

        Args:
            multi360_model (Multi360Model): modelo da tabela da
                integração
            req (Requisicao): objeto que representa a requisição.

        Returns:
            list[dict]: json contendo os dados os itens do menu.
        """
        # obtem os dados do DB pra passar pro simulador e assim obtem
        # as opções de financiamento do simulador
        simulacao: SimulacaoModel = self.multi360_model.pessoa.simulacoes[0]
        cod_caixa: int = self.multi360_model.pessoa.cidade.cod_caixa
        nome: str = self.multi360_model.pessoa.cidade.nome
        nome_sem_aspa: str = self.multi360_model.pessoa.cidade.nome_sem_aspa

        sim: SimuladorCaixa = SimuladorCaixa()
        sim.tipo_imovel = TipoImovelCaixa(simulacao.tipo_imovel)
        sim.adicionar_cidade(cod_caixa, nome, nome_sem_aspa)
        sim.cidade_indice = 0
        sim.tipo_financiamento = TipoFinanciamentoCaixa(simulacao.tipo_financiamento)
        sim.possui_imovel_cidade = self.multi360_model.pessoa.possui_imovel_cidade
        sim.valor_imovel = simulacao.valor_imovel
        sim.cpf = self.multi360_model.pessoa.cpf
        sim.celular = self.multi360_model.pessoa.fone
        sim.renda_familiar = simulacao.renda_bruta
        sim.data_nascimento = self.multi360_model.pessoa.data_nasc
        sim.tres_anos_fgts = self.multi360_model.pessoa.tres_anos_fgts
        sim.mais_de_um_comprador_dependente = \
            self.multi360_model.pessoa.mais_de_um_comprador_dependente
        sim.servidor_publico = \
            self.multi360_model.pessoa.servidor_publico

        opcoes_financiamento: list[OpcaoFinanciamento]
        try:
            opcoes_financiamento = sim.obter_opcoes_financiamento()
        except ErroObterOpcaoFinanciamento as erro:
            # TODO: relatar problema ao desenvolvedor e registrar log
            # TODO: exibir informação simplificada ao contato?
            raise

        opcao_financiamento: OpcaoFinanciamento
        itens_menu: list[dict] = []
        for opcao_financiamento in opcoes_financiamento:
            itens_menu.append(
                {
                    'nome': opcao_financiamento.descricao,
                    'valor': opcao_financiamento.value,
                    'versao': opcao_financiamento.versao,
                    'entrada_seq': self.req.entrada_seq.json()
                }
            )
        return itens_menu

    def _obter_itens_menu_resultado(self) -> list[dict]:
        
        entrada_seq: dict = self.req.entrada_seq.json()
        itens: list[tuple] = []
        opcoes_financ: dict = self.req.data['opcoes_financ']
        match self.banco:
            case Banco.BRADESCO:
                itens = [
                    ('Alterar Prazo', Entrada.ALTERAR_PRAZO),
                    ('Alterar Valor Financiamento', 
                        Entrada.ALTERAR_VALOR_FINANCIAMENTO_BRADESCO),
                    ('Alterar Dados Pessoais e de Imóvel', Entrada.MENU_ALTERAR_DADOS2),
                    ('Finalizar Simulação', Entrada.MENU_FINALIZAR_SIMULACAO),
                ]                
            case Banco.CAIXA:
                itens = [
                    ('Alterar Prazo', Entrada.ALTERAR_PRAZO),
                    ('Alterar Valor da Entrada', Entrada.ALTERAR_VALOR_ENTRADA_CAIXA),
                    ('Alterar Sistema Amortização', Entrada.MENU_SISTEMA_AMORTIZACAO),
                    ('Alterar Prestação Máxima', Entrada.ALTERAR_PRESTACAO_MAX),
                    ('Alterar Renda Familiar', Entrada.ALTERAR_RENDA_FAMILIAR),
                    ('Outra Opção de Financiamento', Entrada.OPCAO_FINANCIAMENTO),
                    ('Alterar Dados Pessoais e de Imóvel', Entrada.MENU_ALTERAR_DADOS2),
                    ('Finalizar Simulação', Entrada.MENU_FINALIZAR_SIMULACAO),
                ]
            case (Banco.ITAU | Banco.ITAU_L | Banco.SANTANDER):
                itens = [
                    ('Alterar Prazo', Entrada.ALTERAR_PRAZO),
                    ('Alterar Valor da Entrada', \
                        Entrada.ALTERAR_VALOR_ENTRADA_ITAU_SANTANDER),
                    ('Alterar Dados Pessoais e de Imóvel', Entrada.MENU_ALTERAR_DADOS2),
                    ('Finalizar Simulação', Entrada.MENU_FINALIZAR_SIMULACAO),
                ]

        nome: str
        valor: Entrada
        itens_menu: list[dict] = [
            {
                'nome': nome,
                'valor': valor.value,
                'opcoes_financ': opcoes_financ,
                'entrada_seq': entrada_seq
            } for nome, valor in itens
        ]
        return itens_menu

    def _obter_itens_menu_alterar_dados(self) -> list[dict]:
        # TODO: celular somente se for diferente de whatsapp
        ## opção de financiamento -> selecionar novamente
        pessoa: PessoaModel = self.multi360_model.pessoa
        simulacao: SimulacaoModel = self.multi360_model.pessoa.simulacoes[0]
        banco: Banco = self.banco
        cpf: str
        cpf: str = Cpf(pessoa.cpf).formatar() \
            if self.banco == Banco.BRADESCO or self.banco == Banco.CAIXA \
               or self.banco == Banco.ITAU and pessoa.cpf is not None \
            else ''
        fone: str = Fone.a_partir_de_fmt_comum(pessoa.fone).formatar()
        data_nasc: str = date.strftime(pessoa.data_nasc, '%d/%m/%Y')
        mais_de_um_comprador_dependente: str = 'SIM' \
            if pessoa.mais_de_um_comprador_dependente else 'NÃO'
        valor_imovel = Decimal2(simulacao.valor_imovel).formatar_moeda()
        valor_entrada = Decimal2(simulacao.valor_entrada).formatar_moeda() \
            if simulacao.valor_entrada is not None\
            else Decimal2('0').formatar_moeda()
        renda_familiar = Decimal2(simulacao.renda_bruta).formatar_moeda() \
            if simulacao.renda_bruta is not None else ''

        E = Entrada
        itens: list[tuple] = []
        if not SimuladorBase.apenas_um_banco_habilitado():
            itens = [
                ('Banco:', banco.name, E.MENU_BANCO.value),
            ]

        match self.banco:
            case Banco.BRADESCO:
                data_nasc_conjuge: str = date.strftime(pessoa.data_nasc_conjuge, '%d/%m/%Y') \
                    if pessoa.data_nasc_conjuge is not None else ''

                tipo_financiamento_bradesco: str = TipoFinanciamentoBradesco(
                    simulacao.tipo_financiamento_bradesco
                ).name if simulacao.tipo_financiamento_bradesco is not None \
                    else TipoFinanciamentoBradesco.NOVO
                
                itens += [
                    ('CPF:', cpf, E.CPF.value),
                    #('Celular:', fone, E.CELULAR.value),
                    ('Nascimento:', data_nasc, E.DATA_NASCIMENTO.value),
                    ('Somar renda cônjuge:',
                        mais_de_um_comprador_dependente,
                        E.MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE.value),
                    ('Nascimento Cônjuge:', data_nasc_conjuge, E.DATA_NASCIMENTO_CONJUGE.value),
                    ('Tipo Financiamento:', tipo_financiamento_bradesco, E.TIPO_FINANCIAMENTO.value),
                    ('Valor Imóvel:', valor_imovel, E.VALOR_IMOVEL.value),
                    ('Simular', '', E.MENU_RESULTADO_SIMULACAO_BRADESCO.value)
                ]
            case Banco.CAIXA:
                tipo_imovel: TipoImovelCaixa = TipoImovelCaixa(simulacao.tipo_imovel)
                cidade: str = pessoa.cidade.nome
                possui_imovel_cidade: str = 'SIM' \
                    if pessoa.possui_imovel_cidade else 'NÃO'
                tres_anos_fgts: str = 'SIM' if pessoa.tres_anos_fgts else 'NÃO'
                servidor_publico: str = 'SIM' if pessoa.servidor_publico else 'NÃO'
                tipo_financiamento: str = TipoFinanciamentoCaixa(
                    simulacao.tipo_financiamento
                ).name

                itens += [
                    ('Tipo Imóvel:', tipo_imovel.name, E.MENU_TIPO_IMOVEL.value),
                    ('Tipo Financiamento:', tipo_financiamento, E.TIPO_FINANCIAMENTO.value),
                    ('Cidade:', cidade, E.CIDADE.value),
                    ('CPF:', cpf, E.CPF.value),
                    ('Celular:', fone, E.CELULAR.value),
                    ('Nascimento:', data_nasc, E.DATA_NASCIMENTO.value),
                    ('Possui imóvel na cidade:', possui_imovel_cidade,
                        E.MENU_POSSUI_IMOVEL_CIDADE.value),
                    ('Possui 3 anos FGTS:', tres_anos_fgts,
                        E.MENU_TRES_ANOS_FGTS.value),
                    ('Mais de um comprador e/ou dependente:',
                        mais_de_um_comprador_dependente,
                        E.MENU_MAIS_DE_UM_COMPRADOR_DEPENDENTE.value),
                    ('É servidor público?', servidor_publico,
                        E.MENU_SERVIDOR_PUBLICO.value),
                    ('Valor Imóvel:', valor_imovel, E.VALOR_IMOVEL.value),
                    ('Renda Familiar:', renda_familiar, E.RENDA_FAMILIAR.value),
                    ('Simular', '', E.OPCAO_FINANCIAMENTO.value)
                ]
            case Banco.ITAU:        # selenium
                e_simular: Entrada = E.MENU_RESULTADO_SIMULACAO_ITAU_SANTANDER
                itens += [
                    ('CPF:', cpf, E.CPF.value),
                    ('Celular:', fone, E.CELULAR.value),
                    ('Nascimento:', data_nasc, E.DATA_NASCIMENTO.value),
                    ('Valor Imóvel:', valor_imovel, E.VALOR_IMOVEL.value),
                    ('Valor Entrada:', valor_entrada, \
                         E.VALOR_ENTRADA_ITAU_SANTANDER.value),
                    ('Nascimento:', data_nasc, E.DATA_NASCIMENTO.value),
                    ('Simular', '', e_simular.value)
                ]                
            case (Banco.ITAU_L | Banco.SANTANDER):
                e_simular: Entrada = E.MENU_RESULTADO_SIMULACAO_ITAU_SANTANDER
                itens += [
                    #('CPF:', cpf, E.CPF.value),
                    ('Celular:', fone, E.CELULAR.value),
                    ('Nascimento:', data_nasc, E.DATA_NASCIMENTO.value),
                    ('Valor Imóvel:', valor_imovel, E.VALOR_IMOVEL.value),
                    ('Valor Entrada:', valor_entrada, \
                         E.VALOR_ENTRADA_ITAU_SANTANDER.value),
                    ('Nascimento:', data_nasc, E.DATA_NASCIMENTO.value),
                    ('Renda Familiar:', renda_familiar, E.RENDA_FAMILIAR.value),
                    ('Simular', '', e_simular.value)
                ]

        itens_menu: list[dict] = [
            {
                'nome': f'{nome} {valor}',
                'valor': entrada,
                'entrada_seq': self.req.entrada_seq.json()
            } for nome, valor, entrada in itens
        ]

        return itens_menu

    def _obter_itens_menu_sistema_amortizacao(self) -> list[dict]:
        opcoes_financ: dict = self.req.data['opcoes_financ']
        entrada_seq: dict = self.req.entrada_seq.json()
        cods_sistema_amortizacao: dict[str,str] = \
            self.req.data['opcoes_financ']['cods_sistema_amortizacao']

        itens_menu: list[dict] = []
        for nome, valor in cods_sistema_amortizacao.items():
            itens_menu.append(
                {
                    'nome': nome,
                    'valor': valor,
                    'opcoes_financ': opcoes_financ,
                    'entrada_seq': entrada_seq
                }
            )
        return itens_menu

    def _obter_itens_menu_finalizar_simulacao(self) -> list[dict]:
        opcoes_financ: dict = self.req.data['opcoes_financ']
        entrada_seq: dict = self.req.entrada_seq.json()
        itens: list[tuple] = [
            ('Sim', Entrada.ATENDIMENTO_SIMULACAO_OK.value),
            ('Dicas pra melhorar simulação', Entrada.MENU_DICAS.value),
            ('Voltar pra simulação', Entrada.MENU_RESULTADO_SIMULACAO.value),
        ]
        
        itens_menu: list[dict] = [
            {
                'nome': nome,
                'valor': valor,
                'opcoes_financ': opcoes_financ,
                'entrada_seq': entrada_seq
            } for nome, valor in itens
        ]
        return itens_menu
    
    # def _obter_anexos_menu_finalizar_simulacao(self) -> list[dict]:
    #     anexos: list = []

    #     PERC_VARIACAO = ConfSiteImobliaria.VALOR_IMOVEL_PERC_VARIACAO
    #     sim = SimuladorCaixa()
    #     simulacao: SimulacaoModel = self.multi360_model.pessoa.simulacoes[0]
    #     sim.valor_imovel = simulacao.valor_imovel
    #     si = SiteImobiliaria.a_partir_de_valor_imovel(
    #         sim._valor_imovel,
    #         PERC_VARIACAO
    #     )
    #     print('*' * 100)
    #     print(si.url)

    #     adicionar_anexo_response(
    #         anexos,
    #         'Imóveis',
    #         si.url,
    #         position='BEFORE',
    #         type='TEXT'
    #     )
    #     return anexos

    def _obter_url_site_imobiliaria(self) -> str:
        PERC_VARIACAO = ConfSiteImobliaria.VALOR_IMOVEL_PERC_VARIACAO
        sim = SimuladorCaixa()
        simulacao: SimulacaoModel = self.multi360_model.pessoa.simulacoes[0]
        sim.valor_imovel = simulacao.valor_imovel
        si = SiteImobiliaria.a_partir_de_valor_imovel(
            sim._valor_imovel,
            PERC_VARIACAO
        )
        print('*' * 100)
        print(si.url)
        
        return si.url




    def _obter_itens_menu_dicas(self) -> list[dict]:
        opcoes_financ: dict = self.req.data['opcoes_financ']
        entrada_seq: dict = self.req.entrada_seq.json()

        i: int = 0
        t: tuple
        itens_menu: list[dict] = []
        nome: str = ''
        valor: str = ''
        while True:
            i += 1
            t = getattr(ConfMulti360.MenuDicas, f'DICA{i}', None)
            rs = Entrada.MENU_RESULTADO_SIMULACAO.value
            nome, valor = t if t else ('Voltar pra Simulação', rs)
            itens_menu.append(
                {
                    'nome': nome,
                    'valor': valor,
                    'opcoes_financ': opcoes_financ,
                    'entrada_seq': entrada_seq
                }
            )
            if not t: break

        return itens_menu

    def _obter_itens_menu_dica_item(self) -> list[dict]:
        opcoes_financ: dict = self.req.data['opcoes_financ']
        entrada_seq: dict = self.req.entrada_seq.json()

        itens: list[tuple] = [
            ('Voltar pra Menu Dicas', Entrada.MENU_DICAS.value),
            ('Voltar pra Simulação', Entrada.MENU_RESULTADO_SIMULACAO.value),
            ('Alterar Dados Pessoais ou de Imóvel', Entrada.MENU_ALTERAR_DADOS2.value),
        ]
        
        itens_menu: list[dict] = [
            {
                'nome': nome,
                'valor':valor,
                'opcoes_financ': opcoes_financ,
                'entrada_seq': entrada_seq
            } for nome, valor in itens
        ]
        return itens_menu


def _response_tipo_questao(txt: str, dados: dict, 
                           endpoint: str
                           ) -> tuple[dict, int]:
    """Retorna response com uma pergunta.
    """
    tipo: TipoResposta = TipoResposta.QUESTAO
    endpoint: str = request.url_root[:-1] + url_for(endpoint)
    
    if not dados: dados = {}
    
    return {
        'type': tipo.value,
        'text': txt,
        'attachments': [],
        'callback': {
            'endpoint': endpoint,
            'data': dados
        }
    }, 200

def _response_tipo_menu(txt: str, opcoes: list, endpoint: str,
                        attachments: list=[]) -> tuple[dict, int]:
    """Retorna  um  menu  de opções com as callbacks pra que o usuário
    selecione e então dê continuidade a interação.

    Args:
        txt (str): título do menu.
        opcoes (list): opções do menu.
        endpoint (str): endpoint pro menu.

    Returns:
        tuple(dict, int): retorna um response com o dicionário contendo
        a resposta e um int com o código do status.
    """
    tipo: TipoResposta = TipoResposta.MENU
    url_root: str = request.url_root[:-1]

    items: list = []
    for i, item in enumerate(opcoes):
        items.append(
            {
                'number': i + 1,
                'text': item['nome'],
                'callback': {
                    'endpoint': url_root + url_for(endpoint),
                    'data': item
                }
            }
        )

    return {
        'type': tipo.value,
        'text': txt,
        'attachments': attachments,
        'items': items
    }, 200


def adicionar_anexo_response(lista: list, name: str, url: str, 
                position: str='BEFORE', type: str='DOCUMENT'):
    lista.append(
        {
            'position': position,
            'type': type,
            'name': name,
            'url': url      #'text': url
        }
    )


def _response_tipo_informacao(txt: str, anexos: list=[]) -> tuple[dict, int]:
    tipo: TipoResposta = TipoResposta.INFORMACAO

    return {
        'type': tipo.value,
        'text': txt,
        'attachments': anexos,
    }, 200

def _response_tipo_criar_atendimento(dpto_uuid: str, usuario_uuid: str = None
                                                       ) -> tuple[dict, int]:
    tipo: TipoResposta = TipoResposta.CRIAR_ATENDIMENTO
    r: dict = {
        'type': tipo.value,
        'departmentUUID': dpto_uuid
    }
    if usuario_uuid: r['userUUID'] = usuario_uuid
    return r