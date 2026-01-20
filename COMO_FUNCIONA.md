# ¿Cómo Funciona la Integración Relatic → Odoo?

## 🎯 Flujo Completo Paso a Paso

### Escenario: Un cliente compra una membresía anual

---

## 📍 PASO 1: Cliente Paga en membresia-relatic

**En el sistema de membresía:**
- Cliente: Juan Pérez
- Email: juan@email.com
- Compra: Membresía Anual ($120.00)
- Método de pago: YAPPY
- Pago confirmado ✅

**Sistema genera evento:**
```json
{
  "event": "ORDER_PAID",
  "order_id": "ORD-2026-00021",
  "timestamp": "2026-01-20T10:30:00Z"
}
```

---

## 📍 PASO 2: membresia-relatic Envía Webhook a Odoo

**El sistema de membresía:**
1. Formatea el payload según contrato JSON v1.0
2. Genera firma HMAC del payload
3. Envía POST a Odoo

**Request HTTP:**
```
POST https://odoo.relatic.org/api/relatic/v1/sale
Headers:
  Authorization: Bearer RELATIC_API_KEY
  X-Relatic-Signature: abc123... (firma HMAC)
  Content-Type: application/json

Body:
{
  "meta": {
    "version": "1.0",
    "source": "membresia-relatic",
    "environment": "prod",
    "timestamp": "2026-01-20T10:30:00Z"
  },
  "order_id": "ORD-2026-00021",
  "member": {
    "email": "juan@email.com",
    "name": "Juan Pérez",
    "vat": "8-123-456",
    "phone": "+507-6123-4567"
  },
  "items": [
    {
      "sku": "MEMB-ANUAL",
      "name": "Membresía Anual",
      "qty": 1,
      "price": 120.00,
      "tax_rate": 7.0
    }
  ],
  "payment": {
    "method": "YAPPY",
    "amount": 128.40,
    "reference": "YAPPY-EBOWR-38807178",
    "date": "2026-01-20",
    "currency": "PAB"
  }
}
```

---

## 📍 PASO 3: Odoo Recibe el Webhook

**Controller REST (`api_controller.py`):**

### 3.1 Validar Autenticación
```python
# Verificar API Key
if api_key != config_api_key:
    return error 401 "INVALID_API_KEY"

# Verificar firma HMAC
if signature != expected_signature:
    return error 401 "INVALID_SIGNATURE"
```
✅ **Si pasa:** Continúa  
❌ **Si falla:** Retorna error 401

### 3.2 Validar Payload
```python
# Verificar campos requeridos
if 'order_id' not in payload:
    return error 400 "INVALID_PAYLOAD"

# Verificar formato de email
if not valid_email(payload['member']['email']):
    return error 400 "INVALID_EMAIL"

# Verificar que montos coincidan
if payment_amount != total_items:
    return error 400 "AMOUNT_MISMATCH"
```
✅ **Si pasa:** Continúa  
❌ **Si falla:** Retorna error 400

### 3.3 Crear Log Inicial
```python
log = relatic.sync.log.create({
    'order_id': 'ORD-2026-00021',
    'status': 'pending',
    'payload_hash': 'abc123...'  # Hash SHA256 del payload
})
```
📝 **Registro creado:** Log en estado "pending"

### 3.4 Verificar Idempotencia
```python
# Buscar factura existente
existing_invoice = account.move.search([
    ('x_relatic_order_id', '=', 'ORD-2026-00021')
])

if existing_invoice:
    log.mark_success()
    return success 200 "Factura ya existe"
```
✅ **Si existe:** Retorna factura existente  
🔄 **Si no existe:** Continúa

### 3.5 Lock Transaccional
```python
# Bloquear para evitar duplicados simultáneos
with savepoint():
    execute("SELECT id FROM account_move WHERE x_relatic_order_id=%s FOR UPDATE")
    # ... crear factura ...
```
🔒 **Previene:** Duplicados si llegan 2 requests al mismo tiempo

---

## 📍 PASO 4: Crear/Actualizar Contacto

**Partner Service (`partner_service.py`):**

```python
# Buscar por email
partner = res.partner.search([
    ('email', '=', 'juan@email.com')
])

if partner:
    # Actualizar existente
    partner.write({
        'name': 'Juan Pérez',
        'phone': '+507-6123-4567',
        'vat': '8-123-456'
    })
else:
    # Crear nuevo
    partner = res.partner.create({
        'name': 'Juan Pérez',
        'email': 'juan@email.com',
        'is_company': False,
        'customer_rank': 1,
        'category_id': [etiqueta 'RELATIC_MIEMBRO']
    })
```

**Resultado:**
- ✅ Contacto creado/actualizado
- ✅ Etiqueta "RELATIC_MIEMBRO" asignada
- ✅ Marcado como cliente (`customer_rank = 1`)

---

## 📍 PASO 5: Crear Factura

**Invoice Service (`invoice_service.py`):**

