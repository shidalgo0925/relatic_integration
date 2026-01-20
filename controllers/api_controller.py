# -*- coding: utf-8 -*-

import json
import hmac
import hashlib
import time
from datetime import datetime
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError


class RelaticAPIController(http.Controller):
    """Controller REST para recibir webhooks de membresia-relatic"""

    @http.route('/api/relatic/v1/sale', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    def relatic_sale_webhook(self):
        """
        Endpoint para recibir webhooks de ventas desde membresia-relatic
        
        Returns:
            dict: Respuesta JSON con status y data o error
        """
        start_time = time.time()
        log_record = None
        
        try:
            # 1. Obtener payload raw para validación HMAC
            raw_body = request.httprequest.data.decode('utf-8')
            payload = json.loads(raw_body)
            
            # 2. Validar autenticación (API Key)
            api_key = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')
            if not self._validate_api_key(api_key):
                return self._error_response(
                    'INVALID_API_KEY',
                    'API Key inválida o faltante',
                    401
                )
            
            # 3. Validar firma HMAC
            signature = request.httprequest.headers.get('X-Relatic-Signature', '')
            if not self._validate_hmac_signature(raw_body, signature):
                return self._error_response(
                    'INVALID_SIGNATURE',
                    'La firma HMAC no coincide con el payload',
                    401
                )
            
            # 4. Validar estructura del payload
            validation_error = self._validate_payload(payload)
            if validation_error:
                return self._error_response(
                    validation_error['code'],
                    validation_error['message'],
                    400
                )
            
            # 5. Extraer datos del payload
            order_id = payload.get('order_id')
            meta = payload.get('meta', {})
            
            # 6. Crear log inicial
            log_record = request.env['relatic.sync.log'].sudo().create_log(
                order_id=order_id,
                payload=payload,
                status='pending',
                payload_version=meta.get('version'),
                source=meta.get('source', 'membresia-relatic'),
                environment=meta.get('environment'),
            )
            
            # 7. Verificar idempotencia (factura ya existe)
            existing_invoice = request.env['account.move'].sudo().search_by_relatic_order_id(order_id)
            if existing_invoice:
                log_record.mark_success(
                    partner_id=existing_invoice.partner_id.id,
                    invoice_id=existing_invoice.id,
                    processing_time=time.time() - start_time
                )
                return self._success_response(
                    data={
                        'order_id': order_id,
                        'partner_id': existing_invoice.partner_id.id,
                        'invoice_id': existing_invoice.id,
                        'invoice_number': existing_invoice.name,
                        'already_exists': True,
                        'sync_log_id': log_record.id,
                    },
                    message='Factura ya existe, retornando existente',
                    warning='INVOICE_EXISTS'
                )
            
            # 8. Procesar con lock transaccional (idempotencia)
            with request.env.cr.savepoint():
                # Lock transaccional para evitar duplicados simultáneos
                request.env.cr.execute(
                    "SELECT id FROM account_move WHERE x_relatic_order_id=%s FOR UPDATE",
                    (order_id,)
                )
                
                # Verificar nuevamente después del lock
                existing_invoice = request.env['account.move'].sudo().search_by_relatic_order_id(order_id)
                if existing_invoice:
                    log_record.mark_success(
                        partner_id=existing_invoice.partner_id.id,
                        invoice_id=existing_invoice.id,
                        processing_time=time.time() - start_time
                    )
                    return self._success_response(
                        data={
                            'order_id': order_id,
                            'partner_id': existing_invoice.partner_id.id,
                            'invoice_id': existing_invoice.id,
                            'invoice_number': existing_invoice.name,
                            'already_exists': True,
                            'sync_log_id': log_record.id,
                        },
                        message='Factura ya existe, retornando existente',
                        warning='INVOICE_EXISTS'
                    )
                
                # 9. Importar servicios (se crearán en Fase 4)
                # Por ahora, crear estructura básica
                partner_service = request.env['relatic.partner.service'].sudo()
                invoice_service = request.env['relatic.invoice.service'].sudo()
                payment_service = request.env['relatic.payment.service'].sudo()
                
                # 10. Crear/actualizar contacto
                member_data = payload.get('member', {})
                partner = partner_service.create_or_update_partner(member_data)
                
                # 11. Crear factura
                items = payload.get('items', [])
                payment_data = payload.get('payment', {})
                invoice = invoice_service.create_invoice(
                    partner=partner,
                    order_id=order_id,
                    items=items,
                    payment_data=payment_data
                )
                
                # 12. Registrar pago
                payment_move = payment_service.register_payment(
                    invoice=invoice,
                    partner=partner,
                    payment_data=payment_data
                )
                
                # 13. Marcar log como exitoso
                processing_time = time.time() - start_time
                log_record.mark_success(
                    partner_id=partner.id,
                    invoice_id=invoice.id,
                    payment_move_id=payment_move.id,
                    processing_time=processing_time
                )
                
                # 14. Retornar respuesta exitosa
                return self._success_response(
                    data={
                        'order_id': order_id,
                        'partner_id': partner.id,
                        'invoice_id': invoice.id,
                        'invoice_number': invoice.name,
                        'payment_move_id': payment_move.id,
                        'sync_log_id': log_record.id,
                    },
                    message='Factura creada exitosamente'
                )
                
        except json.JSONDecodeError:
            return self._error_response(
                'INVALID_PAYLOAD',
                'Payload JSON inválido',
                400
            )
        except ValidationError as e:
            error_msg = str(e)
            if log_record:
                log_record.mark_error('VALIDATION_ERROR', error_msg, retry=False)
            return self._error_response(
                'VALIDATION_ERROR',
                error_msg,
                422
            )
        except Exception as e:
            error_msg = f"Error interno: {str(e)}"
            if log_record:
                log_record.mark_error('ODOO_ERROR', error_msg, retry=True)
            # Log del error para debugging
            request.env['ir.logging'].sudo().create({
                'type': 'server',
                'name': 'relatic_integration',
                'message': f"Error en webhook Relatic: {error_msg}",
                'path': '/api/relatic/v1/sale',
                'func': 'relatic_sale_webhook',
                'line': '1',
            })
            return self._error_response(
                'ODOO_ERROR',
                'Error interno del servidor',
                500
            )

    def _validate_api_key(self, api_key):
        """
        Validar API Key
        
        :param api_key: API Key recibida
        :return: True si es válida, False si no
        """
        if not api_key:
            return False
        
        config_api_key = request.env['ir.config_parameter'].sudo().get_param(
            'relatic_integration.api_key',
            ''
        )
        
        return api_key == config_api_key

    def _validate_hmac_signature(self, raw_body, received_signature):
        """
        Validar firma HMAC del payload
        
        :param raw_body: Cuerpo raw del request
        :param received_signature: Firma recibida en header
        :return: True si es válida, False si no
        """
        if not received_signature:
            return False
        
        secret = request.env['ir.config_parameter'].sudo().get_param(
            'relatic_integration.hmac_secret',
            ''
        )
        
        if not secret:
            # Si no hay secret configurado, no validar (solo para desarrollo)
            return True
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            raw_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(received_signature, expected_signature)

    def _validate_payload(self, payload):
        """
        Validar estructura y contenido del payload según contrato JSON v1.0
        
        :param payload: Diccionario con el payload
        :return: Dict con error si hay problema, None si es válido
        """
        # Validar campos requeridos
        required_fields = ['meta', 'order_id', 'member', 'items', 'payment']
        for field in required_fields:
            if field not in payload:
                return {
                    'code': 'INVALID_PAYLOAD',
                    'message': f'Campo requerido faltante: {field}'
                }
        
        # Validar meta
        meta = payload.get('meta', {})
        if 'version' not in meta or 'source' not in meta or 'environment' not in meta:
            return {
                'code': 'INVALID_PAYLOAD',
                'message': 'Campo meta incompleto. Requiere: version, source, environment'
            }
        
        # Validar order_id
        order_id = payload.get('order_id', '')
        if not order_id or not isinstance(order_id, str):
            return {
                'code': 'INVALID_PAYLOAD',
                'message': 'order_id debe ser un string no vacío'
            }
        
        # Validar member
        member = payload.get('member', {})
        email = member.get('email', '')
        if not email or '@' not in email:
            return {
                'code': 'INVALID_EMAIL',
                'message': 'Email inválido o faltante en member'
            }
        
        name = member.get('name', '')
        if not name:
            return {
                'code': 'INVALID_PAYLOAD',
                'message': 'Campo name faltante en member'
            }
        
        # Validar items
        items = payload.get('items', [])
        if not items or not isinstance(items, list) or len(items) == 0:
            return {
                'code': 'EMPTY_ITEMS',
                'message': 'Array de items vacío o inválido'
            }
        
        total_amount = 0.0
        for item in items:
            if 'sku' not in item or 'name' not in item:
                return {
                    'code': 'INVALID_PAYLOAD',
                    'message': 'Item incompleto. Requiere: sku, name'
                }
            
            qty = item.get('qty', 0)
            if not isinstance(qty, (int, float)) or qty <= 0:
                return {
                    'code': 'INVALID_QUANTITY',
                    'message': f'Cantidad inválida en item {item.get("sku")}. Debe ser > 0'
                }
            
            price = item.get('price', 0)
            if not isinstance(price, (int, float)) or price < 0:
                return {
                    'code': 'INVALID_PRICE',
                    'message': f'Precio inválido en item {item.get("sku")}. Debe ser >= 0'
                }
            
            total_amount += qty * price
        
        # Validar payment
        payment = payload.get('payment', {})
        if 'method' not in payment or 'amount' not in payment or 'reference' not in payment or 'date' not in payment:
            return {
                'code': 'INVALID_PAYLOAD',
                'message': 'Campo payment incompleto. Requiere: method, amount, reference, date'
            }
        
        payment_amount = payment.get('amount', 0)
        if not isinstance(payment_amount, (int, float)):
            return {
                'code': 'INVALID_PAYLOAD',
                'message': 'payment.amount debe ser numérico'
            }
        
        # Validar que el monto coincida (con tolerancia de 0.01 para redondeos)
        if abs(payment_amount - total_amount) > 0.01:
            return {
                'code': 'AMOUNT_MISMATCH',
                'message': f'Monto del pago ({payment_amount}) no coincide con total de items ({total_amount})'
            }
        
        # Validar fecha
        payment_date = payment.get('date', '')
        try:
            datetime.strptime(payment_date, '%Y-%m-%d')
            # Validar que no sea futura
            payment_dt = datetime.strptime(payment_date, '%Y-%m-%d').date()
            if payment_dt > datetime.now().date():
                return {
                    'code': 'INVALID_DATE',
                    'message': 'La fecha del pago no puede ser futura'
                }
        except ValueError:
            return {
                'code': 'INVALID_DATE',
                'message': 'Formato de fecha inválido. Debe ser YYYY-MM-DD'
            }
        
        # Validar VAT si existe
        vat = member.get('vat', '')
        if vat:
            # Validación básica de formato (puede mejorarse según país)
            if not isinstance(vat, str) or len(vat) < 3:
                return {
                    'code': 'INVALID_VAT',
                    'message': 'Formato de VAT/RUC inválido'
                }
        
        return None  # Payload válido

    def _success_response(self, data, message='Operación exitosa', warning=None):
        """
        Crear respuesta de éxito
        
        :param data: Datos a retornar
        :param message: Mensaje de éxito
        :param warning: Warning opcional (ej: INVOICE_EXISTS)
        :return: Dict con respuesta
        """
        response = {
            'status': 'success',
            'data': data,
            'message': message
        }
        if warning:
            response['warning'] = warning
        return response

    def _error_response(self, error_code, error_message, http_status=400, details=None, retry=False):
        """
        Crear respuesta de error
        
        :param error_code: Código del error
        :param error_message: Mensaje del error
        :param http_status: Código HTTP (400, 401, 422, 500)
        :param details: Detalles adicionales del error
        :param retry: Si se puede reintentar
        :return: Dict con respuesta de error
        """
        response = {
            'status': 'error',
            'error': {
                'code': error_code,
                'message': error_message
            },
            'retry': retry
        }
        
        if details:
            response['error']['details'] = details
        
        # Establecer código HTTP en la respuesta
        request.httprequest.status_code = http_status
        
        return response
