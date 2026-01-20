# Pasos a Ejecutar en el Servidor de Odoo

## 🖥️ Instrucciones para Ejecutar en el Servidor de Odoo

---

## 📋 PASO 1: Copiar Módulo al Servidor de Odoo

**Desde el servidor de Odoo, ejecutar:**

```bash
# Copiar módulo desde ubicación actual a custom-addons
sudo cp -r /home/ubuntu/relatic_integration_dev /opt/odoo/custom-addons/relatic_integration

# Ajustar permisos
sudo chown -R odoo:odoo /opt/odoo/custom-addons/relatic_integration

# Verificar que se copió correctamente
ls -la /opt/odoo/custom-addons/relatic_integration/
```

**Verificar que veas:**
- `__init__.py`
- `__manifest__.py`
- `controllers/`
- `models/`
- `services/`
- etc.

---

## 🔧 PASO 2: Verificar Configuración de Odoo

```bash
# Verificar que custom-addons esté en addons_path
grep addons_path /etc/odoo/odoo.conf
```

**Debe incluir:** `/opt/odoo/custom-addons`

**Si NO está, agregarlo:**
```bash
sudo nano /etc/odoo/odoo.conf
```

**Buscar línea:**
```ini
addons_path = /opt/odoo/odoo/addons,/opt/odoo/addons
```

**Cambiar a:**
```ini
addons_path = /opt/odoo/odoo/addons,/opt/odoo/addons,/opt/odoo/custom-addons
```

**Guardar:** `Ctrl+O`, `Enter`, `Ctrl+X`

---

## 🔄 PASO 3: Reiniciar Odoo

```bash
# Reiniciar servicio
sudo systemctl restart odoo

# Esperar 5 segundos
sleep 5

# Verificar que esté corriendo
sudo systemctl status odoo
```

**Debe mostrar:** `active (running)` ✅

**Si hay errores, ver logs:**
```bash
sudo tail -50 /var/log/odoo/odoo.log
```

---

## 📦 PASO 4: Instalar Módulo desde Interfaz Web

**Desde el navegador, acceder a Odoo:**

1. **Ir a:** `https://odoo.relatic.org` (o tu URL de Odoo)

2. **Iniciar sesión** como administrador

3. **Ir a Aplicaciones:**
   - Menú: **Aplicaciones → Aplicaciones**

4. **Activar modo desarrollador** (si no está activo):
   - Click en **"Activar modo desarrollador"** (esquina superior derecha)

5. **Actualizar lista:**
   - Click en **"Actualizar lista de aplicaciones"**
   - Esperar a que termine

6. **Buscar módulo:**
   - En el buscador, escribir: **"Relatic Integration"**
   - O filtrar por categoría: **"Accounting"**

7. **Instalar:**
   - Click en **"Relatic Integration"**
   - Click en botón **"Instalar"**

8. **Verificar instalación:**
   - Debe aparecer: **"El módulo se instaló correctamente"**
   - Debe aparecer nuevo menú: **Contabilidad → Relatic Integration**

---

## ⚙️ PASO 5: Configurar Parámetros desde Odoo Web

### 5.1 Configurar API Key

1. **Ir a:** Configuración → Técnico → Parámetros → Parámetros del Sistema

2. **Buscar:** `relatic_integration.api_key`

3. **Si existe:** Click en el registro y editar el valor

4. **Si NO existe:** Click en **"Crear"**
   - **Clave:** `relatic_integration.api_key`
   - **Valor:** `TU_API_KEY_AQUI` (ejemplo: `RELATIC_API_KEY_2026_SECRET123`)
   - **Guardar**

### 5.2 Configurar HMAC Secret

1. **En el mismo lugar** (Parámetros del Sistema)

2. **Buscar:** `relatic_integration.hmac_secret`

3. **Crear o editar:**
   - **Clave:** `relatic_integration.hmac_secret`
   - **Valor:** `TU_SECRET_AQUI` (ejemplo: `my_secret_key_for_hmac_2026`)
   - **Guardar**

**⚠️ IMPORTANTE:** Este mismo secret debe estar en membresia-relatic

### 5.3 Configurar Auto-creación de Productos (Opcional)

1. **Parámetro:**
   - **Clave:** `relatic_integration.auto_create_product`
   - **Valor:** `True` o `False`
   - **Default:** `False` (recomendado)

---

## 💰 PASO 6: Crear Diarios desde Odoo Web

### 6.1 Crear Diario YAPPY

1. **Ir a:** Contabilidad → Configuración → Diarios

2. **Click en "Crear"**

3. **Completar:**
   - **Nombre:** `YAPPY` ⚠️ **EXACTO**
   - **Tipo:** `Banco`
   - **Cuenta por defecto:** Seleccionar cuenta bancaria
   - **Código:** `YAPPY` (opcional)

4. **Guardar**

