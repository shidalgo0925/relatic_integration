# Guía de Instalación y Configuración desde Odoo

## 📋 ¿Qué hacer desde Odoo?

Esta guía te explica paso a paso cómo instalar, configurar y usar el módulo de integración Relatic en Odoo 18.

---

## 🚀 PASO 1: Copiar el Módulo

### Opción A: Desde el servidor (recomendado)

```bash
# 1. Copiar módulo a custom-addons
sudo cp -r /home/ubuntu/relatic_integration_dev /opt/odoo/custom-addons/relatic_integration

# 2. Asegurar permisos
sudo chown -R odoo:odoo /opt/odoo/custom-addons/relatic_integration

# 3. Verificar que esté en la ruta correcta
ls -la /opt/odoo/custom-addons/relatic_integration/
```

### Opción B: Desde Git (si tienes repositorio)

```bash
cd /opt/odoo/custom-addons/
git clone [URL_DEL_REPOSITORIO] relatic_integration
sudo chown -R odoo:odoo relatic_integration
```

---

## 🔧 PASO 2: Verificar Configuración de Odoo

### Verificar que custom-addons esté en la configuración

```bash
# Editar configuración de Odoo
sudo nano /etc/odoo/odoo.conf
```

**Verificar que tenga:**
```ini
[options]
addons_path = /opt/odoo/odoo/addons,/opt/odoo/addons,/opt/odoo/custom-addons
```

**Si falta `/opt/odoo/custom-addons`, agregarlo.**

---

## 🔄 PASO 3: Reiniciar Odoo

```bash
# Reiniciar servicio
sudo systemctl restart odoo

# Verificar que inició correctamente
sudo systemctl status odoo

# Ver logs si hay problemas
sudo tail -f /var/log/odoo/odoo.log
```

---

## 📦 PASO 4: Instalar el Módulo en Odoo

### Desde la interfaz web:

1. **Ir a Aplicaciones**
   - Menú: Aplicaciones → Aplicaciones

2. **Activar modo desarrollador** (si no está activo)
   - Click en "Activar modo desarrollador" (esquina superior derecha)

3. **Actualizar lista de aplicaciones**
   - Click en "Actualizar lista de aplicaciones"

4. **Buscar el módulo**
   - Buscar: "Relatic Integration"
   - O filtrar por: "Relatic"

5. **Instalar el módulo**
   - Click en "Relatic Integration"
   - Click en botón "Instalar"

### Verificar instalación:

- Deberías ver: "El módulo se instaló correctamente"
- Menú nuevo: **Contabilidad → Relatic Integration → Logs de Sincronización**

---

## ⚙️ PASO 5: Configurar Parámetros del Sistema

### 5.1 Configurar API Key

1. **Ir a Configuración Técnica**
   - Menú: Configuración → Técnico → Parámetros → Parámetros del Sistema

2. **Buscar o crear parámetro:**
   - **Clave:** `relatic_integration.api_key`
   - **Valor:** Tu API Key (ejemplo: `RELATIC_API_KEY_2026_SECRET`)

3. **Guardar**

### 5.2 Configurar HMAC Secret

1. **En el mismo lugar (Parámetros del Sistema)**

2. **Buscar o crear parámetro:**
   - **Clave:** `relatic_integration.hmac_secret`
   - **Valor:** Tu secret compartido (ejemplo: `my_secret_key_for_hmac_2026`)

3. **Guardar**

**⚠️ IMPORTANTE:** Este mismo secret debe estar configurado en membresia-relatic

### 5.3 Configurar Auto-creación de Productos (Opcional)

1. **Parámetro:**
   - **Clave:** `relatic_integration.auto_create_product`
   - **Valor:** `True` o `False`
   - **Default:** `False`

**Si es `True:** Los productos se crearán automáticamente si no existen  
**Si es `False:** Debe existir el producto antes de crear factura

---

## 💰 PASO 6: Crear Diarios de Pago

### 6.1 Crear Diario YAPPY

1. **Ir a Contabilidad**
   - Menú: Contabilidad → Configuración → Diarios

