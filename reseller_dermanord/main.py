# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2017- Vertel AB (<http://vertel.se>).
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

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import http
from openerp.http import request
import urllib
import json
import werkzeug
import base64
import math
from datetime import date
from dateutil.relativedelta import relativedelta
from openerp.addons.website_sale_home.website_sale import website_sale_home

import logging
_logger = logging.getLogger(__name__)

class res_partner(models.Model):
    _inherit = 'res.partner'

    brand_name = fields.Char(string='Brand Name')
    is_reseller = fields.Boolean(string='Show Reseller in websearch')
    always_searchable = fields.Boolean(string='Always searchable', help='When checked. Reseller is always searchable.')
    top_image = fields.Binary(string='Top Image')
    type = fields.Selection(selection_add=[('visit', 'Visit')])
    webshop_category_ids = fields.Many2many(comodel_name='product.public.category', string='Product Categories', domain=[('website_published', '=', True)])
    website_short_description = fields.Text(string='Website Partner Short Description', translate=True)
    
    # ~ visit_city = fields.Char(string='Visit Adress City', compute='_compute_visit_city', store=True)
    
    # ~ #env['res.partner'].search([('is_reseller', 's=', True), ('child_ids.type', '=', 'visit')])._compute_visit_city()
    # ~ @api.one
    # ~ @api.depends('child_ids.type', 'child_ids.city', 'child_ids.active')
    # ~ def _compute_visit_city(self):
        # ~ pass
        # ~ _logger.warn('\n\n%s._compute_visit_city()' % self)
        # ~ visit = self.child_ids.filtered(lambda c: c.active == True and c.type == 'visit' and c.city)
        # ~ if visit:
            # ~ self.visit_city = visit[0].city
        # ~ else:
            # ~ self.visit_city = False

    #~ @api.one
    #~ def _is_reseller(self):
        #~ self.is_reseller = self.env['ir.model.data'].xmlid_to_object('reseller_dermanord.reseller_tag') in self.category_id

    #~ @api.model
    #~ def _search_is_reseller(self, operator, value):
        #~ resellers = self.env.search([('category_id', '=', self.env['ir.model.data'].xmlid_to_object('reseller_dermanord.reseller_tag').id)])
        #~ return [('id', 'in', [r.id for r in resellers])]

    @api.one
    @api.onchange('always_searchable')
    def always_searchable_onchange(self):
        if self.always_searchable:
            self.is_reseller = True

    @api.multi
    def write(self, vals):
        if 'always_searchable' in vals:
            if vals.get('always_searchable'):
                vals['is_reseller'] = True
        res = super(res_partner, self).write(vals)
        return res

    @api.multi
    def searchable_reseller(self):
        self.ensure_one()
        # is company and customer
        # has tag Hudterapeut eller SPA-terapeut, and has purchased more than 10000SEK(ex.moms) in last 12 months.
        # has other tags and purchase more than 2000SEK(ex.moms) once in last 12 months.
        if not self.always_searchable:
            previous_is_reseller = self.is_reseller
            self.is_reseller = False
            if (self.env['res.partner.category'].search([('name', '=', 'Hudterapeut')])[0] in self.category_id) or (self.env['res.partner.category'].search([('name', '=', 'SPA-Terapeut')])[0] in self.category_id):
                if sum(self.env['account.invoice'].search(['|', ('partner_id', '=', self.id), ('partner_id.child_ids', '=', self.id), ('date_invoice', '>=', fields.Date.to_string((date.today()-relativedelta(years=1))))]).mapped('amount_untaxed')) >= 10000.0:
                    self.is_reseller = True
            else:
                if sum(self.env['account.invoice'].search(
                        ['|', ('partner_id', '=', self.id), ('partner_id.child_ids', '=', self.id), ('date_invoice', '>=', fields.Date.to_string((date.today()-relativedelta(years=1))))]
                        ).mapped('amount_untaxed')) > 2000.0:
                    self.is_reseller = True
            if self.is_reseller != previous_is_reseller:
                # send message to responsible
                self.env['mail.message'].create({
                    'model': 'res.partner',
                    'res_id': self.id,
                    'author_id': self.env.ref('base.partner_root').id,
                    'subject': _('Partner show reseller in websearch updated'),
                    'type': 'notification',
                    'body': """<p>Show in Websearch: %s → %s</p>""" %(previous_is_reseller, self.is_reseller)
                })

    @api.model
    def searchable_reseller_cron(self):
        for partner in self.env['res.partner'].search([('is_company', '=', True), ('customer', '=', True)]):
            partner.searchable_reseller()

    @api.model
    def highest_sales_resellers_cron(self):
        domain = [('date_order', '>', '%s%s' %(str(int(fields.Datetime.now()[:4])-1), fields.Datetime.now()[4:])), ('date_order', '<=', fields.Datetime.now()), ('partner_id.is_reseller', '=', True), ('partner_id.is_company', '=', True), ('partner_id.is_reseller', '=', True), ('partner_id.has_webshop', '=', True), ('state', '=', 'done')]
        sos = self.env['sale.order'].search(domain)
        partners = sos.mapped('partner_id')
        d = {}
        for partner in partners:
            d[partner.id] = sum(self.env['sale.order'].search(domain + [('partner_id', '=', partner.id)]).mapped('amount_total'))
        sorted_d = sorted(d.items(), key=lambda x: x[1], reverse=True)
        partner_ids = [p[0] for p in sorted_d]
        lst = partner_ids[:25] if len(partner_ids) > 25 else partner_ids
        partner_lst = []
        for l in lst:
            p = self.env['res.partner'].browse(l)
            partner_lst.append([l, p.webshop_category_ids.mapped('id')])
        self.env['ir.config_parameter'].set_param(key='reseller_dermanord.highest_sales_resellers', value=str(partner_lst))


