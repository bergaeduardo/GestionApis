# InterBanking — API Consultiva

Integración con la plataforma InterBanking para consulta de información financiera de cuentas bancarias.

**API Version:** Saldos v1.1 / Información Financiera v1.0.0  
**Contacto soporte IBK:** consultasapi@interbanking.com.ar  
**Contacto desarrollo IBK:** desarrollo@interbanking.com.ar

---

## Alcance actual

### Implementado

- **Consulta de Saldos** (`GET /accounts/balances`)  
  Obtención de saldos diarios históricos (hasta 180 días) para todas las cuentas configuradas en la plataforma IBK. Incluye saldo contable, operativo, proyectado a 24hs y 48hs.

---

## Propuestas de implementación futura

Las siguientes funcionalidades están disponibles en la API de InterBanking pero no forman parte del alcance inicial. Se documentan como referencia para futuras iteraciones.

---

### 1. Consulta de Cuentas (`GET /accounts`)

**Beneficio:**  
Obtener el listado completo y actualizado de todas las cuentas bancarias dadas de alta en la plataforma IBK, con su CBU, tipo de cuenta, moneda y banco asociado.  
Útil para mantener un catálogo local de cuentas sin carga manual, y como base para parametrizar las consultas de saldos y movimientos automáticamente.

---

### 2. Consulta de Movimientos (`GET /accounts/{account-number}/movements/{movement-type}`)

**Tipos disponibles:** `dia`, `diferidos`, `anteriores`

**Beneficio:**  
- **Del día:** visibilidad en tiempo real de los débitos y créditos del día, con detalle de CUIT del originante, descripción del movimiento e importe.
- **Diferidos:** anticipar movimientos con fechas futuras programadas (útil para proyección de cash flow).
- **Anteriores:** consultar historial de movimientos de días previos para conciliación bancaria.

---

### 3. Consulta de Extracto (`GET /accounts/{account-number}/statements`)

**Beneficio:**  
Equivalente digital del extracto bancario. Provee el detalle completo de movimientos con saldo de apertura y cierre por día, por banco y moneda. Es la base para automatizar la conciliación bancaria sin acceder manualmente a cada home banking.

---

### 4. Consulta de Transferencias — Detalle (`GET /transfers/details`)

**Beneficio:**  
Visualizar todas las transferencias recibidas y ejecutadas (incluyendo las programadas), con estado, fecha, importe, cuenta debitada/acreditada y número de referencia. Permite auditar el flujo de transferencias entre cuentas propias y de terceros.

---

### 5. Consulta de Transferencias — Comprobantes (`GET /transfers/vouchers`)

**Beneficio:**  
Obtener los datos completos para la confección de comprobantes de transferencias ejecutadas: código de validación, número de red, concepto de tercero y descripción. Útil para automatizar la generación de comprobantes sin intervención manual.

---

## Autenticación

OAuth 2.0 — Security Flow: `client_credentials`  
Token expira en **7200 segundos (2 horas)**. El cliente debe gestionar el ciclo de vida del token (cache, verificación de vigencia, renovación).

Ver `interbanking_api.py` para la implementación del cliente.

---

## Configuración

Las credenciales y parámetros de conexión se configuran en `GestionAPI/common/credenciales.py` bajo la clave `INTERBANKING`.

La base de datos destino se configura bajo la clave `INTERBANKING_DB` en el mismo archivo.
