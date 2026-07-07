# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################

{
    'name': 'HR Work Anniversary Reminder',
    'version': '0.1',
    'summary': 'Automatic email greetings on employee work anniversaries.',
    'category': 'Human Resources',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/',
    'license': 'AGPL-3',
    'depends': ['hr', 'mail', 'hr_contract'],
    'data': [
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
