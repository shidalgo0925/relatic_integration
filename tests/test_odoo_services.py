#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas unitarias de servicios Odoo

Ejecutar desde Odoo shell:
    odoo-bin shell -d relatic -c /etc/odoo/odoo.conf
    >>> exec(open('tests/test_odoo_services.py').read())
"""

from odoo import api
from odoo.exceptions import ValidationError


class TestOdooServices:
    """Pruebas de servicios Odoo"""
    
    def __init__(self, env):
        self.env = env
        self.passed = 0
        self.failed = 0
    
    def log(self, message, status='INFO'):
        """Log de prueba"""
        prefix = '✓' if status == 'PASS' else '✗' if status == 'FAIL' else '→'
        print(f"{prefix} {message}")
    
    def test(self, name, func):
        """Ejecutar test"""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print('='*60)
        try:
            result = func()
            if result:
                self.passed += 1
                self.log(f"PASSED: {name}", 'PASS')
                return True
            else:
                self.failed += 1
                self.log(f"FAILED: {name}", 'FAIL')
                return False
        except Exception as e:
            self.failed += 1
            self.log(f"ERROR: {name} - {str(e)}", 'FAIL')
            import traceback
            traceback.print_exc()
            return False
    
    def test_partner_service_create(self):
        """Test: Crear contacto nuevo"""
        partner_service = self.env['relatic.partner.service']
        member_data = {
            'email': 'test_create@relatic.test',
            'name': 'Test Create',
            'phone': '+507-6123-4567',
            'vat': '8-123-456',
            'country_code': 'PA'
        }
        
        partner = partner_service.create_or_update_partner(member_data)
        
        if partner and partner.email == 'test_create@relatic.test':
            self.log(f"Contacto creado: {partner.name} (ID: {partner.id})")
            return True
        return False
    
    def test_partner_service_update(self):
        """Test: Actualizar contacto existente"""
        partner_service = self.env['relatic.partner.service']
        
        # Crear primero
        member_data1 = {
            'email': 'test_update@relatic.test',
            'name': 'Test Update Original',
            'phone': '+507-6123-4567',
        }
        partner = partner_service.create_or_update_partner(member_data1)
        
        # Actualizar
        member_data2 = {
            'email': 'test_update@relatic.test',
            'name': 'Test Update Modified',
            'phone': '+507-9999-9999',
        }
        partner_updated = partner_service.create_or_update_partner(member_data2)
        
        if partner_updated.id == partner.id and partner_updated.name == 'Test Update Modified':
            self.log(f"Contacto actualizado: {partner_updated.name}")
            return True
        return False
    
    def test_invoice_service_create(self):
        """Test: Crear factura"""
        # Crear contacto primero
        partner_service = self.env['relatic.partner.service']
        partner = partner_service.create_or_update_partner({
            'email': 'test_invoice@relatic.test',
            'name': 'Test Invoice',
        })
        
        # Crear producto si no existe
        product = self.env['product.product'].search([('default_code', '=', 'MEMB-ANUAL')], limit=1)
        if not product:
            product = self.env['product.product'].create({
                'name': 'Membresía Anual',
                'default_code': 'MEMB-ANUAL',
                'type': 'service',
                'sale_ok': True,
            })
        
        invoice_service = self.env['relatic.invoice.service']
        items = [{
            'sku': 'MEMB-ANUAL',
            'name': 'Membresía Anual',
            'qty': 1,
            'price': 120.00,
            'tax_rate': 7.0
        }]
        payment_data = {
            'reference': 'TEST-INV-001',
            'date': '2026-01-20',
        }
        
        invoice = invoice_service.create_invoice(
            partner=partner,
            order_id='ORD-TEST-INV-001',
            items=items,
            payment_data=payment_data
        )
        
        if invoice and invoice.move_type == 'out_invoice':
            self.log(f"Factura creada: {invoice.name}")
            return True
        return False
    
    def test_payment_service_register(self):
        """Test: Registrar pago"""
        # Crear factura primero
        partner_service = self.env['relatic.partner.service']
        partner = partner_service.create_or_update_partner({
            'email': 'test_payment@relatic.test',
            'name': 'Test Payment',
        })
        
        product = self.env['product.product'].search([('default_code', '=', 'MEMB-ANUAL')], limit=1)
        if not product:
            product = self.env['product.product'].create({
                'name': 'Membresía Anual',
                'default_code': 'MEMB-ANUAL',
                'type': 'service',
                'sale_ok': True,
            })
        
        invoice_service = self.env['relatic.invoice.service']
        invoice = invoice_service.create_invoice(
            partner=partner,
            order_id='ORD-TEST-PAY-001',
            items=[{
                'sku': 'MEMB-ANUAL',
                'name': 'Membresía Anual',
                'qty': 1,
                'price': 120.00,
            }],
            payment_data={'reference': 'TEST-PAY-001', 'date': '2026-01-20'}
        )
        
        # Buscar diario YAPPY
        journal = self.env['account.journal'].search([
            ('name', '=', 'YAPPY'),
            ('type', '=', 'bank')
        ], limit=1)
        
        if not journal:
            self.log("Diario YAPPY no encontrado. Crear diario para pruebas.")
            return False
        
        payment_service = self.env['relatic.payment.service']
        payment_data = {
            'method': 'YAPPY',
            'amount': 120.00,
            'reference': 'YAPPY-TEST-001',
            'date': '2026-01-20',
        }
        
        payment_move = payment_service.register_payment(
            invoice=invoice,
            partner=partner,
            payment_data=payment_data
        )
        
        if payment_move and payment_move.move_type == 'entry':
            self.log(f"Pago registrado: {payment_move.name}")
            # Verificar que la factura esté pagada
            if invoice.amount_residual == 0:
                self.log("Factura conciliada correctamente")
                return True
        return False
    
    def test_sync_log_create(self):
        """Test: Crear log de sincronización"""
        payload = {
            'order_id': 'ORD-TEST-LOG-001',
            'meta': {'version': '1.0', 'source': 'test'}
        }
        
        log = self.env['relatic.sync.log'].create_log(
            order_id='ORD-TEST-LOG-001',
            payload=payload,
            status='pending'
        )
        
        if log and log.order_id == 'ORD-TEST-LOG-001':
            self.log(f"Log creado: {log.order_id}")
            
            # Marcar como exitoso
            log.mark_success(processing_time=1.5)
            if log.status == 'success':
                self.log("Log marcado como exitoso")
                return True
        return False
    
    def run_all_tests(self):
        """Ejecutar todos los tests"""
        print("\n" + "="*60)
        print("PRUEBAS DE SERVICIOS ODOO")
        print("="*60)
        
        self.test("Partner Service - Crear", self.test_partner_service_create)
        self.test("Partner Service - Actualizar", self.test_partner_service_update)
        self.test("Invoice Service - Crear", self.test_invoice_service_create)
        self.test("Payment Service - Registrar", self.test_payment_service_register)
        self.test("Sync Log - Crear y marcar éxito", self.test_sync_log_create)
        
        print("\n" + "="*60)
        print("RESUMEN")
        print("="*60)
        print(f"Pasados: {self.passed}")
        print(f"Fallidos: {self.failed}")
        print("="*60)
        
        return self.failed == 0


# Ejecutar si se llama directamente desde shell de Odoo
if __name__ == '__main__':
    # Esto solo funciona dentro de Odoo shell
    print("Este script debe ejecutarse desde Odoo shell:")
    print("odoo-bin shell -d relatic -c /etc/odoo/odoo.conf")
    print(">>> exec(open('tests/test_odoo_services.py').read())")
