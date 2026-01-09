#!/usr/bin/env python
# coding: utf-8
"""
App API Simulador de Crédito Imobiliário.
"""
__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.3'


from rest_api.app_factory import create_app
from rest_api.bootstrap import bootstrap_database

app = create_app()

with app.app_context():
    bootstrap_database()

if __name__ == '__main__':
    app.run('0.0.0.0', 8080)
