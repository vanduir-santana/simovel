#!/usr/bin/env python
# coding: utf-8
"""
App API Simulador de Crédito Imobiliário.
"""
__author__ = 'Vanduir Santana Medeiros'
__version__ = '0.3'


from rest_api.app_factory import create_app


app = create_app()


if __name__ == '__main__':
    app.run('0.0.0.0', 8080)
