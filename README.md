# Módulo Relatic Integration - Odoo 18

## 📋 Descripción

Módulo de integración entre el sistema de membresía Relatic (membresia-relatic) y Odoo Community 18.

## 🏗️ Estructura del Módulo

```
relatic_integration_dev/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── api_controller.py          # (Fase 3)
├── models/
│   ├── __init__.py
│   ├── relatic_sync_log.py         # ✅ Modelo de logs (Fase 2)
│   └── account_move.py             # ✅ Extensión para x_relatic_order_id
├── services/
│   ├── __init__.py
│   ├── partner_service.py          # (Fase 4)
│   ├── invoice_service.py          # (Fase 4)
│   └── payment_service.py          # (Fase 4)
├── views/
│   └── relatic_sync_log_views.xml  # ✅ Vistas del modelo de logs
├── security/
│   └── ir.model.access.csv         # ✅ Permisos
└── data/
    └── ir_config_parameter_data.xml # ✅ Configuración inicial
```

## ✅ Fase 2 Completada: Modelo de Logs

### Modelo: `relatic.sync.log`

**Campos principales:**
- `order_id`: ID de la orden (único, indexado)
- `payload_hash`: Hash SHA256 del payload (auditoría)
- `status`: Estado (pending, success, error, retry)
- `retries`: Número de reintentos
- `error_code` / `error_message`: Información de errores
- `partner_id`: Contacto creado/actualizado
- `invoice_id`: Factura creada
- `payment_move_id`: Movimiento de pago
- Metadata: `payload_version`, `source`, `environment`, `processing_time`

**Métodos helper:**
- `create_log()`: Crear log con hash automático
- `mark_success()`: Marcar como exitoso
- `mark_error()`: Marcar como error
- `increment_retry()`: Incrementar reintentos

### Extensión: `account.move`

**Campo agregado:**
- `x_relatic_order_id`: ID de orden Relatic (único, constraint)
- Método: `search_by_relatic_order_id()`: Buscar por Order ID

### Vistas

- **Tree View**: Lista con colores por estado
- **Form View**: Vista detallada con pestañas
- **Search View**: Filtros y agrupaciones
- **Menu**: Contabilidad → Relatic Integration → Logs de Sincronización

### Permisos

- **Usuario**: Solo lectura
- **Contador**: Lectura/escritura/creación
- **Administrador Contable**: Todos los permisos

## 🔧 Configuración

Parámetros de configuración (ir.config_parameter):

- `relatic_integration.auto_create_product`: Auto-crear productos (default: False)
- `relatic_integration.hmac_secret`: Secret para HMAC (cambiar en producción)
- `relatic_integration.api_key`: API Key (cambiar en producción)

## 📦 Instalación

1. Copiar módulo a `/opt/odoo/custom-addons/relatic_integration`
2. Actualizar lista de aplicaciones en Odoo
3. Instalar módulo "Relatic Integration"
4. Configurar parámetros en Configuración → Técnico → Parámetros → Parámetros del Sistema

## 🚀 Próximas Fases

- **Fase 3**: Controller REST con validación HMAC
- **Fase 4**: Servicios (partner, invoice, payment)
- **Fase 5**: Scripts de pruebas end-to-end

## 📝 Notas

- El módulo está diseñado para Odoo 18 Community
- Usa `account.move` (no `account.payment`) para pagos
- Campo `move_type` (no `type`) para facturas
- Idempotencia garantizada con constraint único en `x_relatic_order_id`