### 6.2 Crear Diario TARJETA

**Mismo proceso:**
- **Nombre:** `TARJETA` ⚠️ **EXACTO**
- **Tipo:** `Banco`

### 6.3 Crear Diario TRANSFERENCIA

**Mismo proceso:**
- **Nombre:** `TRANSFERENCIA` ⚠️ **EXACTO**
- **Tipo:** `Banco`

---

## 📦 PASO 7: Crear Productos desde Odoo Web

### 7.1 Crear Producto MEMB-ANUAL

1. **Ir a:** Inventario → Productos → Productos

2. **Click en "Crear"**

3. **Pestaña General:**
   - **Nombre:** `Membresía Anual`
   - **Referencia interna:** `MEMB-ANUAL` ⚠️ **EXACTO**
   - **Tipo:** `Servicio`
   - **Vendible:** ✅ Marcado
   - **Comprable:** ❌ Desmarcado

4. **Pestaña Contabilidad:**
   - **Cuenta de ingresos:** Seleccionar cuenta (ej: "Ingresos por Servicios")
   - **Impuestos en ventas:** Seleccionar ITBMS 7% (si aplica)

5. **Guardar**

### 7.2 Crear Otros Productos (si aplica)

- `MEMB-MENSUAL` - Membresía Mensual
- `MEMB-SEMESTRAL` - Membresía Semestral
- etc.

---

## 🧪 PASO 8: Probar desde el Servidor

### 8.1 Verificar que el Endpoint Responda

```bash
# Probar endpoint (debe dar error 401 sin autenticación)
curl -X POST https://odoo.relatic.org/api/relatic/v1/sale \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' \
  -v
```

**Respuesta esperada:** `401 Unauthorized` ✅

### 8.2 Verificar Logs de Odoo

```bash
# Ver logs en tiempo real
sudo tail -f /var/log/odoo/odoo.log | grep relatic
```

---

## 📊 PASO 9: Verificar desde Odoo Web

### 9.1 Ver Menú de Relatic Integration

**Debe aparecer:**
- Contabilidad → Relatic Integration → Logs de Sincronización

### 9.2 Probar con Webhook de Prueba

**Desde membresia-relatic, enviar webhook de prueba**

**Luego verificar en Odoo:**

1. **Logs de Sincronización:**
   - Contabilidad → Relatic Integration → Logs de Sincronización
   - Buscar el order_id de prueba
   - Ver estado: "success" o "error"

2. **Facturas:**
   - Contabilidad → Clientes → Facturas
   - Buscar por "Origen" = order_id de prueba
   - Verificar que esté creada y pagada

3. **Contactos:**
   - Contactos → Contactos
   - Buscar por email de prueba
   - Verificar que esté creado con etiqueta "RELATIC_MIEMBRO"

---

## ✅ Checklist Final

**Desde el servidor de Odoo:**

- [ ] Módulo copiado a `/opt/odoo/custom-addons/relatic_integration`
- [ ] Permisos correctos (`odoo:odoo`)
- [ ] `addons_path` incluye `/opt/odoo/custom-addons`
- [ ] Odoo reiniciado y corriendo
- [ ] Módulo instalado desde interfaz web
- [ ] API Key configurada en parámetros
- [ ] HMAC Secret configurado en parámetros
- [ ] Diario YAPPY creado
- [ ] Diario TARJETA creado
- [ ] Diario TRANSFERENCIA creado
- [ ] Producto MEMB-ANUAL creado
- [ ] Endpoint responde (error 401 sin auth)
- [ ] Webhook de prueba funciona

---

## 🔍 Comandos Útiles para Debugging

```bash
# Ver si el módulo está en la ruta correcta
ls -la /opt/odoo/custom-addons/relatic_integration/

# Ver logs de Odoo
sudo tail -f /var/log/odoo/odoo.log

# Ver estado de Odoo
sudo systemctl status odoo

# Reiniciar Odoo
sudo systemctl restart odoo

# Ver configuración de Odoo
cat /etc/odoo/odoo.conf | grep addons_path

# Ver permisos del módulo
ls -la /opt/odoo/custom-addons/relatic_integration/
```

---

## 📝 Notas Importantes

1. **Nombres exactos:** Los diarios y productos deben tener los nombres EXACTOS:
   - Diarios: `YAPPY`, `TARJETA`, `TRANSFERENCIA`
   - Productos: `MEMB-ANUAL`, etc.

2. **API Key y Secret:** Deben ser los mismos en Odoo y en membresia-relatic

3. **Permisos:** El módulo debe pertenecer a `odoo:odoo`

4. **Reiniciar:** Después de copiar el módulo, siempre reiniciar Odoo

5. **Logs:** Revisar logs si algo no funciona

---

**¡Listo!** Con estos pasos ejecutados en el servidor de Odoo, la integración estará funcionando. 🚀