### 5.1 Buscar/Crear Productos
```python
for item in items:
    product = product.product.search([
        ('default_code', '=', 'MEMB-ANUAL')
    ])
    
    if not product:
        # Auto-crear si está habilitado
        product = product.product.create({
            'name': 'Membresía Anual',
            'default_code': 'MEMB-ANUAL',
            'type': 'service',
            'x_relatic_auto': True
        })
```

### 5.2 Crear Líneas de Factura
```python
invoice_lines = []
for item in items:
    invoice_lines.append({
        'product_id': product.id,
        'name': 'Membresía Anual',
        'quantity': 1,
        'price_unit': 120.00,
        'tax_ids': [impuesto ITBMS 7%]
    })
```

### 5.3 Crear Factura
```python
invoice = account.move.create({
    'move_type': 'out_invoice',  # Factura de cliente
    'partner_id': partner.id,
    'invoice_origin': 'ORD-2026-00021',
    'ref': 'YAPPY-EBOWR-38807178',
    'invoice_date': '2026-01-20',
    'invoice_line_ids': invoice_lines,
    'x_relatic_order_id': 'ORD-2026-00021'  # Para idempotencia
})

# Confirmar factura
invoice.action_post()
```

**Resultado:**
- ✅ Factura creada: `FACT/2026/0001`
- ✅ Líneas con productos e impuestos
- ✅ Estado: "Publicada" (`posted`)
- ✅ Campo `x_relatic_order_id` guardado

---

## 📍 PASO 6: Registrar Pago

**Payment Service (`payment_service.py`):**

### 6.1 Obtener Diario
```python
journal = account.journal.search([
    ('name', '=', 'YAPPY'),
    ('type', '=', 'bank')
])
```

### 6.2 Crear Movimiento Contable de Pago
```python
# IMPORTANTE: En Odoo 18, los pagos son account.move (no account.payment)
payment_move = account.move.create({
    'move_type': 'entry',  # Movimiento contable
    'date': '2026-01-20',
    'journal_id': journal.id,
    'ref': 'YAPPY-EBOWR-38807178',
    'line_ids': [
        # Línea banco (débito)
        {
            'account_id': journal.default_account_id.id,
            'debit': 128.40,
            'credit': 0.0,
            'partner_id': partner.id
        },
        # Línea cliente (crédito)
        {
            'account_id': partner.property_account_receivable_id.id,
            'debit': 0.0,
            'credit': 128.40,
            'partner_id': partner.id
        }
    ]
})

payment_move.action_post()  # Confirmar movimiento
```

**Resultado:**
- ✅ Movimiento contable creado
- ✅ Asiento contable generado
- ✅ Estado: "Publicado"

### 6.3 Conciliar Factura con Pago
```python
# Obtener líneas conciliables
invoice_lines = invoice.line_ids.filtered(
    lambda l: l.account_id.reconcile
)
payment_lines = payment_move.line_ids.filtered(
    lambda l: l.account_id.reconcile
)

# Conciliar automáticamente
(invoice_lines + payment_lines).reconcile()
```

**Resultado:**
- ✅ Factura conciliada con pago
- ✅ Estado de factura: "Pagada" (`paid`)
- ✅ Monto pendiente: $0.00

---

## 📍 PASO 7: Marcar Log como Exitoso

```python
log.mark_success(
    partner_id=partner.id,
    invoice_id=invoice.id,
    payment_move_id=payment_move.id,
    processing_time=1.5  # segundos
)
```

**Resultado:**
- ✅ Log actualizado: estado "success"
- ✅ Relaciones guardadas (partner, invoice, payment)
- ✅ Tiempo de procesamiento registrado

---

## 📍 PASO 8: Retornar Respuesta

**Response HTTP 200 OK:**
```json
{
  "status": "success",
  "data": {
    "order_id": "ORD-2026-00021",
    "partner_id": 123,
    "invoice_id": 456,
    "invoice_number": "FACT/2026/0001",
    "payment_move_id": 789,
    "sync_log_id": 101
  },
  "message": "Factura creada exitosamente"
}
```

---

## 🔄 Flujo Visual Completo

