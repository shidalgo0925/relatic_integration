# -*- coding: utf-8 -*-
{
    'name': 'Relatic Integration',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Integración con sistema de membresía Relatic',
    'description': """
        Integración con sistema de membresía Relatic
        ============================================
        
        Este módulo permite:
        - Recibir webhooks desde membresia-relatic
        - Crear/actualizar contactos automáticamente
        - Generar facturas de cliente
        - Registrar pagos y conciliar facturas
        - Mantener trazabilidad completa con logs de sincronización
    """,
    'author': 'Relatic',
    'website': 'https://relatic.org',
    'depends': [
        'base',
        'account',
        'sale',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/relatic_sync_log_views.xml',
        'data/ir_config_parameter_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
