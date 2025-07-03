from flask import Blueprint
from flask_restx import Api
from rest_api.apis.ns_multi360 import api as ns_multi360
from config.geral import Api as CfgApi

URL_PREFIX_MULTI_360 = CfgApi.URL_PREFIX_MULTI_360

blueprint = Blueprint('api_multi360', __name__, url_prefix=URL_PREFIX_MULTI_360)
api = Api(blueprint,
    title='Simóvel - API de integração com o Multi 360.',
    version='1.0'
)

api.add_namespace(ns_multi360)