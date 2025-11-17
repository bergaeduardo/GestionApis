# 📦 Sistema de Gestión de Envíos Welivery

## 🎯 ¿Para qué sirve?

Sistema de integración con la API de Welivery para automatizar la gestión de envíos y seguimiento de pedidos. Proporciona sincronización automática entre la base de datos interna y la plataforma Welivery.

### Funcionalidades principales:
- 🔄 Sincronización automática de estados de envío
- 📊 Consultas masivas optimizadas 
- 🛡️ Manejo robusto de errores
- 📝 Logging detallado para auditoría

## 🚀 Instalación

### Prerrequisitos
- Python 3.8+
- Acceso a SQL Server
- Credenciales de API Welivery

### Pasos de instalación

1. **Instalar dependencias**:
```bash
pip install aiohttp pyodbc
```

2. **Configurar credenciales** en `../common/credenciales.py`:
```python
WELIVERY = {
    "url": "https://sistema.welivery.com.ar/api/delivery/status",
    "user": "tu_usuario",
    "password": "tu_password"
}
```

3. **Verificar conectividad**:
```bash
python test_welivery.py
```

## ⚡ Puesta en marcha

### Ejecución básica
```bash
cd GestionAPI/Welivery
python sync_welivery.py
```

### Uso programático
```python
from sync_welivery import WeliverySync
import asyncio

async def main():
    sync = WeliverySync()
    try:
        stats = await sync.sincronizacion_completa()
        print(f"Estados actualizados: {stats['estados_actualizados']}")
    finally:
        await sync.close()

asyncio.run(main())
```

## 📋 Comandos útiles

```bash
# Ejecutar sincronización completa
python sync_welivery.py

# Ejecutar pruebas
python test_welivery.py

# Ver logs
tail -f logs/welivery.log
```



## 📞 Soporte

- 🐛 Issues: Sistema de gestión de proyectos
- 📧 Email: bergaeduardo@gmail.com

---
**Versión**: 1.0 | **Estado**: Producción ✅