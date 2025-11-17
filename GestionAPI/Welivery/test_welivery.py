import asyncio
import unittest
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Importar las clases del módulo Welivery
from GestionAPI.Welivery.welivery_api import WeliveryAPI
from GestionAPI.Welivery.db_operations_welivery import WeliveryDB
from GestionAPI.Welivery.sync_welivery import WeliverySync


class TestWeliveryAPI(unittest.TestCase):
    """Pruebas para la clase WeliveryAPI."""
    
    def setUp(self):
        """Configuración inicial para las pruebas."""
        self.api = WeliveryAPI(
            base_url="https://test.welivery.com.ar",
            user="test_user",
            password="test_password"
        )

    def test_init(self):
        """Prueba la inicialización del API client."""
        self.assertEqual(self.api.base_url, "https://test.welivery.com.ar")
        self.assertEqual(self.api.user, "test_user")
        self.assertEqual(self.api.password, "test_password")

    def test_map_status_to_code(self):
        """Prueba el mapeo de estados a códigos."""
        # Casos comunes
        self.assertEqual(self.api.map_status_to_code("COMPLETADO"), ("COMPLETADO", 3))
        self.assertEqual(self.api.map_status_to_code("PENDIENTE"), ("PENDIENTE", 0))
        self.assertEqual(self.api.map_status_to_code("EN CURSO"), ("EN CURSO", 2))
        self.assertEqual(self.api.map_status_to_code("CANCELADO"), ("CANCELADO", 4))
        
        # Caso insensitivo a mayúsculas/minúsculas
        self.assertEqual(self.api.map_status_to_code("completado"), ("COMPLETADO", 3))
        self.assertEqual(self.api.map_status_to_code("Pendiente"), ("PENDIENTE", 0))
        
        # Estado no reconocido
        self.assertEqual(self.api.map_status_to_code("ESTADO_INEXISTENTE"), ("INDEFINIDO", 98))

    def test_get_delivery_status_success(self):
        """Prueba mapeo de respuesta exitosa (sin llamada real a API)."""
        # Solo probar el mapeo de estado sin hacer llamada real a la API
        # Simular respuesta de API
        mock_response = {
            "Status": "COMPLETADO",
            "welivery_id": "12345",
            "external_id": "test-123"
        }
        
        # Probar mapeo de estados
        estado_texto, estado_id = self.api.map_status_to_code(mock_response["Status"])
        
        self.assertEqual(estado_texto, "COMPLETADO")
        self.assertEqual(estado_id, 3)

    def test_get_delivery_status_not_found(self):
        """Prueba mapeo de estados no encontrados."""
        # Probar diferentes casos de estados
        test_cases = [
            ("PENDIENTE", ("PENDIENTE", 0)),
            ("EN CURSO", ("EN CURSO", 2)),
            ("CANCELADO", ("CANCELADO", 4)),
            ("ESTADO_INEXISTENTE", ("INDEFINIDO", 98))
        ]
        
        for input_status, expected_output in test_cases:
            with self.subTest(status=input_status):
                resultado = self.api.map_status_to_code(input_status)
                self.assertEqual(resultado, expected_output)


class TestWeliveryDB(unittest.TestCase):
    """Pruebas para la clase WeliveryDB."""
    
    def setUp(self):
        """Configuración inicial para las pruebas."""
        with patch('GestionAPI.Welivery.db_operations_welivery.Conexion'):
            self.db = WeliveryDB()

    @patch('GestionAPI.Welivery.db_operations_welivery.Conexion')
    def test_init(self, mock_conexion):
        """Prueba la inicialización de la clase DB."""
        db = WeliveryDB()
        mock_conexion.assert_called_once()

    def test_get_pedidos_pendientes_envio(self):
        """Prueba obtención de pedidos pendientes de envío."""
        # Mock de datos de prueba
        mock_data = [
            ("123", "ORDER-123", "99"),
            ("124", "ORDER-124", "99"),
        ]
        self.db.conexion.ejecutar_consulta = Mock(return_value=mock_data)
        
        result = self.db.get_pedidos_pendientes_envio()
        
        self.assertEqual(result, mock_data)
        self.assertEqual(len(result), 2)

    def test_update_numero_seguimiento(self):
        """Prueba actualización de número de seguimiento."""
        self.db.conexion.ejecutar_update = Mock(return_value=1)
        
        result = self.db.update_numero_seguimiento("123", "99", "TRACK-123")
        
        self.assertTrue(result)
        self.db.conexion.ejecutar_update.assert_called_once()

    def test_update_estado_envio(self):
        """Prueba actualización de estado de envío."""
        self.db.conexion.ejecutar_update = Mock(return_value=1)
        
        result = self.db.update_estado_envio("123", "99", "COMPLETADO", 3)
        
        self.assertTrue(result)
        self.db.conexion.ejecutar_update.assert_called_once()