class Main(http.Controller):

    def get_reseller_domain_append(self, post):
        country_ids = []
        cities = []
        competence_ids = []
        assortment_ids = []

        for k, v in post.iteritems():
            if k.split('_')[0] == 'country':
                if v:
                    country_ids.append(int(v))
            if k.split('_')[0] == 'city':
                if v:
                     cities.append(v)
            if k.split('_')[0] == 'competence':
                if v:
                    competence_ids.append(int(v))
            if k.split('_')[0] == 'assortment':
                if v:
                    assortment_ids.append(int(v))

        domain_append = []
        domain_append += [('is_reseller', '=', True)]
        if country_ids:
            domain_append.append(('country_id', 'in', country_ids))
        if cities:
            domain_append.append(('city', '=', cities))
        if competence_ids:
            domain_append.append(('child_category_ids', 'in', competence_ids))
        if assortment_ids:
            domain_append.append(('category_id', 'in', assortment_ids))
        if post.get('webshop') == '1':
            domain_append.append(('website', '!=', ''))

        return domain_append

    def get_reseller_form_values(self):
        if not request.session.get('form_values'):
            request.session['form_values'] = {}
        return request.session.get('form_values')

    def get_reseller_chosen_filter_qty(self, post):
        chosen_filter_qty = 0
        for k, v in post.iteritems():
            if k not in ['post_form', 'order', 'webshop', 'view']:
                chosen_filter_qty += 1
        return chosen_filter_qty

    def get_reseller_chosen_order(self, post):
        sort_name = 'name'
        sort_order = 'asc'
        for k, v in post.iteritems():
            if k == 'order':
                sort_name = post.get('order').split(' ')[0]
                sort_order = post.get('order').split(' ')[1]
                break
        return [sort_name, sort_order]

    def sort_reseller(self, resellers):
        # ~ _logger.warn(len(resellers))
        res = resellers.sorted(key=lambda p: p.child_ids.filtered(lambda c: c.type == 'visit').city)
        # ~ _logger.warn(len(res))
        return res

    def restore_original_order(self, records, order):
        def sorter(record):
            try:
                # Check index in original list
                return order.index(record.id)
            except:
                # Not in the original list. Position last.
                return len(order)
        records.sorted(sorter)
    
    def check_for_city(self, country, word_list):
        """Check if the given word is a city. Deletes the first found city from word_list.
        :returns: city name or None."""
        # ~ _logger.warn('\n\ncheck_for_city: %s, %s\n' % (country, word_list))
        for i in range(len(word_list)):
            word = word_list[i]
            request.env.cr.execute("""
                    select city
                        from location_zcs l
                        where country=%s AND city ilike %s limit 1
                """, (country, word))
            city = request.env.cr.dictfetchone()
            # ~ _logger.warn(city)
            if city:
                # Its a city
                del word_list[i]
                return city['city']
    
    def check_for_postal_code(self, country, word_list):
        """Check word_list for a postal code. Deletes the first found code from word_list.
        :returns: postal code or None."""
        # TODO: Implement postal codes for other countries
        if country == 'SE':
            # Swedish postal codes
            first_part = None
            # Check for correct formatting first.
            for i in range(len(word_list)):
                word = word_list[i]
                if len(word) == 3 and word.isdigit():
                    # Found possible first half
                    first_part = word
                    continue
                elif first_part and len(word) == 2 and word.isdigit():
                    # Possible match. Check if its an actual postal code.
                    request.env.cr.execute("""
                            select postalcode
                                from location_zcs l
                                where country=%s AND postalcode = %s limit 1
                        """, (country, '%s %s' % (first_part, word)))
                    code = request.env.cr.dictfetchone()
                    if code:
                        del word_list[i]
                        del word_list[i-1]
                        return code['postalcode']
                first_part = None
            # Check for postal codes without space.
            for i in range(len(word_list)):
                word = word_list[i]
                if len(word) == 5 and word.isdigit():
                    # Possible match. Check if its an actual postal code.
                    request.env.cr.execute("""
                            select postalcode
                                from location_zcs l
                                where country=%s AND postalcode = %s limit 1
                        """, (country, '%s %s' % (word[:3], word[3:])))
                    code = request.env.cr.dictfetchone()
                    if code:
                        del word_list[i]
                        return code['postalcode']
    
    # Return result of resellers with postcode, domain searching
    def get_resellers(self, words, domain, search_partner, params=None, webshop=False, limit=99):
        """Find resellers.
        
        :param words: Search terms.
        :param domain: Extra domain values to use.
        :param search_partner: Search function to use for text values.
        :param params: Extra parameters to send to search_partner.
        :param webshop: Webshop True/False. ??? Not used at all
        :param limit: Limit when searching.
        """
        # ~ _logger.warn('\n\nwords: %s\ndomain: %s\nsearch_partner: %s\nwebshop: %s\nlimit: %s' % (words, domain, search_partner, webshop, limit))
        params = params or {}
        words = words or ''
        partner_obj = request.env['res.partner'].sudo()
        resellers = partner_obj.browse()
        partner_ids = []
        country = request.session.get('geoip', {}).get('country_code', 'SE') # Country to use in postal code search
        city = None
        
        word_list = words.split()
        if word_list:
            # Identify country in search terms to use in postal code search
            for i in range(len(word_list)):
                c = request.env['res.country'].search([('name', 'ilike', word_list[i])])
                if c:
                    country = c.code
                    # Leave country to be used as search term.
                    #del word_list[i]
                    break
                    # TODO: country search has been broken.
            # Check for a postal code and city.
            postal_code = self.check_for_postal_code(country, word_list)
            city = self.check_for_city(country, word_list)
            # ~ _logger.warn('\nword_list: %s\npostal_code: %s\n' % (word_list, postal_code))
            
            if postal_code:
                # Search the postal code and get the closest reseller inside 0.5 degree
                partner_ids += partner_obj.geo_zip_search('position', 'SE', postal_code, domain + [('partner_latitude', '!=', 0.0), ('partner_longitude', '!=', 0.0)], distance=360, limit=limit) # this is supposed to be a limited distance
                if len(partner_ids) < limit:
                    # Fill up to limit with unlimited range.
                    partner_ids += partner_obj.geo_zip_search('position', 'SE', postal_code, domain + [('id', 'not in', partner_ids), ('partner_latitude', '!=', 0.0), ('partner_longitude', '!=', 0.0)], distance=360, limit=limit - len(partner_ids)) # this is supposed to be a limited distance
            
            if not partner_ids and city:
                # Perform city search
                partner_ids = partner_obj.geo_city_search('position', country, city, domain + [('partner_latitude', '!=', 0.0), ('partner_longitude', '!=', 0.0)], distance=360, limit=limit)
                # ~ _logger.warn('city search %s %s' % (city, partner_ids))
            
            if partner_ids:
                resellers = partner_obj.browse(partner_ids)
            
            # Search using search terms
            # Should this be combined with geo search results?
            if not partner_ids:
                # Search keyword
                for s in word_list:
                    if not resellers:
                        # First keyword search
                        resellers = search_partner(s, **params)
                    else:
                        # Restrict further for every keyword
                        resellers &= search_partner(s, **params)
                
                self.restore_original_order(resellers, partner_ids)
                if len(resellers) > limit:
                    resellers = resellers[:limit]
        else:
            # No search terms. Perform geo search.
            position = request.session.get('geoip', {})
            # ~ _logger.warn('\n\nposition: %s\n' % str(position))
            if 'latitude' in position and 'longitude' in position:
                position = (position['longitude'], position['latitude'])
                resellers = partner_obj.browse(partner_obj.geo_search('position', position, domain=domain, distance=360, limit=limit))
        return resellers

    def get_resellers_without_keyword(self, domain, position, distance=None, limit=10, webshop=False):
        partner_obj = request.env['res.partner']
        def get_partner_ids(d, l):
            return partner_obj.sudo().geo_search('position', position, domain + [('partner_latitude', '!=', 0.0), ('partner_longitude', '!=', 0.0)], distance=d, limit=l)
        if webshop:
            # ~ partner_ids = get_partner_ids(0.5, 5)
            # ~ if len(partner_ids) == 0:
            partner_ids = get_partner_ids(360, limit if limit else 5)
        else:
            # ~ partner_ids = get_partner_ids(0.5, 10)
            # ~ if len(partner_ids) == 0:
            partner_ids = get_partner_ids(360, limit if limit else 10)
        if len(partner_ids) > 0:
            return partner_obj.sudo().browse(partner_ids)
        else:
            return partner_obj.sudo().browse()

    # remove resellers has not street or street2
    def resellers_filter(self, resellers):
        res = []
        for r in resellers:
            visit = r.child_ids.filtered(lambda c: c.type == 'visit')
            if len(visit) > 0:
                if visit[0].street != '' or visit[0].street2 != '':
                    res.append(r)
        return res

    @http.route(['/resellers/competence/<model("res.partner.category"):competence>',], type='http', auth="public", website=True)
    def reseller_competence(self, competence, **post):
        partner_obj = request.env['res.partner']

        def search_partner_name(word, all_visit_ids):
            return partner_obj.sudo().search([
                ('is_company', '=', True),
                ('is_reseller', '=', True),
                ('child_ids.type', '=', 'visit'),
                ('child_ids', 'in', all_visit_ids),
                ('child_competence_ids', '=', competence.id),
                '|', '|', '|',
                    ('child_category_ids.name', 'ilike', word),
                    ('child_competence_ids.name', 'ilike', word),
                    ('brand_name', 'ilike', word),
                    '&',
                        ('name', 'ilike', word),
                        ('brand_name', '=', False),
                ], limit=100).sorted(key=lambda p: (p.child_ids.filtered(lambda c: c.type == 'visit').mapped('city'), p.brand_name))

        def search_partner(word, all_visit_ids):
            matching_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', ''), '|', ('street', 'ilike', word), '|', ('street2', 'ilike', word), '|', ('state_id.name', 'ilike', word), ('country_id.name', 'ilike', word)], ['id'])]
            res = partner_obj.sudo().search([
                ('is_company', '=', True),
                ('is_reseller', '=', True),
                ('child_ids.type', '=', 'visit'),
                ('child_ids', 'in', all_visit_ids),
                ('child_competence_ids', '=', competence.id),
                '|', '|',
                    ('child_ids', 'in', matching_visit_ids),
                    ('child_category_ids.name', 'ilike', word),
                    ('child_competence_ids.name', 'ilike', word),
                ]).sorted(key=lambda p: (p.child_ids.filtered(lambda c: c.type == 'visit').mapped('city'), p.brand_name))
            return res

        words = post.get('search_resellers')
        if words and words != '':
            all_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', '')], ['id'])]
            domain = [('is_company', '=', True), ('is_reseller', '=', True), ('child_ids.type', '=', 'visit'), ('child_competence_ids', '=', competence.id)]
            resellers = self.get_resellers(words, domain, search_partner_name, params={'all_visit_ids': all_visit_ids})
            if len(resellers) < 100:
                matched_reseller_ids = resellers.mapped('id')
                resellers += self.get_resellers(
                        words,
                        domain + [('id', 'not in', matched_reseller_ids)],
                        search_partner,
                        params={'all_visit_ids': all_visit_ids},
                        webshop=False,
                        limit=100 - len(resellers))
            return request.website.render('reseller_dermanord.resellers', {
                'competence': competence,
                'search_resellers': words,
                'resellers': resellers,
                'placeholder': ''
            })
        else:
            matching_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', '')], ['id'])]
            domain = [('is_company', '=', True), ('is_reseller', '=', True), ('child_ids', 'in', matching_visit_ids), ('child_competence_ids', '=', competence.id)]
            if request.session.get('geoip') and request.session.get('geoip', {}).get('longitude') and request.session.get('geoip', {}).get('latitude'): # Geo search
                return request.website.render('reseller_dermanord.resellers', {
                    'competence': competence,
                    'search_resellers': '',
                    'resellers': self.get_resellers_without_keyword(domain, tuple((float(request.session.get('geoip').get('longitude')), float(request.session.get('geoip').get('latitude')))), limit=100),
                    'placeholder': _('<i class="fa fa-map-marker"></i> <span style="padding-left: 5px;">My position</span>')
                })
        return request.website.render('reseller_dermanord.resellers', {'competence': competence, 'resellers': [], 'placeholder': _('<span>Search...</span>')})

    @http.route(['/resellers'], type='http', auth="public", website=True)
    def reseller(self, country=None, city='', competence=None, **post):
        partner_obj = request.env['res.partner']
        
        def search_partner_name(word, all_visit_ids):
            return partner_obj.sudo().search([
                ('is_company', '=', True),
                ('is_reseller', '=', True),
                ('child_ids', 'in', all_visit_ids),
                '|', '|',
                    ('child_category_ids.name', 'ilike', word),
                    ('brand_name', 'ilike', word),
                    '&',
                        ('name', 'ilike', word),
                        ('brand_name', '=', False),
                ], limit=100).sorted(key=lambda p: (p.child_ids.filtered(lambda c: c.type == 'visit').mapped('city'), p.brand_name))
        
        def search_partner(word, all_visit_ids):
            matching_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', ''), '|', ('street', 'ilike', word), '|', ('street2', 'ilike', word), '|', ('zip', 'ilike', word), '|', ('state_id.name', 'ilike', word), ('country_id.name', 'ilike', word)], ['id'])]
            res = partner_obj.sudo().search([
                ('is_company', '=', True),
                ('is_reseller', '=', True),
                ('child_ids', 'in', all_visit_ids),
                '|',
                    ('child_ids', 'in', matching_visit_ids),
                    ('child_category_ids.name', 'ilike', word)
                ]).sorted(key=lambda p: (p.child_ids.filtered(lambda c: c.type == 'visit').mapped('city'), p.brand_name))
            return res
        
        all_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', '')], ['id'])]
        domain = [('is_company', '=', True), ('is_reseller', '=', True), ('child_ids', 'in', all_visit_ids)]
        words = post.get('search_resellers')
        resellers = self.get_resellers(words, domain, search_partner_name, params={'all_visit_ids': all_visit_ids}, limit=30)
        if len(resellers) < 30:
            matched_reseller_ids = resellers.mapped('id')
            resellers += self.get_resellers(
                words,
                domain + [('id', 'not in', matched_reseller_ids)],
                search_partner,
                params={'all_visit_ids': all_visit_ids},
                webshop=False,
                limit=30 - len(resellers))
        return request.website.render('reseller_dermanord.resellers', {'resellers': resellers, 'search_resellers': words, 'placeholder': '<span>Search...</span>'})
        
    @http.route(['/reseller/<int:partner_id>',], type='http', auth="public", website=True)
    def reseller_page(self, partner_id=None, **post):
        partner = request.env['res.partner'].sudo().search([('id', '=', partner_id), ('is_reseller', '=', True), ('child_ids.type', '=', 'visit')])
        return request.website.render('reseller_dermanord.reseller', {
            'reseller': partner,
        })

    @http.route(['/website_set_location'], type='json', auth="public", website=True)
    def website_set_location(self, longitude, latitude, **kwags):
        geoip = request.session.get('geoip', {})
        if geoip.get('longitude') and geoip.get('latitude'):
            if abs(longitude - geoip.get('longitude')) > 0.001 or abs(latitude - geoip.get('latitude')) > 0.001:
                geoip['longitude'] = longitude
                geoip['latitude'] = latitude
                request.session['geoip'] = geoip
        else:
            geoip['longitude'] = longitude
            geoip['latitude'] = latitude
            request.session['geoip'] = geoip

        #~ if partner:
            #~ return request.website.render('reseller_dermanord.reseller', {
                #~ 'reseller': partner,
                #~ 'country_ids': sorted(list(set(reseller_all.mapped('country_id')))),
                #~ 'city_ids': sorted([c.strip() for c in list(set(reseller_all.mapped('city')))]),
                #~ 'competence_ids': reseller_all.mapped('child_category_ids'),
                #~ 'assortment_ids': reseller_all.mapped('category_id'),
                #~ 'reseller_footer': True,
            #~ })
        #~ word = post.get('search', False)
        #~ domain = []
        #~ domain += self.get_reseller_domain_append(post)
        #~ order = ''
        #~ if post.get('post_form') and post.get('post_form') == 'ok':
            #~ request.session['form_values'] = post
            #~ order = post.get('order', '')
        #~ view = post.get('view')
        #~ if not request.session.get('form_values'):
            #~ request.session['form_values'] = {}
        #~ request.session['form_values']['view'] = view
        #~ if country:
            #~ domain.append(('country_id', '=', country.id))
            #~ post['country_%s' %country.id] = str(country.id)
            #~ request.session['form_values']['country_%s' %country.id] = str(country.id)
        #~ if competence:
            #~ domain.append(('child_category_ids', 'in', competence.id))
            #~ post['competence_%s' %competence.id] = str(competence.id)
            #~ request.session['form_values']['competence_%s' %competence.id] = str(competence.id)

        #~ if word and word != '':
            #~ partners.filtered(lambda p: p.name in word)
        #~ request.session['chosen_filter_qty'] = self.get_reseller_chosen_filter_qty(self.get_reseller_form_values())
        #~ request.session['sort_name'] = self.get_reseller_chosen_order(self.get_reseller_form_values())[0]
        #~ request.session['sort_order'] = self.get_reseller_chosen_order(self.get_reseller_form_values())[1]

        #~ marker_tmp = """var marker%s = new google.maps.Marker({
                        #~ title: '%s',
                        #~ position: {lat: %s, lng: %s},
                        #~ map: map,
                        #~ icon: 'http://wiggum.vertel.se/dn_maps_marker.png'
                    #~ });
                    #~ """

        #~ partners = request.env['res.partner'].sudo().search(domain, limit=20, order=order)
        #~ res = []
        #~ for partner in partners:
            #~ pos = partner.get_position()
            #~ res.append(marker_tmp %(partner.id, partner.name.replace("'", ''), pos['lat'], pos['lng']))

        #~ if view == 'city':
            #~ cities = []
            #~ if city == '':
                #~ cities = partners.mapped('city')
            #~ else:
                #~ for k,v in request.session['form_values']:
                    #~ if 'city_' in k:
                        #~ cities.append(v)
            #~ return request.website.render('reseller_dermanord.resellers_city', {
                #~ 'resellers': partners,
                #~ 'cities': sorted([c.strip() for c in list(set(cities))]),
                #~ 'country_ids': sorted(list(set(reseller_all.mapped('country_id')))),
                #~ 'city_ids': sorted([c.strip() for c in list(set(reseller_all.mapped('city')))]),
                #~ 'competence_ids': reseller_all.mapped('child_category_ids'),
                #~ 'assortment_ids': reseller_all.mapped('category_id'),
                #~ 'reseller_footer': True,
            #~ })
        #~ if view == 'country':
            #~ country_ids = partners.mapped('country_id')
            #~ return request.website.render('reseller_dermanord.resellers_country', {
                #~ 'resellers': partners,
                #~ 'countries': sorted(list(set(country_ids))),
                #~ 'country_ids': sorted(list(set(reseller_all.mapped('country_id')))),
                #~ 'city_ids': sorted([c.strip() for c in list(set(reseller_all.mapped('city')))]),
                #~ 'competence_ids': reseller_all.mapped('child_category_ids'),
                #~ 'assortment_ids': reseller_all.mapped('category_id'),
                #~ 'reseller_footer': True,
            #~ })
        #~ return request.website.render('reseller_dermanord.resellers', {
            #~ 'resellers': partners,
            #~ 'resellers_geo': res,
            #~ 'country_ids': sorted(list(set(reseller_all.mapped('country_id')))),
            #~ 'city_ids': sorted([c.strip() for c in list(set(reseller_all.mapped('city')))]),
            #~ 'competence_ids': reseller_all.mapped('child_category_ids'),
            #~ 'assortment_ids': reseller_all.mapped('category_id'),
            #~ 'reseller_footer': True,
        #~ })


