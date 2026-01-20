#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de pruebas end-to-end para integración Relatic → Odoo

Ejecutar desde la raíz del proyecto:
    python3 tests/test_integration.py

O desde Odoo shell:
    odoo-bin shell -d relatic -c /etc/odoo/odoo.conf
    >>> exec(open('tests/test_integration.py').read())
"""

import json
import hmac
import hashlib
import requests
from datetime import datetime, date
import sys


# Configuración
ODOO_URL = "https://odoo.relatic.org"  # Cambiar según ambiente
API_ENDPOINT = f"{ODOO_URL}/api/relatic/v1/sale"
API_KEY = "CHANGE_THIS_API_KEY_IN_PRODUCTION"  # Cambiar en producción
HMAC_SECRET = "CHANGE_THIS_SECRET_IN_PRODUCTION"  # Cambiar en producción

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class TestRelaticIntegration:
    """Clase para ejecutar pruebas de integración"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def log(self, message, color=RESET):
        """Log con color"""
        print(f"{color}{message}{RESET}")
    
    def test(self, name, func):
        """Ejecutar test individual"""
        self.log(f"\n{'='*60}", BLUE)
        self.log(f"TEST: {name}", BLUE)
        self.log('='*60, BLUE)
        try:
            result = func()
            if result:
                self.passed += 1
                self.log(f"✓ PASSED: {name}", GREEN)
                return True
            else:
                self.failed += 1
                self.log(f"✗ FAILED: {name}", RED)
                return False
        except Exception as e:
            self.failed += 1
            self.log(f"✗ ERROR: {name} - {str(e)}", RED)
            import traceback
            traceback.print_exc()
            return False
    
    def generate_hmac_signature(self, payload):
        """Generar firma HMAC del payload"""
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            HMAC_SECRET.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def create_payload(self, order_id_suffix="", amount=None, items_override=None):
        """Crear payload de prueba estándar"""
        order_id = f"ORD-2026-TEST{order_id_suffix:03d}"
        
        items = items_override or [
            {
                "sku": "MEMB-ANUAL",
                "name": "Membresía Anual",
                "qty": 1,
                "price": 120.00,
                "tax_rate": 7.0
            }
        ]
        
        # Calcular total
        total = sum(item['qty'] * item['price'] for item in items)
        if amount is None:
            amount = total
        
        payload = {
            "meta": {
                "version": "1.0",
                "source": "membresia-relatic",
                "environment": "test",
                "timestamp": datetime.now().isoformat() + "Z"
            },
            "order_id": order_id,
            "member": {
                "email": f"test{order_id_suffix}@relatic.test",
                "name": f"Test User {order_id_suffix}",
                "vat": "8-123-456",
                "phone": "+507-6123-4567",
                "street": "Calle Test 123",
                "city": "Panamá",
                "country_code": "PA"
            },
            "items": items,
            "payment": {
                "method": "YAPPY",
                "amount": amount,
                "reference": f"YAPPY-TEST-{order_id_suffix:03d}",
                "date": date.today().strftime('%Y-%m-%d'),
                "currency": "PAB"
            }
        }
        return payload
    
    def send_request(self, payload, headers_override=None):
        """Enviar request al endpoint"""
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json',
            'X-Relatic-Signature': self.generate_hmac_signature(payload)
        }
        
        if headers_override:
            headers.update(headers_override)
        
        try:
            response = requests.post(
                API_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=30
            )
            return response.status_code, response.json()
        except requests.exceptions.RequestException as e:
            return None, {'error': str(e)}
    
    # ========== CASOS DE PRUEBA ==========
    
    def test_1_valid_payload(self):
        """Test 1: Payload válido - Debe crear factura exitosamente"""
        payload = self.create_payload(order_id_suffix=1)
        status, response = self.send_request(payload)
        
        if status == 200 and response.get('status') == 'success':
            self.log(f"  Factura creada: {response['data'].get('invoice_number')}", GREEN)
            return True
        else:
            self.log(f"  Status: {status}", RED)
            self.log(f"  Response: {json.dumps(response, indent=2)}", RED)
            return False
    
    def test_2_idempotency(self):
        """Test 2: Idempotencia - Enviar mismo order_id dos veces"""
        payload = self.create_payload(order_id_suffix=2)
        
        # Primera vez
        status1, response1 = self.send_request(payload)
        if status1 != 200:
            self.log(f"  Primera request falló: {status1}", RED)
            return False
        
        # Segunda vez (debe retornar existente)
        status2, response2 = self.send_request(payload)
        if status2 == 200 and response2.get('warning') == 'INVOICE_EXISTS':
            self.log(f"  Idempotencia OK: {response2.get('message')}", GREEN)
            return True
        else:
            self.log(f"  Idempotencia falló. Status: {status2}", RED)
            return False
    
    def test_3_invalid_api_key(self):
        """Test 3: API Key inválida - Debe rechazar"""
        payload = self.create_payload(order_id_suffix=3)
        status, response = self.send_request(
            payload,
            headers_override={'Authorization': 'Bearer INVALID_KEY'}
        )
        
        if status == 401 and response.get('error', {}).get('code') == 'INVALID_API_KEY':
            self.log("  API Key inválida rechazada correctamente", GREEN)
            return True
        else:
            self.log(f"  No rechazó API Key inválida. Status: {status}", RED)
            return False
    
    def test_4_invalid_signature(self):
        """Test 4: Firma HMAC inválida - Debe rechazar"""
        payload = self.create_payload(order_id_suffix=4)
        status, response = self.send_request(
            payload,
            headers_override={'X-Relatic-Signature': 'invalid_signature'}
        )
        
        if status == 401 and response.get('error', {}).get('code') == 'INVALID_SIGNATURE':
            self.log("  Firma HMAC inválida rechazada correctamente", GREEN)
            return True
        else:
            self.log(f"  No rechazó firma inválida. Status: {status}", RED)
            return False
    
    def test_5_missing_required_field(self):
        """Test 5: Campo requerido faltante - Debe rechazar"""
        payload = self.create_payload(order_id_suffix=5)
        del payload['order_id']  # Eliminar campo requerido
        
        status, response = self.send_request(payload)
        
        if status == 400 and response.get('error', {}).get('code') == 'INVALID_PAYLOAD':
            self.log("  Campo faltante rechazado correctamente", GREEN)
            return True
        else:
            self.log(f"  No rechazó campo faltante. Status: {status}", RED)
            return False
    
    def test_6_invalid_email(self):
        """Test 6: Email inválido - Debe rechazar"""
        payload = self.create_payload(order_id_suffix=6)
        payload['member']['email'] = 'invalid-email'
        
        status, response = self.send_request(payload)
        
        if status == 400 and response.get('error', {}).get('code') == 'INVALID_EMAIL':
            self.log("  Email inválido rechazado correctamente", GREEN)
            return True
        else:
            self.log(f"  No rechazó email inválido. Status: {status}", RED)
            return False
    
    def test_7_amount_mismatch(self):
        """Test 7: Monto no coincide - Debe rechazar"""
        payload = self.create_payload(order_id_suffix=7)
        payload['payment']['amount'] = 999.99  # Monto incorrecto
        
        status, response = self.send_request(payload)
        
        if status == 400 and response.get('error', {}).get('code') == 'AMOUNT_MISMATCH':
            self.log("  Monto incorrecto rechazado correctamente", GREEN)
            return True
        else:
            self.log(f"  No rechazó monto incorrecto. Status: {status}", RED)
            return False
    
    def test_8_invalid_quantity(self):
        """Test 8: Cantidad inválida (<= 0) - Debe rechazar"""
        payload = self.create_payload(order_id_suffix=8)
        payload['items'][0]['qty'] = 0  # Cantidad inválida
        
        status, response = self.send_request(payload)
        
        if status == 400 and response.get('error', {}).get('code') == 'INVALID_QUANTITY':
            self.log("  Cantidad inválida rechazada correctamente", GREEN)
            return True
        else:
            self.log(f"  No rechazó cantidad inválida. Status: {status}", RED)
            return False
    
    def test_9_invalid_date(self):
        """Test 9: Fecha inválida - Debe rechazar"""
        payload = self.create_payload(order_id_suffix=9)
        payload['payment']['date'] = 'invalid-date'
        
        status, response = self.send_request(payload)
        
        if status == 400 and response.get('error', {}).get('code') == 'INVALID_DATE':
            self.log("  Fecha inválida rechazada correctamente", GREEN)
            return True
        else:
            self.log(f"  No rechazó fecha inválida. Status: {status}", RED)
            return False
    
    def test_10_future_date(self):
        """Test 10: Fecha futura - Debe rechazar"""
        payload = self.create_payload(order_id_suffix=10)
        from datetime import timedelta
        future_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        payload['payment']['date'] = future_date
        
        status, response = self.send_request(payload)
        
        if status == 400 and response.get('error', {}).get('code') == 'INVALID_DATE':
            self.log("  Fecha futura rechazada correctamente", GREEN)
            return True
        else:
            self.log(f"  No rechazó fecha futura. Status: {status}", RED)
            return False
    
    def test_11_empty_items(self):
        """Test 11: Items vacío - Debe rechazar"""
        payload = self.create_payload(order_id_suffix=11)
        payload['items'] = []
        
        status, response = self.send_request(payload)
        
        if status == 400 and response.get('error', {}).get('code') == 'EMPTY_ITEMS':
            self.log("  Items vacío rechazado correctamente", GREEN)
            return True
        else:
            self.log(f"  No rechazó items vacío. Status: {status}", RED)
            return False
    
    def test_12_multiple_items(self):
        """Test 12: Múltiples items - Debe procesar correctamente"""
        items = [
            {
                "sku": "MEMB-ANUAL",
                "name": "Membresía Anual",
                "qty": 1,
                "price": 120.00,
                "tax_rate": 7.0
            },
            {
                "sku": "MEMB-MENSUAL",
                "name": "Membresía Mensual",
                "qty": 2,
                "price": 15.00,
                "tax_rate": 7.0
            }
        ]
        payload = self.create_payload(order_id_suffix=12, items_override=items)
        
        status, response = self.send_request(payload)
        
        if status == 200 and response.get('status') == 'success':
            self.log(f"  Múltiples items procesados: {response['data'].get('invoice_number')}", GREEN)
            return True
        else:
            self.log(f"  Falló con múltiples items. Status: {status}", RED)
            return False
    
    def run_all_tests(self):
        """Ejecutar todos los tests"""
        self.log("\n" + "="*60, BLUE)
        self.log("INICIANDO PRUEBAS DE INTEGRACIÓN RELATIC → ODOO", BLUE)
        self.log("="*60 + "\n", BLUE)
        
        # Tests exitosos
        self.test("1. Payload válido", self.test_1_valid_payload)
        self.test("2. Idempotencia", self.test_2_idempotency)
        self.test("12. Múltiples items", self.test_12_multiple_items)
        
        # Tests de validación
        self.test("3. API Key inválida", self.test_3_invalid_api_key)
        self.test("4. Firma HMAC inválida", self.test_4_invalid_signature)
        self.test("5. Campo requerido faltante", self.test_5_missing_required_field)
        self.test("6. Email inválido", self.test_6_invalid_email)
        self.test("7. Monto no coincide", self.test_7_amount_mismatch)
        self.test("8. Cantidad inválida", self.test_8_invalid_quantity)
        self.test("9. Fecha inválida", self.test_9_invalid_date)
        self.test("10. Fecha futura", self.test_10_future_date)
        self.test("11. Items vacío", self.test_11_empty_items)
        
        # Resumen
        self.log("\n" + "="*60, BLUE)
        self.log("RESUMEN DE PRUEBAS", BLUE)
        self.log("="*60, BLUE)
        self.log(f"Total tests: {self.passed + self.failed}", BLUE)
        self.log(f"{GREEN}✓ Pasados: {self.passed}{RESET}", GREEN)
        self.log(f"{RED}✗ Fallidos: {self.failed}{RESET}", RED)
        self.log("="*60 + "\n", BLUE)
        
        return self.failed == 0


if __name__ == '__main__':
    tester = TestRelaticIntegration()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