```
┌─────────────────────────────────┐
│   membresia-relatic (srv A)     │
│                                  │
│  1. Cliente paga membresía       │
│  2. Pago confirmado ✅           │
│  3. Genera evento ORDER_PAID    │
│  4. Formatea payload JSON        │
│  5. Genera firma HMAC            │
│  6. POST → Odoo                  │
└──────────────┬──────────────────┘
               │ HTTPS POST
               │ Authorization: Bearer API_KEY
               │ X-Relatic-Signature: HMAC
               │
               ▼
┌─────────────────────────────────┐
│      Odoo 18 (srv B)            │
│                                  │
│  ┌──────────────────────────┐   │
│  │ Controller REST          │   │
│  │ /api/relatic/v1/sale     │   │
│  │                          │   │
│  │ 1. Validar API Key      │   │
│  │ 2. Validar HMAC          │   │
│  │ 3. Validar payload       │   │
│  │ 4. Crear log inicial     │   │
│  │ 5. Verificar idempotencia│   │
│  │ 6. Lock transaccional    │   │
│  └──────────┬───────────────┘   │
│             │                    │
│  ┌──────────▼───────────────┐   │
│  │ Partner Service          │   │
│  │ - Buscar por email        │   │
│  │ - Crear/actualizar        │   │
│  │ - Etiqueta RELATIC_MIEMBRO│   │
│  └──────────┬───────────────┘   │
│             │                    │
│  ┌──────────▼───────────────┐   │
│  │ Invoice Service           │   │
│  │ - Buscar productos        │   │
│  │ - Crear líneas            │   │
│  │ - Crear factura           │   │
│  │ - Confirmar (action_post) │   │
│  └──────────┬───────────────┘   │
│             │                    │
│  ┌──────────▼───────────────┐   │
│  │ Payment Service           │   │
│  │ - Obtener diario          │   │
│  │ - Crear account.move       │   │
│  │ - Confirmar movimiento    │   │
│  │ - Conciliar factura       │   │
│  └──────────┬───────────────┘   │
│             │                    │
│  ┌──────────▼───────────────┐   │
│  │ Actualizar Log            │   │
│  │ - status: success         │   │
│  │ - Guardar relaciones     │   │
│  └───────────────────────────┘   │
│                                  │
│  ┌──────────────────────────┐   │
│  │ Retornar Response 200 OK │   │
│  └──────────────────────────┘   │
└──────────────────────────────────┘
```

---

## 🛡️ Seguridad en Cada Paso

1. **API Key**: Solo requests con key válida
2. **HMAC**: Firma del payload (previene manipulación)
3. **Validación**: Payload validado antes de procesar
4. **Idempotencia**: Mismo order_id = misma factura
5. **Lock**: Previene duplicados simultáneos
6. **Logs**: Todo queda registrado para auditoría

---

## 📊 Qué se Crea en Odoo

### 1. Contacto (`res.partner`)
- Nombre: Juan Pérez
- Email: juan@email.com
- Teléfono: +507-6123-4567
- VAT: 8-123-456
- Etiqueta: RELATIC_MIEMBRO
- Tipo: Cliente

### 2. Factura (`account.move`)
- Tipo: Factura de cliente (`out_invoice`)
- Número: FACT/2026/0001
- Cliente: Juan Pérez
- Líneas: Membresía Anual ($120.00 + ITBMS)
- Total: $128.40
- Estado: Pagada
- Origen: ORD-2026-00021

### 3. Movimiento de Pago (`account.move`)
- Tipo: Movimiento contable (`entry`)
- Diario: YAPPY
- Líneas:
  - Banco: Débito $128.40
  - Cliente: Crédito $128.40
- Estado: Publicado
- Conciliado: Sí

### 4. Log (`relatic.sync.log`)
- Order ID: ORD-2026-00021
- Estado: success
- Payload Hash: abc123...
- Relaciones: partner_id, invoice_id, payment_move_id
- Tiempo: 1.5 segundos

---

## ⚠️ Manejo de Errores

### Si falla la autenticación:
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_API_KEY",
    "message": "API Key inválida o faltante"
  }
}
```
**Acción:** membresia-relatic puede reintentar

### Si falla la validación:
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_EMAIL",
    "message": "Formato de email inválido"
  }
}
```
**Acción:** No reintentar (error del cliente)

### Si falla el procesamiento:
```json
{
  "status": "error",
  "error": {
    "code": "ODOO_ERROR",
    "message": "Error interno del servidor"
  },
  "retry": true
}
```
**Acción:** Reintentar automáticamente (cola)

---

## 🔍 Verificar en Odoo

### 1. Ver Factura Creada:
- Contabilidad → Clientes → Facturas
- Buscar: FACT/2026/0001
- Verificar: Estado "Pagada", Origen "ORD-2026-00021"

### 2. Ver Log de Sincronización:
- Contabilidad → Relatic Integration → Logs de Sincronización
- Buscar: ORD-2026-00021
- Verificar: Estado "success", relaciones guardadas

### 3. Ver Contacto:
- Contactos → Buscar: juan@email.com
- Verificar: Etiqueta "RELATIC_MIEMBRO", Facturas relacionadas

---

## ✅ Resultado Final

**En Odoo tienes:**
- ✅ Contacto creado/actualizado
- ✅ Factura generada y confirmada
- ✅ Pago registrado y conciliado
- ✅ Factura marcada como "Pagada"
- ✅ Log completo de la operación
- ✅ Trazabilidad completa (order_id, payment reference)

**Todo automático, sin intervención manual.** 🎉

---

**¿Preguntas?** Revisa los logs de sincronización en Odoo para ver el detalle completo de cada operación.
