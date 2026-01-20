# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class RelaticPartnerService(models.Model):
    _name = 'relatic.partner.service'
    _description = 'Servicio para crear/actualizar contactos desde Relatic'

    def create_or_update_partner(self, member_data):
        """
        Crear o actualizar contacto desde datos de member
        
        :param member_data: Dict con datos del miembro
        :return: res.partner record
        """
        email = member_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError('Email es requerido para crear/actualizar contacto')
        
        # Validar formato de email
        if not self._validate_email(email):
            raise ValidationError(f'Formato de email inválido: {email}')
        
        # Buscar por email (case insensitive)
        partner = self.env['res.partner'].search([
            ('email', '=ilike', email)
        ], limit=1)
        
        # Preparar valores
        name = member_data.get('name', '').strip()
        if not name:
            raise ValidationError('Nombre es requerido para crear/actualizar contacto')
        
        values = {
            'name': name,
            'email': email,
            'phone': self._normalize_phone(member_data.get('phone', '')),
            'vat': self._normalize_vat(member_data.get('vat', '')),
            'street': member_data.get('street', '').strip(),
            'city': member_data.get('city', '').strip(),
            'is_company': False,
            'customer_rank': 1,
        }
        
        # País si se especifica
        country_code = member_data.get('country_code', 'PA')
        if country_code:
            country = self.env['res.country'].search([
                ('code', '=', country_code.upper())
            ], limit=1)
            if country:
                values['country_id'] = country.id
            else:
                # Si no existe, usar Panamá por defecto
                country_pa = self.env['res.country'].search([('code', '=', 'PA')], limit=1)
                if country_pa:
                    values['country_id'] = country_pa.id
        
        # Etiqueta RELATIC_MIEMBRO
        category = self._get_or_create_category('RELATIC_MIEMBRO')
        
        if partner:
            # Actualizar existente (solo campos no vacíos)
            update_values = {k: v for k, v in values.items() if v}
            partner.write(update_values)
            if category not in partner.category_id:
                partner.category_id = [(4, category.id)]
        else:
            # Crear nuevo
            values['category_id'] = [(4, category.id)]
            partner = self.env['res.partner'].create(values)
        
        return partner

    def _validate_email(self, email):
        """
        Validar formato de email básico
        
        :param email: Email a validar
        :return: True si es válido
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _normalize_phone(self, phone):
        """
        Normalizar formato de teléfono
        
        :param phone: Teléfono a normalizar
        :return: Teléfono normalizado
        """
        if not phone:
            return ''
        
        # Remover espacios y caracteres especiales excepto + y números
        phone = re.sub(r'[^\d+]', '', phone.strip())
        return phone

    def _normalize_vat(self, vat):
        """
        Normalizar formato de VAT/RUC
        
        :param vat: VAT a normalizar
        :return: VAT normalizado
        """
        if not vat:
            return ''
        
        # Remover espacios y mantener formato
        return vat.strip().upper()

    def _get_or_create_category(self, category_name):
        """
        Obtener o crear categoría de contacto
        
        :param category_name: Nombre de la categoría
        :return: res.partner.category record
        """
        category = self.env['res.partner.category'].search([
            ('name', '=', category_name)
        ], limit=1)
        
        if not category:
            category = self.env['res.partner.category'].create({
                'name': category_name
            })
        
        return category
