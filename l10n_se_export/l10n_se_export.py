# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import itertools
from lxml import etree

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

import openerp.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)

from fnmatch import fnmatch,fnmatchcase

from openerp.addons.web.http import request


def content_disposition(filename):
    filename = filename.encode('utf8')
    escaped = filename
    browser = request.httprequest.user_agent.browser
    version = int((request.httprequest.user_agent.version or '0').split('.')[0])
    if browser == 'msie' and version < 9:
        return "attachment; filename=%s" % escaped
    elif browser == 'safari':
        return "attachment; filename=%s" % filename
    else:
        return "attachment; filename*=UTF-8''%s" % escaped





class l10n_se_export(models.AbstractModel):
    _name = 'report.l10n_se_export.export_transaction_container'
            
    @api.multi
    def render_html(self, data=None):
            
        def export_xml(lines):
            document = etree.Element('openerp')
            data = etree.SubElement(document,'data')
            for line in lines:
                if line.id:
                    k,id = line.get_external_id().items()[0] if line.get_external_id() else 0,"%s-%s" % (line._name,line.id)
                    _logger.info("Reporting Block id = %s" % id)          
                    record = etree.SubElement(data,'record',id=id,model=line._name)
                    names = [name for name in line.fields_get().keys() if fnmatch(name,'in_group*')] + [name for name in line.fields_get().keys() if fnmatch(name,'sel_groups*')]
                    for field,values in line.fields_get().items():
                        if not field in ['create_date','nessage_ids','id','write_date','create_uid','__last_update','write_uid',] + names:
                            if values.get('type') in ['boolean','char','text','float','integer','selection','date','datetime']:
                                if eval('line.%s' % field):
                                    etree.SubElement(record,'field',name = field).text = "%s" % eval('line.%s' % field)
                            elif values.get('type') in ['many2one']:
                                if eval('line.%s' % field):                                     
                                    k,id = eval('line.%s.get_external_id().items()[0]' % field) if eval('line.%s.get_external_id()' % field) else (0,"%s-%s" % (eval('line.%s._name' % field),eval('line.%s.id' % field)))
                                    if id == "":
                                        id = "%s-%s" % (eval('line.%s._name' % field),eval('line.%s.id' % field))
                                    etree.SubElement(record,'field',name=field,ref="%s" % id)
                            elif values.get('type') in ['one2many']:  # Update from the other end
                                pass
                            elif values.get('type') in ['many2many']:
                                etree.SubElement(record,'field',name=field,ref="%s %s" % (values.get('type'),eval('line.%s' % field)))
                    
            return document

        def get_related(models,depth):
            objects = set()
            if depth < 4:
                for model in models:
                    _logger.info('Get related model %s id %s' % (model._name,model.id))
                    for field,values in model.fields_get().items(): 
                        if not field in ['create_date','nessage_ids','id','write_date','create_uid','__last_update','write_uid']:
                            if values.get('type') in ['many2one']:
                                for related in get_related(eval("model.%s" % field),depth+1):
                                    objects.add(related)
                    objects.add(model)
            return objects

        
        
        
        
        
        _logger.info("Reporting Block")
        report = self.env['report']._get_report_from_name('l10n_se_export.export_transaction_container')
        return self.env[report.model].browse(self._ids).export_data(['name'])
        
        
        document = etree.tostring(export_xml(list(get_related(self.env[report.model].browse(self._ids),0))),pretty_print=True,encoding="utf-8")
        #return request.make_response(document,
         #headers=[
             #('Content-Disposition', content_disposition("%s.xml" % report.model)),
             #('Content-Type',  	'application/rdf+xml'),
             #('Content-Length', len(document))],)
        
        
        document= export_xml(list(get_related(self.env[report.model].browse(self._ids),0)))
                
        return etree.tostring(document,pretty_print=True,encoding="utf-8")



        
        partner = set()  # to create uniq lists
        journal = set()
        account = set()
        account_tax = set()
        period = set()
        lines = []
        company = set()
        invoice = set()
        product = set()
        moves = self.env['account.move'].browse(self._ids)
        for move in moves:
            for line in move.line_id:
                lines.append(line)
                account.add(line.account_id)
                account_tax.add(line.account_tax_id)
                invoice.add(line.invoice)
                product.add(line.product_id)
                
            partner.add(move.partner_id)
            period.add(move.period_id)
            company.add(move.company_id)
            journal.add(move.journal_id)


        
        document= export_xml(list(company)+list(period)+list(account)+list(account_tax)+list(partner)+list(product)+list(invoice)+list(moves)+lines) # + period + account + account_tax + partner + product + journal + moves + lines )
                
        return etree.tostring(document,pretty_print=True,encoding="utf-8")
        
        #return self.env['report'].render('l10n_se_export.export_transaction_container', {
                    #'report': report,
                    #'doc_ids': self._ids,
                    #'doc_model': report.model,
                    #'partner': list(partner),
                    #'journal': list(journal),
                    #'account': list(account),
                    #'period': list(period),
                    #'lines': lines,
                    #'moves': moves,
                    #'company': list(company),
                #})