class website_sale_home(website_sale_home):

    def get_help(self):
        res = super(website_sale_home, self).get_help()
        res['help_visit_street'] = _("If the street is not filled in, your salon will not appear in reseller searching.")
        res['help_top_image_size'] = _("Notice: This image will be cut to 1366x450 px.")
        return res

    def get_address_type(self):
        res = super(website_sale_home, self).get_address_type()
        res.append('visit')
        return res

    def get_address_types_readonly(self):
        return ['delivery', 'invoice']

    def get_children_by_address_type(self, company):
        res = super(website_sale_home, self).get_children_by_address_type(company)
        res.update({'visit': company.child_ids.filtered(lambda c: c.type == 'visit')[0] if company.child_ids.filtered(lambda c: c.type == 'visit') else None})
        return res

    @http.route(['/home/<model("res.users"):home_user>/info_update',], type='http', auth="user", website=True)
    def info_update(self, home_user=None, **post):
        # update data for main partner
        self.validate_user(home_user)
        if home_user == request.env.user:
            home_user = home_user.sudo()
        #~ home_user.email = post.get('email')
        #~ home_user.login = post.get('login')
        if post.get('confirm_password'):
            home_user.password = post.get('password')
        if home_user.partner_id.commercial_partner_id.is_reseller:
            commercial_partner = home_user.partner_id.commercial_partner_id
            commercial_partner.brand_name = post.get('brand_name')
            commercial_partner.website_short_description = post.get('website_short_description')
            if post.get('top_image'):
                commercial_partner.top_image = base64.encodestring(post.get('top_image').read())
            for weekday in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                self.update_opening_weekday(commercial_partner, weekday, post)
            if post.get('opening_hours_exceptions') != None and post.get('opening_hours_exceptions') != commercial_partner.opening_hours_exceptions:
                commercial_partner.opening_hours_exceptions = post.get('opening_hours_exceptions')
        self.update_info(home_user, post)
        return werkzeug.utils.redirect("/home/%s" % home_user.id)

    def update_opening_weekday(self, partner, weekday, post):
        day = partner.opening_hours_ids.filtered(lambda o: o.dayofweek == weekday)
        if not day:
            day = request.env['opening.hours'].sudo().create({'partner_id': partner.id, 'dayofweek': weekday})
        day.open_time = self.get_time_float(post.get('%s_open_time' %weekday) or '0.0')
        day.close_time = self.get_time_float(post.get('%s_close_time' %weekday) or '0.0')
        day.break_start = self.get_time_float(post.get('%s_break_start' %weekday) or '0.0')
        day.break_stop = self.get_time_float(post.get('%s_break_stop' %weekday) or '0.0')
        day.close = True if post.get('%s_close' %weekday) == '1' else False

    def update_info(self, home_user, post):
        res = super(website_sale_home, self).update_info(home_user, post)
        # create a visit partner if doesn't exist
        self.update_visit(home_user, post)
        categories = request.env['product.public.category'].search([('id', 'in', [int(i) for i in request.httprequest.form.getlist('webshop_category_ids')]), ('website_published', '=', True)])
        if categories and (categories != home_user.partner_id.commercial_partner_id.webshop_category_ids):
            home_user.partner_id.commercial_partner_id.webshop_category_ids = categories
        return res

    def update_visit(self, home_user, post):
        if post.get('visit_street') or post.get('visit_street2') or post.get('visit_email') or post.get('visit_city') or post.get('visit_phone') or post.get('visit_zip'):
            visit = home_user.partner_id.commercial_partner_id.child_ids.filtered(lambda c: c.type == 'visit')
            if not visit:
                request.env['res.partner'].sudo().create({
                    'name': _('visit'),
                    'parent_id': home_user.partner_id.commercial_partner_id.id,
                    'type': 'visit',
                    'street': post.get('visit_street', ''),
                    'street2': post.get('visit_street2', ''),
                    'zip': post.get('visit_zip', ''),
                    'city': post.get('visit_city', ''),
                    'country_id': int(post.get('visit_country_id')) if post.get('visit_country_id') else 0,
                    'email': post.get('visit_email', ''),
                    'phone': post.get('visit_phone', ''),
                })
            else:
                visit[0].sudo().write({
                    'name': _('visit'),
                    'type': 'visit',
                    'street': post.get('visit_street', ''),
                    'street2': post.get('visit_street2', ''),
                    'zip': post.get('visit_zip', ''),
                    'city': post.get('visit_city', ''),
                    'country_id': int(post.get('visit_country_id')) if post.get('visit_country_id') else 0,
                    'email': post.get('visit_email', ''),
                    'phone': post.get('visit_phone', ''),
                })
            visit.geo_localize() # update geo location
            visit.commercial_partner_id.geo_localize() # update geo location

    def get_time_float(self, time):
        return (math.floor(float(time)) + (float(time)%1)/0.6) if time else 0.0

    @http.route(['/remove_img',], type='json', auth="public", website=True)
    def remove_img(self, partner_id='0', **kw):
        partner = request.env['res.partner'].sudo().browse(int(partner_id))
        if partner:
            partner.write({'top_image': None})
            return True
        return False

class website(models.Model):
    _inherit = 'website'

    @api.model
    def get_float_time(self, time):
        return ("%.2f" %(math.floor(float(time)) + (float(time)%1)*0.6)) if time else 0.0

    def sale_home_get_data(self, home_user, post):
        values = super(website, self).sale_home_get_data(home_user, post)
        values['webshop_category_ids'] = [(category['id'], category['name']) for category in request.env['product.public.category'].search_read([('website_published', '=', True), ('parent_id', '=', False), ('id', 'not in', [1])], ['name'])]
        # id 1 är Ovrigt
        return values
