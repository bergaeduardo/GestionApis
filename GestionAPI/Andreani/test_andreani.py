#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from GestionAPI.Andreani.andreani_api import AndreaniAPI
from GestionAPI.Andreani.db_operations_andreani import AndreaniDB
from GestionAPI.common.credenciales import DATA_QA

class TestAndreani(unittest.IsolatedAsyncioTestCase):

    async def test_api_connection(self):
        """Verifica que la conexión a la API de Andreani sea exitosa."""
        try:
            base_url_qa = DATA_QA["url"]
            user = DATA_QA["user"]
            password = DATA_QA["passw"]
            api = AndreaniAPI(base_url_qa, user, password)
            self.assertIsNotNone(api, "La inicialización de AndreaniAPI falló.")
            # Realizar una llamada simple para verificar la conexión y autenticación
            token = await api._get_auth_token()
            self.assertIsNotNone(token, "La obtención del token de autenticación falló.")
            print("Conexión a la API de Andreani exitosa.")
        except Exception as e:
            self.fail(f"La conexión a la API de Andreani falló con el error: {e}")

    def test_db_connection(self):
        """Verifica que la conexión a la base de datos sea exitosa."""
        try:
            andreani_db = AndreaniDB()
            cursor = andreani_db.conexion.conectar()
            self.assertIsNotNone(cursor, "La conexión a la base de datos falló.")
            print("Conexión a la base de datos exitosa.")
            cursor.close()
        except Exception as e:
            self.fail(f"La conexión a la base de datos falló con el error: {e}")

if __name__ == '__main__':
    unittest.main()
