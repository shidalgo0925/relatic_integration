# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import hashlib
import json


class RelaticSyncLog(models.Model):
    _name = 'relatic.sync.log'
    _description = 'Log de Sincronización Relatic'
    _order = 'create_date desc'
    _rec_name = 'order_id'

    # Campos principales
    order_id = fields.Char(
        string='Order ID',
        required=True,
        index=True,
        help='Identificador único de la orden desde membresia-relatic'
    )
    
    payload_hash = fields.Char(
        string='Hash Payload',
        index=True,
        help='Hash SHA256 del payload recibido para auditoría'
    )
    
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('success', 'Exitoso'),
        ('error', 'Error'),
        ('retry', 'Reintento'),
    ], string='Estado', required=True, default='pending', index=True)
    
    retries = fields.Integer(
        string='Reintentos',
        default=0,
        help='Número de intentos de sincronización'
    )
    
    error_message = fields.Text(
        string='Mensaje de Error',
        help='Mensaje detallado del error si ocurrió'
    )
    
    error_code = fields.Char(
        string='Código de Error',
        help='Código estándar del error (ej: PRODUCT_NOT_FOUND)'
    )
    
    # Relaciones
    partner_id = fields.Many2one(
        'res.partner',
        string='Contacto',
        ondelete='set null',
        help='Contacto creado o actualizado'
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura',
        domain=[('move_type', '=', 'out_invoice')],
        ondelete='set null',
        help='Factura creada'
    )
    
    payment_move_id = fields.Many2one(
        'account.move',
        string='Movimiento de Pago',
        domain=[('move_type', '=', 'entry')],
        ondelete='set null',
        help='Movimiento contable del pago registrado'
    )
    
    # Metadata
    payload_version = fields.Char(
        string='Versión Payload',
        help='Versión del contrato API usado'
    )
    
    source = fields.Char(
        string='Origen',
        default='membresia-relatic',
        help='Sistema origen del webhook'
    )
    
    environment = fields.Selection([
        ('prod', 'Producción'),
        ('staging', 'Staging'),
        ('dev', 'Desarrollo'),
    ], string='Ambiente', help='Ambiente del sistema origen')
    
    processing_time = fields.Float(
        string='Tiempo Procesamiento (seg)',
        digits=(16, 3),
        help='Tiempo total de procesamiento en segundos'
    )
    
    # Campos calculados
    invoice_number = fields.Char(
        string='Número de Factura',
        related='invoice_id.name',
        store=True,
        readonly=True
    )
    
    partner_name = fields.Char(
        string='Nombre Contacto',
        related='partner_id.name',
        store=True,
        readonly=True
    )
    
    # Timestamps
    received_at = fields.Datetime(
        string='Recibido en',
        default=fields.Datetime.now,
        required=True,
        readonly=True
    )
    
    processed_at = fields.Datetime(
        string='Procesado en',
        readonly=True,
        help='Fecha y hora en que se completó el procesamiento'
    )

    @api.model
    def create_log(self, order_id, payload, status='pending', **kwargs):
        """
        Método helper para crear un log de sincronización
        
        :param order_id: ID de la orden
        :param payload: Diccionario con el payload recibido
        :param status: Estado inicial ('pending', 'success', 'error', 'retry')
        :param kwargs: Campos adicionales (partner_id, invoice_id, etc.)
        :return: registro creado
        """
        # Calcular hash del payload
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        payload_hash = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
        
        # Extraer metadata del payload si existe
        meta = payload.get('meta', {})
        
        values = {
            'order_id': order_id,
            'payload_hash': payload_hash,
            'status': status,
            'payload_version': meta.get('version'),
            'source': meta.get('source', 'membresia-relatic'),
            'environment': meta.get('environment'),
            **kwargs
        }
        
        return self.create(values)

    def mark_success(self, partner_id=None, invoice_id=None, payment_move_id=None, processing_time=0.0):
        """
        Marcar log como exitoso
        
        :param partner_id: ID del contacto creado/actualizado
        :param invoice_id: ID de la factura creada
        :param payment_move_id: ID del movimiento de pago
        :param processing_time: Tiempo de procesamiento en segundos
        """
        self.write({
            'status': 'success',
            'partner_id': partner_id,
            'invoice_id': invoice_id,
            'payment_move_id': payment_move_id,
            'processing_time': processing_time,
            'processed_at': fields.Datetime.now(),
        })

    def mark_error(self, error_code, error_message, retry=False):
        """
        Marcar log como error
        
        :param error_code: Código del error
        :param error_message: Mensaje del error
        :param retry: Si es True, marca como 'retry', sino como 'error'
        """
        self.write({
            'status': 'retry' if retry else 'error',
            'error_code': error_code,
            'error_message': error_message,
            'retries': self.retries + 1,
            'processed_at': fields.Datetime.now(),
        })

    def increment_retry(self):
        """Incrementar contador de reintentos"""
        self.write({
            'retries': self.retries + 1,
            'status': 'retry',
        })

    @api.constrains('order_id')
    def _check_order_id_unique(self):
        """Validar que no haya duplicados por order_id en mismo día"""
        for record in self:
            if self.search_count([
                ('order_id', '=', record.order_id),
                ('id', '!=', record.id),
                ('create_date', '>=', fields.Datetime.today()),
            ]) > 0:
                raise ValidationError(
                    f'Ya existe un log para la orden {record.order_id} hoy. '
                    'Verifique que no se esté procesando duplicado.'
                )

    def name_get(self):
        """Personalizar nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.order_id} - {dict(record._fields['status'].selection).get(record.status, '')}"
            if record.invoice_number:
                name += f" ({record.invoice_number})"
            result.append((record.id, name))
        return result
