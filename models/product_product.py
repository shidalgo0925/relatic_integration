# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    x_relatic_auto = fields.Boolean(
        string='Auto-creado por Relatic',
        default=False,
        help='Indica si el producto fue creado automáticamente por la integración Relatic'
    )
