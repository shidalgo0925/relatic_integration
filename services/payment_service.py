# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RelaticPaymentService(models.Model):
    _name = 'relatic.payment.service'
    _description = 'Servicio para registrar pagos desde Relatic'

    def register_payment(self, invoice, partner, payment_data, partial=False):
        """
        Registrar pago y conciliar factura
        
        IMPORTANTE: En Odoo 18, los pagos son account.move (no account.payment)
        
        :param invoice: account.move record (factura)
        :param partner: res.partner record
        :param payment_data: Dict con datos del pago
        :param partial: Si es True, permite pago parcial
        :return: account.move record (movimiento de pago)
        """
        # Validar que la factura esté confirmada
        if invoice.state != 'posted':
            raise ValidationError(f'La factura {invoice.name} debe estar confirmada para registrar pago')
        
        # Obtener diario según método de pago
        journal = self._get_journal(payment_data.get('method', ''))
        if not journal:
            raise ValidationError(
                f"Diario no configurado para método de pago: {payment_data.get('method')}"
            )
        
        # Obtener cuentas
        bank_account = journal.default_account_id
        if not bank_account:
            raise ValidationError(f"Cuenta por defecto no configurada en diario: {journal.name}")
        
        receivable_account = partner.property_account_receivable_id
        if not receivable_account:
            raise ValidationError(f"Cuenta por cobrar no configurada para contacto: {partner.name}")
        
        amount = float(payment_data.get('amount', 0))
        payment_date = payment_data.get('date', fields.Date.today())
        
        if isinstance(payment_date, str):
            payment_date = fields.Date.from_string(payment_date)
        
        # Validar monto
        if amount <= 0:
            raise ValidationError('El monto del pago debe ser mayor a cero')
        
        # Validar monto vs factura (si no es parcial)
        invoice_residual = abs(invoice.amount_residual)
        if not partial and abs(amount - invoice_residual) > 0.01:
            raise ValidationError(
                f'El monto del pago ({amount}) no coincide con el monto pendiente de la factura ({invoice_residual}). '
                'Use partial=True para pagos parciales.'
            )
        
        # Si es pago parcial, usar el monto menor entre el pago y el pendiente
        if partial:
            amount = min(amount, invoice_residual)
        
        # Crear movimiento contable de pago (Odoo 18)
        payment_move = self.env['account.move'].create({
            'move_type': 'entry',  # Movimiento contable
            'date': payment_date,
            'journal_id': journal.id,
            'ref': payment_data.get('reference', ''),
            'line_ids': [
                # Línea banco / método de pago (débito)
                (0, 0, {
                    'account_id': bank_account.id,
                    'debit': amount,
                    'credit': 0.0,
                    'partner_id': partner.id,
                    'name': f"Pago {payment_data.get('reference', '')} - {invoice.name}",
                }),
                # Línea cliente (crédito)
                (0, 0, {
                    'account_id': receivable_account.id,
                    'debit': 0.0,
                    'credit': amount,
                    'partner_id': partner.id,
                    'name': f"Pago factura {invoice.name}",
                }),
            ],
        })
        
        # Validar y confirmar movimiento
        payment_move.action_post()
        
        # Conciliar factura con pago (soporta parcial)
        self._reconcile_invoice(invoice, payment_move, partial=partial)
        
        return payment_move

    def _get_journal(self, payment_method):
        """
        Obtener diario según método de pago
        
        :param payment_method: Método de pago (YAPPY, TARJETA, TRANSFERENCIA)
        :return: account.journal record o False
        """
        # Mapeo de métodos a nombres de diarios
        journal_names = {
            'YAPPY': 'YAPPY',
            'TARJETA': 'TARJETA',
            'TRANSFERENCIA': 'TRANSFERENCIA',
        }
        
        journal_name = journal_names.get(payment_method.upper())
        if not journal_name:
            return False
        
        journal = self.env['account.journal'].search([
            ('name', '=', journal_name),
            ('type', '=', 'bank'),
        ], limit=1)
        
        return journal

    def _reconcile_invoice(self, invoice, payment_move, partial=False):
        """
        Conciliar factura con movimiento de pago
        
        :param invoice: account.move record (factura)
        :param payment_move: account.move record (pago)
        :param partial: Si es True, permite conciliación parcial
        """
        # Obtener líneas conciliables de la factura
        invoice_lines = invoice.line_ids.filtered(
            lambda l: l.account_id.reconcile and 
                      l.account_id == invoice.partner_id.property_account_receivable_id and
                      not l.reconciled
        )
        
        # Obtener líneas conciliables del pago
        payment_lines = payment_move.line_ids.filtered(
            lambda l: l.account_id.reconcile and 
                      l.account_id == invoice.partner_id.property_account_receivable_id and
                      not l.reconciled
        )
        
        # Conciliar (soporta parcial automáticamente)
        if invoice_lines and payment_lines:
            (invoice_lines + payment_lines).reconcile()

    def create_refund(self, invoice, order_id, reason=''):
        """
        Crear nota de crédito (reembolso) para una factura
        
        :param invoice: account.move record (factura original)
        :param order_id: Order ID de Relatic (con sufijo -REFUND)
        :param reason: Razón del reembolso
        :return: account.move record (nota de crédito)
        """
        # Verificar que la factura esté confirmada
        if invoice.state != 'posted':
            raise ValidationError(f'La factura {invoice.name} debe estar confirmada para crear reembolso')
        
        # Verificar que no exista ya el reembolso
        refund_order_id = f"{order_id}-REFUND"
        existing_refund = self.env['account.move'].search_by_relatic_order_id(refund_order_id)
        if existing_refund:
            return existing_refund
        
        # Crear nota de crédito copiando líneas de la factura original
        refund_lines = []
        for line in invoice.invoice_line_ids:
            refund_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.quantity,
                'price_unit': -line.price_unit,  # Negativo para nota de crédito
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'account_id': line.account_id.id,
            }))
        
        # Crear nota de crédito
        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': invoice.partner_id.id,
            'invoice_origin': order_id,
            'ref': reason or f'Reembolso de {invoice.name}',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': refund_lines,
            'x_relatic_order_id': refund_order_id,
        })
        
        # Validar y confirmar nota de crédito
        refund._onchange_invoice_line_ids()
        refund.action_post()
        
        return refund
