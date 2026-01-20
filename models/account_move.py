# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_relatic_order_id = fields.Char(
        string='Relatic Order ID',
        index=True,
        copy=False,
        help='Identificador único de la orden desde membresia-relatic para idempotencia'
    )

    _sql_constraints = [
        ('relatic_order_unique',
         'UNIQUE(x_relatic_order_id)',
         'Ya existe una factura con este Order ID de Relatic. Verifique que no se esté procesando duplicado.')
    ]

    @api.model
    def search_by_relatic_order_id(self, order_id):
        """
        Buscar factura por Relatic Order ID
        
        :param order_id: Order ID de Relatic
        :return: recordset con factura encontrada o vacío
        """
        return self.search([
            ('x_relatic_order_id', '=', order_id),
            ('move_type', '=', 'out_invoice')
        ], limit=1)