2. **Crear nuevo diario**
   - Click en "Crear"
   - **Nombre:** `YAPPY`
   - **Tipo:** `Banco`
   - **Cuenta por defecto:** Seleccionar cuenta bancaria (ej: "Banco YAPPY")
   - **Código:** `YAPPY` (opcional)

3. **Guardar**

### 6.2 Crear Diario TARJETA

1. **Mismo proceso**
   - **Nombre:** `TARJETA`
   - **Tipo:** `Banco`
   - **Cuenta por defecto:** Seleccionar cuenta bancaria

### 6.3 Crear Diario TRANSFERENCIA

1. **Mismo proceso**
   - **Nombre:** `TRANSFERENCIA`
   - **Tipo:** `Banco`
   - **Cuenta por defecto:** Seleccionar cuenta bancaria

**⚠️ IMPORTANTE:** Los nombres deben ser exactamente:
- `YAPPY`
- `TARJETA`
- `TRANSFERENCIA`

---

## 📦 PASO 7: Crear Productos

### 7.1 Crear Producto Membresía Anual

1. **Ir a Productos**
   - Menú: Inventario → Productos → Productos

2. **Crear nuevo producto**
   - Click en "Crear"
   - **Nombre:** `Membresía Anual`
   - **Referencia interna:** `MEMB-ANUAL` ⚠️ **DEBE SER EXACTO**
   - **Tipo:** `Servicio`
   - **Vendible:** ✅ Marcado
   - **Comprable:** ❌ Desmarcado

3. **Pestaña Contabilidad**
   - **Cuenta de ingresos:** Seleccionar cuenta de ingreso (ej: "Ingresos por Servicios")
   - **Impuestos en ventas:** Seleccionar ITBMS 7% (si aplica)

4. **Guardar**

### 7.2 Crear Otros Productos (Opcional)

- `MEMB-MENSUAL` - Membresía Mensual
- `MEMB-SEMESTRAL` - Membresía Semestral
- etc.

**⚠️ IMPORTANTE:** La referencia interna (SKU) debe coincidir exactamente con lo que envía membresia-relatic

---

## 🧪 PASO 8: Probar la Integración

### 8.1 Verificar Endpoint

Desde el servidor:

```bash
# Probar que el endpoint responde (debe dar error 401 sin autenticación)
curl -X POST https://odoo.relatic.org/api/relatic/v1/sale \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**Respuesta esperada:** Error 401 (sin autenticación) ✅

### 8.2 Ejecutar Tests

```bash
# Instalar dependencias
pip install requests

# Ejecutar tests
cd /home/ubuntu/relatic_integration_dev
python3 tests/test_integration.py
```

### 8.3 Probar con Webhook Real

Desde membresia-relatic, enviar un webhook de prueba con:
- Order ID de prueba: `ORD-2026-TEST-001`
- Email de prueba: `test@relatic.test`

---

## 📊 PASO 9: Verificar Resultados

### 9.1 Ver Logs de Sincronización

1. **Ir a Logs**
   - Menú: Contabilidad → Relatic Integration → Logs de Sincronización

2. **Verificar:**
   - Estado: "success" (verde) o "error" (rojo)
   - Order ID recibido
   - Factura creada
   - Tiempo de procesamiento

### 9.2 Ver Facturas Creadas

1. **Ir a Facturas**
   - Menú: Contabilidad → Clientes → Facturas

2. **Buscar:**
   - Por número de factura
   - Por "Origen" = order_id recibido
   - Por contacto creado

3. **Verificar:**
   - Estado: "Pagada"
   - Líneas correctas
   - Monto correcto

### 9.3 Ver Contactos Creados

1. **Ir a Contactos**
   - Menú: Contactos → Contactos

2. **Buscar:**
   - Por email recibido
   - Por etiqueta "RELATIC_MIEMBRO"

3. **Verificar:**
   - Datos correctos
   - Etiqueta asignada
   - Facturas relacionadas

---

## 🔍 PASO 10: Monitoreo y Mantenimiento

### 10.1 Revisar Logs Regularmente

**Ubicación:** Contabilidad → Relatic Integration → Logs de Sincronización

**Filtros útiles:**
- Estado = "Error" → Ver qué falló
- Reintentos > 0 → Ver problemas temporales
- Hoy → Ver actividad reciente

### 10.2 Revisar Logs del Servidor

```bash
# Ver logs de Odoo en tiempo real
sudo tail -f /var/log/odoo/odoo.log | grep relatic
```

### 10.3 Verificar Configuración Periódicamente

**Revisar:**
- ✅ API Key activa
- ✅ HMAC Secret correcto
- ✅ Diarios configurados
- ✅ Productos existentes
- ✅ Cuentas contables configuradas

---

## ⚠️ Solución de Problemas Comunes

### Problema: Módulo no aparece en Aplicaciones

**Solución:**
```bash
# Verificar permisos
sudo chown -R odoo:odoo /opt/odoo/custom-addons/relatic_integration

