#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import logging
from GestionAPI.common.credenciales import obtener_credenciales

logger = logging.getLogger(__name__)

class JauserAPI:
    def __init__(self):
        self.base_url = "https://api-jys.jauser.global/api/"
        self.credentials = obtener_credenciales('jauser') # Asegúrate de tener una sección 'jauser' en tu archivo de credenciales
        if not self.credentials:
            logger.error("No se encontraron credenciales para Jauser.")
            raise ValueError("Credenciales de Jauser no encontradas.")

    def get_token(self):
        login_url = f"{self.base_url}login"
        headers = {"Content-Type": "application/json"}
        data = {
            "username": self.credentials.get('username'),
            "password": self.credentials.get('password')
        }
        try:
            logger.info(f"Intentando obtener token de {login_url}")
            resp = requests.post(login_url, headers=headers, json=data)
            resp.raise_for_status() # Lanza una excepción para códigos de estado de error (4xx o 5xx)
            token = resp.json().get('token') # Ajusta según la respuesta real de la API
            if token:
                logger.info("Token obtenido.")
                return token
            else:
                logger.error("No se encontró token en la respuesta: %s", resp.text)
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener token: {e}")
            return None

    def get_stock_nacional(self, token):
        stock_url = f"{self.base_url}magaya/items-jiwory"
        headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
            }
        try:
            logger.info(f"Consultando stock nacional desde {stock_url}")
            resp = requests.get(stock_url, headers=headers)
            resp.raise_for_status()
            return resp.json().get('Items', []) # Asume que el stock está en la clave 'Items'
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener stock nacional: {e}")
            return None

    def get_stock_fiscal(self, token):
        stock_url = f"{self.base_url}magaya/items-jiwory-fiscal"
        headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
            }
        try:
            logger.info(f"Consultando stock fiscal desde {stock_url}")
            resp = requests.get(stock_url, headers=headers)
            resp.raise_for_status()
            return resp.json().get('Items', []) # Asume que el stock está en la clave 'Items'
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener stock fiscal: {e}")
            return None
