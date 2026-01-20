# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RelaticInvoiceService(models.Model):
    _name = 'relatic.invoice.service'
    _description = 'Servicio para crear facturas desde Relatic'

    def create_invoice(self, partner, order_id, items, payment_data):
        """
        Crear factura desde datos de orden
        
        :param partner: res.partner record
        :param order_id: Order ID de Relatic
        :param items: Lista de items
        :param payment_data: Datos del pago
        :return: account.move record (factura)
        """
        # Verificar que no exista ya
        existing = self.env['account.move'].search_by_relatic_order_id(order_id)
        if existing:
            return existing
        
        # Validar que el partner tenga cuenta por cobrar configurada
        if not partner.property_account_receivable_id:
            raise ValidationError(
                f'Cuenta por cobrar no configurada para contacto: {partner.name}. '
                'Configure la cuenta en el contacto o en su tipo de contacto.'
            )
        
        # Preparar líneas de factura
        invoice_lines = []
        for item in items:
            product = self._get_or_create_product(item)
            
            # Calcular impuesto
            tax_ids = []
            tax_rate = item.get('tax_rate', 7.0)
            if tax_rate and tax_rate > 0:
                tax = self._get_tax(tax_rate)
                if tax:
                    tax_ids = [(6, 0, [tax.id])]
            
            # Obtener cuenta de ingreso del producto
            account_id = product.property_account_income_id.id or \
                         product.categ_id.property_account_income_categ_id.id
            
            if not account_id:
                raise ValidationError(
                    f'Cuenta de ingreso no configurada para producto: {product.name}. '
                    'Configure la cuenta en el producto o en su categoría.'
                )
            
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'name': item.get('name', product.name),
                'quantity': item.get('qty', 1),
                'price_unit': item.get('price', 0),
                'tax_ids': tax_ids,
                'account_id': account_id,
            }))
        
        # Validar fecha
        invoice_date = payment_data.get('date', fields.Date.today())
        if isinstance(invoice_date, str):
            invoice_date = fields.Date.from_string(invoice_date)
        
        # Crear factura
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_origin': order_id,
            'ref': payment_data.get('reference', ''),
            'invoice_date': invoice_date,
            'invoice_line_ids': invoice_lines,
            'x_relatic_order_id': order_id,
        })
        
        # Validar factura
        invoice._onchange_invoice_line_ids()
        
        # Confirmar factura
        invoice.action_post()
        
        return invoice

    def _get_or_create_product(self, item):
        """
        Obtener o crear producto desde SKU
        
        :param item: Dict con datos del item
        :return: product.product record
        """
        sku = item.get('sku')
        if not sku:
            raise ValidationError('SKU es requerido para crear línea de factura')
        
        product = self.env['product.product'].search([
            ('default_code', '=', sku)
        ], limit=1)
        
        if not product:
            # Verificar si está habilitado auto-crear productos
            auto_create = self.env['ir.config_parameter'].sudo().get_param(
                'relatic_integration.auto_create_product',
                'False'
            ) == 'True'
            
            if not auto_create:
                raise ValidationError(
                    f"El producto con SKU '{sku}' no existe en Odoo. "
                    "Active 'auto_create_product' en configuración para crearlo automáticamente."
                )
            
            # Obtener o crear categoría de productos Relatic
            category = self._get_or_create_product_category('Relatic')
            
            # Obtener cuenta de ingreso por defecto
            account_income = self._get_default_income_account()
            
            # Crear producto automáticamente
            product = self.env['product.product'].create({
                'name': item.get('name', sku),
                'default_code': sku,
                'type': 'service',
                'sale_ok': True,
                'purchase_ok': False,
                'categ_id': category.id,
                'property_account_income_id': account_income.id if account_income else False,
                'x_relatic_auto': True,  # Marcar como auto-creado
            })
        
        return product

    def _get_or_create_product_category(self, category_name):
        """
        Obtener o crear categoría de productos
        
        :param category_name: Nombre de la categoría
        :return: product.category record
        """
        category = self.env['product.category'].search([
            ('name', '=', category_name)
        ], limit=1)
        
        if not category:
            # Buscar categoría "All" como padre
            parent = self.env['product.category'].search([('name', '=', 'All')], limit=1)
            
            category = self.env['product.category'].create({
                'name': category_name,
                'parent_id': parent.id if parent else False,
            })
        
        return category

    def _get_default_income_account(self):
        """
        Obtener cuenta de ingreso por defecto
        
        :return: account.account record o False
        """
        # Buscar cuenta de ingreso por servicios
        account = self.env['account.account'].search([
            ('code', 'like', '4%'),  # Cuentas de ingreso generalmente empiezan con 4
            ('account_type', '=', 'income'),
        ], limit=1)
        
        return account

    def _get_tax(self, tax_rate):
        """
        Obtener impuesto por tasa
        
        :param tax_rate: Tasa del impuesto (ej: 7.0 para 7%)
        :return: account.tax record o False
        """
        # Buscar impuesto por cantidad
        tax = self.env['account.tax'].search([
            ('amount', '=', tax_rate),
            ('type_tax_use', '=', 'sale'),
        ], limit=1)
        
        return tax