# Verificar que esté en addons_path
grep addons_path /etc/odoo/odoo.conf

# Reiniciar Odoo
sudo systemctl restart odoo

# Actualizar lista de aplicaciones en Odoo
```

### Problema: Error 401 - Invalid API Key

**Solución:**
1. Verificar parámetro `relatic_integration.api_key` en Odoo
2. Verificar que membresia-relatic esté usando la misma API Key
3. Verificar que no haya espacios extra

### Problema: Error 401 - Invalid Signature

**Solución:**
1. Verificar parámetro `relatic_integration.hmac_secret` en Odoo
2. Verificar que membresia-relatic esté usando el mismo secret
3. Verificar que el payload se esté firmando correctamente

### Problema: Error 422 - Product Not Found

**Solución:**
1. Verificar que el producto exista con el SKU exacto
2. O activar `relatic_integration.auto_create_product = True`
3. Verificar que el producto tenga cuenta de ingreso configurada

### Problema: Error 422 - Journal Not Found

**Solución:**
1. Verificar que existan los diarios:
   - YAPPY
   - TARJETA
   - TRANSFERENCIA
2. Verificar que sean tipo "Banco"
3. Verificar que tengan cuenta por defecto configurada

### Problema: Factura no se marca como Pagada

**Solución:**
1. Verificar que el contacto tenga cuenta por cobrar configurada
2. Verificar que las cuentas sean conciliables
3. Revisar logs de sincronización para ver el error específico

---

## 📝 Checklist de Instalación

Usa este checklist para asegurarte de que todo esté configurado:

- [ ] Módulo copiado a `/opt/odoo/custom-addons/relatic_integration`
- [ ] Permisos correctos (odoo:odoo)
- [ ] Odoo reiniciado
- [ ] Módulo instalado en Odoo
- [ ] API Key configurada (`relatic_integration.api_key`)
- [ ] HMAC Secret configurado (`relatic_integration.hmac_secret`)
- [ ] Diario YAPPY creado
- [ ] Diario TARJETA creado
- [ ] Diario TRANSFERENCIA creado
- [ ] Producto MEMB-ANUAL creado (o auto-creación activada)
- [ ] Cuentas contables configuradas
- [ ] Tests ejecutados y pasados
- [ ] Webhook de prueba enviado
- [ ] Factura creada correctamente
- [ ] Logs de sincronización funcionando

---

## 🎯 Configuración en membresia-relatic

Una vez que Odoo esté configurado, necesitas configurar en membresia-relatic:

1. **Endpoint:** `https://odoo.relatic.org/api/relatic/v1/sale`
2. **API Key:** La misma que configuraste en Odoo
3. **HMAC Secret:** El mismo que configuraste en Odoo
4. **Headers:**
   - `Authorization: Bearer {API_KEY}`
   - `X-Relatic-Signature: {HMAC_SIGNATURE}`
   - `Content-Type: application/json`

---

## 📞 Soporte

Si tienes problemas:

1. **Revisar logs de sincronización** en Odoo
2. **Revisar logs del servidor:** `/var/log/odoo/odoo.log`
3. **Ejecutar tests:** `python3 tests/test_integration.py`
4. **Verificar configuración:** Revisar todos los parámetros

---

**¡Listo!** Con estos pasos, la integración debería estar funcionando completamente. 🎉
