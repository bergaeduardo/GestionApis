# Módulo de Sincronización de Stock - Jauser

## Descripción
Este módulo se encarga de sincronizar el stock de productos desde la API de Jauser hacia la base de datos local. Obtiene información de stock de dos depósitos: Nacional y Fiscal.

## Estructura del Módulo
```
Jauser/
├── api_jauser.py          # Cliente API para Jauser
├── db_operations_jauser.py # Operaciones de base de datos
├── sync_stock_Jauser.py   # Script principal de sincronización
├── consultas.py          # Consultas SQL reutilizables
└── test_sync.py         # Script de pruebas
```

## Instalación y Configuración

### 1. Configuración de Base de Datos
Ejecutar el script SQL ubicado en `scripts/create_jauser_table.sql` para crear la tabla necesaria.

### 2. Configuración de Credenciales
Asegurarse de tener configuradas las credenciales en `common/credenciales.py`:
```python
JAUSER = {
    'username': 'tu_usuario',
    'password': 'tu_contraseña'
}
```

### 3. Instalación de Dependencias
```bash
pip install requests pyodbc
```

## Uso

### Sincronización Completa
```bash
python Jauser/sync_stock_Jauser.py
```

### Pruebas
```bash
python Jauser/test_sync.py
```

## Funcionalidades

### Endpoints de API
- **Login**: `POST https://api-jys.jauser.global/api/login`
- **Stock Nacional**: `GET https://api-jys.jauser.global/api/magaya/items-jiwory`
- **Stock Fiscal**: `GET https://api-jys.jauser.global/api/magaya/items-jiwory-fiscal`

### Campos de la Tabla
- `piezas`: Cantidad de piezas en stock
- `descripcion`: Descripción del producto
- `codigo`: Código único del producto
- `model`: Modelo o categoría del producto
- `tipo_deposito`: Tipo de depósito (NACIONAL o FISCAL)
- `fecha_actualizacion`: Fecha y hora de la última actualización

## Flujo de Sincronización
1. Obtener token de autenticación
2. Consultar stock Nacional
3. Consultar stock Fiscal
4. Limpiar datos existentes por tipo de depósito
5. Insertar nuevos datos
6. Registrar logs del proceso

## Logs
Los logs se generan en el directorio de logs configurado en `common/logger_config.py`