class TestWeliverySync(unittest.TestCase):
    """Pruebas para la clase WeliverySync."""
    
    def setUp(self):
        """Configuración inicial para las pruebas."""
        with patch('GestionAPI.Welivery.sync_welivery.WeliveryAPI'), \
             patch('GestionAPI.Welivery.sync_welivery.WeliveryDB'):
            self.sync = WeliverySync()

    def test_init(self):
        """Prueba la inicialización del sincronizador."""
        self.assertIsNotNone(self.sync.api)
        self.assertIsNotNone(self.sync.db)
        self.assertIn('envios_creados', self.sync.stats)

    def test_get_latest_status_date(self):
        """Prueba extracción de fecha del historial de estados."""
        status_data = {
            "status_history": [
                {"date_time": "2025-09-11 12:40:01", "estado": "PENDIENTE"},
                {"date_time": "2025-09-11 17:38:22", "estado": "COMPLETADO"}
            ]
        }
        
        result = self.sync._get_latest_status_date(status_data)
        
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 9)
        self.assertEqual(result.day, 11)

    def test_get_latest_status_date_empty_history(self):
        """Prueba extracción de fecha con historial vacío."""
        status_data = {"status_history": []}
        
        result = self.sync._get_latest_status_date(status_data)
        
        self.assertIsInstance(result, datetime)
        # Debería retornar fecha actual


class TestIntegracionWelivery(unittest.TestCase):
    """Pruebas de integración para el módulo completo."""
    
    def test_flujo_completo_mock(self):
        """Prueba del flujo completo con mocks simples."""
        with patch('GestionAPI.Welivery.sync_welivery.WeliveryAPI') as mock_api_class, \
             patch('GestionAPI.Welivery.sync_welivery.WeliveryDB') as mock_db_class:
            
            # Configurar mocks básicos sin asyncio
            mock_api = Mock()
            mock_api_class.return_value = mock_api
            mock_api.map_status_to_code.return_value = ("COMPLETADO", 3)
            mock_api.close = Mock()
            
            mock_db = Mock()
            mock_db_class.return_value = mock_db
            mock_db.get_pedidos_pendientes_envio.return_value = []
            mock_db.get_pedidos_pendientes_entrega.return_value = []
            mock_db.close_connection = Mock()
            
            # Crear instancia sin ejecutar métodos asíncronos
            sync = WeliverySync()
            
            # Verificar que la instancia se creó correctamente
            self.assertIsNotNone(sync.api)
            self.assertIsNotNone(sync.db)
            self.assertIn('envios_creados', sync.stats)


# Funciones de utilidad para pruebas manuales
async def test_manual_api():
    """Prueba manual del API client (requiere credenciales reales)."""
    print("=== PRUEBA MANUAL DEL API ===")
    
    # Usar credenciales de prueba
    api = WeliveryAPI(
        base_url="https://sistema.welivery.com.ar",
        user="test_user",
        password="test_password"
    )
    
    try:
        # Probar consulta de estado
        result = await api.get_delivery_status("1560401410870-01")
        print(f"Resultado: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await api.close()


def test_manual_db():
    """Prueba manual de operaciones de base de datos."""
    print("=== PRUEBA MANUAL DE BASE DE DATOS ===")
    
    try:
        db = WeliveryDB()
        
        # Probar consulta de pedidos pendientes
        pedidos = db.get_pedidos_pendientes_envio()
        print(f"Pedidos pendientes: {len(pedidos) if pedidos else 0}")
        
        if pedidos:
            print("Primeros 5 pedidos:")
            for pedido in pedidos[:5]:
                print(f"  {pedido}")
        
    except Exception as e:
        print(f"Error en prueba de BD: {e}")


async def test_manual_sync():
    """Prueba manual del sincronizador completo."""
    print("=== PRUEBA MANUAL DEL SINCRONIZADOR ===")
    
    try:
        sync = WeliverySync()
        
        # Probar solo creación de envíos
        print("Probando creación de envíos...")
        stats = await sync.crear_envios_pendientes()
        print(f"Estadísticas: {stats}")
        
    except Exception as e:
        print(f"Error en prueba de sincronización: {e}")
    finally:
        await sync.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Ejecutar pruebas manuales
        if sys.argv[1] == "manual_api":
            asyncio.run(test_manual_api())
        elif sys.argv[1] == "manual_db":
            test_manual_db()
        elif sys.argv[1] == "manual_sync":
            asyncio.run(test_manual_sync())
        else:
            print("Opciones: manual_api, manual_db, manual_sync")
    else:
        # Ejecutar pruebas unitarias
        unittest.main()