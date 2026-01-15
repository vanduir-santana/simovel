from flask import Blueprint

from rest_api.apis.ns_v1 import api_v1 as ns_v1_bp


api_v1 = Blueprint(
    'api_v1',
    __name__,
    url_prefix='/api/v1'
)

api_v1.register_blueprint(ns_v1_bp)
