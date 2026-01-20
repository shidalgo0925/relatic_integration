# Scripts de Pruebas - Integración Relatic

## 📋 Descripción

Scripts de pruebas end-to-end y unitarias para validar la integración Relatic → Odoo.

## 🧪 Tipos de Pruebas

### 1. Pruebas End-to-End (`test_integration.py`)

Pruebas HTTP que validan el flujo completo desde el webhook hasta la creación de facturas.

**Ejecutar:**
```bash
cd /home/ubuntu/relatic_integration_dev
python3 tests/test_integration.py
```

**Requisitos:**
- Python 3.6+
- Librería `requests`: `pip install requests`
- Configurar `ODOO_URL`, `API_KEY`, `HMAC_SECRET` en el script

**Casos de prueba:**
1. ✅ Payload válido
2. ✅ Idempotencia (mismo order_id dos veces)
3. ✅ API Key inválida
4. ✅ Firma HMAC inválida
5. ✅ Campo requerido faltante
6. ✅ Email inválido
7. ✅ Monto no coincide
8. ✅ Cantidad inválida
9. ✅ Fecha inválida
10. ✅ Fecha futura
11. ✅ Items vacío
12. ✅ Múltiples items

### 2. Pruebas Unitarias Odoo (`test_odoo_services.py`)

Pruebas de servicios directamente en Odoo (requiere shell de Odoo).

**Ejecutar:**
```bash
# Desde el servidor Odoo
odoo-bin shell -d relatic -c /etc/odoo/odoo.conf

# Dentro del shell
>>> exec(open('/opt/odoo/custom-addons/relatic_integration/tests/test_odoo_services.py').read())
```

**Casos de prueba:**
1. ✅ Partner Service - Crear contacto
2. ✅ Partner Service - Actualizar contacto
3. ✅ Invoice Service - Crear factura
4. ✅ Payment Service - Registrar pago
5. ✅ Sync Log - Crear y marcar éxito

## ⚙️ Configuración

### Variables en `test_integration.py`:

```python
ODOO_URL = "https://odoo.relatic.org"  # URL de Odoo
API_KEY = "TU_API_KEY_AQUI"           # API Key configurada en Odoo
HMAC_SECRET = "TU_SECRET_AQUI"         # Secret para HMAC
```

### Configuración en Odoo:

1. **API Key**: Configurar en `ir.config_parameter`:
   - Key: `relatic_integration.api_key`
   - Value: Tu API Key

2. **HMAC Secret**: Configurar en `ir.config_parameter`:
   - Key: `relatic_integration.hmac_secret`
   - Value: Tu secret (mismo que en membresia-relatic)

3. **Diarios de Pago**: Crear diarios:
   - YAPPY (tipo: banco)
   - TARJETA (tipo: banco)
   - TRANSFERENCIA (tipo: banco)

4. **Productos**: Crear productos con SKU:
   - MEMB-ANUAL
   - MEMB-MENSUAL (opcional)

## 📊 Resultados Esperados

### Pruebas End-to-End:
- ✅ 12 tests pasados
- ✅ 0 tests fallidos

### Pruebas Unitarias:
- ✅ 5 tests pasados
- ✅ 0 tests fallidos

## 🔍 Debugging

Si un test falla:

1. **Revisar logs de Odoo:**
   ```bash
   tail -f /var/log/odoo/odoo.log
   ```

2. **Revisar logs de sincronización:**
   - Ir a: Contabilidad → Relatic Integration → Logs de Sincronización
   - Buscar por `order_id` del test fallido

3. **Verificar configuración:**
   - API Key correcta
   - HMAC Secret correcto
   - Diarios configurados
   - Productos existentes

## 📝 Notas

- Los tests crean datos de prueba (contactos, facturas, etc.)
- Los `order_id` de prueba usan formato: `ORD-2026-TEST###`
- Los emails de prueba usan formato: `test###@relatic.test`
- Limpiar datos de prueba después de ejecutar tests si es necesario

## 🚀 Ejecución en CI/CD

Para integración continua, ejecutar:

```bash
# Instalar dependencias
pip install requests

# Ejecutar tests
python3 tests/test_integration.py

# Verificar código de salida
if [ $? -eq 0 ]; then
    echo "Tests pasados"
else
    echo "Tests fallidos"
    exit 1
fi
```

---

**Fecha:** 2026-01-20  
**Versión:** 1.0