#~ class Model(models.BaseModel):
    #~ 
#~ 
    #~ @api.multi
    #~ def export_kalle(self):
        #~ """ export_xml() -> xml
#~ 
        #~ Returns a xml-recordset for the records provided as parameter in the current
        #~ environment.
#~ 
        #~ """
        #~ return self


    #~ def _export_xml(lines):
        #~ document = etree.Element('openerp')
        #~ data = etree.SubElement(document,'data')
        #~ for line in lines:
            #~ if line.id:
                #~ k,id = line.get_external_id().items()[0] if line.get_external_id() else 0,"%s-%s" % (line._name,line.id)
                #~ _logger.info("Reporting Block id = %s" % id)          
                #~ record = etree.SubElement(data,'record',id=id,model=line._name)
                #~ names = [name for name in line.fields_get().keys() if fnmatch(name,'in_group*')] + [name for name in line.fields_get().keys() if fnmatch(name,'sel_groups*')]
                #~ for field,values in line.fields_get().items():
                    #~ if not field in ['create_date','nessage_ids','id','write_date','create_uid','__last_update','write_uid',] + names:
                        #~ if values.get('type') in ['boolean','char','text','float','integer','selection','date','datetime']:
                            #~ if eval('line.%s' % field):
                                #~ etree.SubElement(record,'field',name = field).text = "%s" % eval('line.%s' % field)
                        #~ elif values.get('type') in ['many2one']:
                            #~ if eval('line.%s' % field):                                     
                                #~ k,id = eval('line.%s.get_external_id().items()[0]' % field) if eval('line.%s.get_external_id()' % field) else (0,"%s-%s" % (eval('line.%s._name' % field),eval('line.%s.id' % field)))
                                #~ if id == "":
                                    #~ id = "%s-%s" % (eval('line.%s._name' % field),eval('line.%s.id' % field))
                                #~ etree.SubElement(record,'field',name=field,ref="%s" % id)
                        #~ elif values.get('type') in ['one2many']:  # Update from the other end
                            #~ pass
                        #~ elif values.get('type') in ['many2many']:
                            #~ etree.SubElement(record,'field',name=field,ref="%s %s" % (values.get('type'),eval('line.%s' % field)))
                #~ 
        #~ return document
#~ 
        #~ def _get_related(models,depth):
            #~ objects = set()
            #~ if depth < 4:
                #~ for model in models:
                    #~ _logger.info('Get related model %s id %s' % (model._name,model.id))
                    #~ for field,values in model.fields_get().items(): 
                        #~ if not field in ['create_date','nessage_ids','id','write_date','create_uid','__last_update','write_uid']:
                            #~ if values.get('type') in ['many2one']:
                                #~ for related in get_related(eval("model.%s" % field),depth+1):
                                    #~ objects.add(related)
                    #~ objects.add(model)
            #~ return list(objects)

     

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
