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
        _logger.warn(len(resellers))
        res = resellers.sorted(key=lambda p: p.child_ids.filtered(lambda c: c.type == 'visit').city)
        _logger.warn(len(res))
        return res

    # Return result of resellers with postcode, domain searching
    def get_resellers(self, words, domain, search_partner, webshop=False):
        partner_obj = request.env['res.partner']
        # Split words and try to get postcode first
        word_list = words.split(' ')
        partner_ids = []
        post_codes = []
        strings = []
        limit = 5 if webshop else 10
        found = False
        for i in range(len(word_list)):
            if len(word_list[i]) == 3 and word_list[i].isdigit():
                found = True
                continue
            elif found and len(word_list[i]) == 2 and word_list[i].isdigit():
                post_codes.append('%s%s' %(word_list[i-1], word_list[i]))
            found = False
        resellers = partner_obj.sudo().browse()
        for w in word_list:
            if len(w) == 5 and w.isdigit():
                # Got a keyword is postcode
                post_codes.append(w)
            else:
                # Got a keyword is not postcode
                strings.append(w)
        if len(post_codes) > 0:
            # Search each postcode and get the closest reseller inside 0.5 degree
            for p in post_codes:
                partner_ids += partner_obj.sudo().geo_zip_search('position', 'SE', '%s %s' %(p[:3], p[3:]), domain + [('partner_latitude', '!=', 0.0), ('partner_longitude', '!=', 0.0)], distance=360, limit=limit) # this suppose to be a limited distance
        if not partner_ids:
            for s in strings:
                partner_ids += partner_obj.sudo().geo_city_search('position', 'SE', s, domain + [('partner_latitude', '!=', 0.0), ('partner_longitude', '!=', 0.0)], distance=360, limit=limit)
            # Search keyword
            for s in strings:
                resellers |= search_partner(s)
            if len(partner_ids) > 0:
                resellers = partner_obj.sudo().browse(partner_ids).with_context(resellers=resellers.mapped('id')).filtered(lambda r: r.id in r._context.get('resellers'))
                if len(resellers) == 0:
                    resellers = partner_obj.sudo().browse(partner_ids)
        # If there's no reseller found. Redo search with unlimited distance
        if len(resellers) == 0:
            partner_ids = []
            if len(post_codes) > 0:
                for p in post_codes:
                    partner_ids += partner_obj.sudo().geo_zip_search('position', 'SE', '%s %s' %(p[:3], p[3:]), domain, distance=360, limit=3)
                if len(partner_ids) > 0:
                    if len(partner_ids) > 3:
                        partner_ids = partner_ids[:3]
                    resellers = partner_obj.sudo().browse(partner_ids)
        return resellers

    def get_resellers_without_keyword(self, domain, position, distance=None, limit=10, webshop=False):
        partner_obj = request.env['res.partner']
        def get_partner_ids(d, l):
            return partner_obj.sudo().geo_search('position', position, domain + [('partner_latitude', '!=', 0.0), ('partner_longitude', '!=', 0.0)], distance=d, limit=l)
        if webshop:
            # ~ partner_ids = get_partner_ids(0.5, 5)
            # ~ if len(partner_ids) == 0:
            partner_ids = get_partner_ids(360, 5)
        else:
            # ~ partner_ids = get_partner_ids(0.5, 10)
            # ~ if len(partner_ids) == 0:
            partner_ids = get_partner_ids(360, 10)
        if len(partner_ids) > 0:
            return partner_obj.sudo().browse(partner_ids)
        else:
            return partner_obj.sudo().browse()

    @http.route(['/resellers/competence/<model("res.partner.category"):competence>',], type='http', auth="public", website=True)
    def reseller_competence(self, competence, **post):
        partner_obj = request.env['res.partner']
        context = {'competence': competence}
        def search_partner(word):
            # Find all matching visit addresses
            matching_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', ''), '|', ('street', 'ilike', word), '|', ('street2', 'ilike', word), '|', ('city', 'ilike', word), '|', ('state_id.name', 'ilike', word), ('country_id.name', 'ilike', word)], ['id'])]
            all_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', '')], ['id'])]
            res = partner_obj.sudo().search([
                ('is_company', '=', True),
                ('is_reseller', '=', True),
                ('child_ids.type', '=', 'visit'),
                ('child_ids', 'in', all_visit_ids),
                ('child_competence_ids', '=', competence.id),
                '|', '|', '|', '|',
                    ('child_ids', 'in', matching_visit_ids),
                    ('child_category_ids.name', 'ilike', word),
                    ('child_competence_ids.name', 'ilike', word),
                    ('brand_name', 'ilike', word),
                    '&',
                        ('name', 'ilike', word),
                        ('brand_name', '=', False),
                    ]).sorted(key=lambda p: (p.child_ids.filtered(lambda c: c.type == 'visit').mapped('city'), p.brand_name))
            return res

        words = post.get('search_resellers')
        if words and words != '':
            context['resellers'] = self.get_resellers(words, [('is_company', '=', True), ('is_reseller', '=', True), ('child_ids.type', '=', 'visit'), ('child_competence_ids', '=', competence.id)], search_partner)
        else:
            matching_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', '')], ['id'])]
            context['resellers'] = partner_obj.sudo().search([
                ('is_company', '=', True),
                ('is_reseller', '=', True),
                ('child_ids', 'in', matching_visit_ids),
                ('child_competence_ids', '=', competence.id)]).sorted(key=lambda p: (p.child_ids.filtered(lambda c: c.type == 'visit').mapped('city'), p.brand_name))
        return request.website.render('reseller_dermanord.resellers', context)

    @http.route([
        '/resellers',
        #~ '/resellers/country/<model("res.country"):country>',
        #~ '/resellers/city/<string:city>',
        #~ '/resellers/competence/<model("res.partner.category"):competence>',
        '/reseller/<int:partner>',
    ], type='http', auth="public", website=True)
    def reseller(self, partner=None, country=None, city='', competence=None, **post):
        partner_obj = request.env['res.partner']
        def search_partner(word):
            # Find all matching visit addresses
            matching_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', ''), '|', ('street', 'ilike', word), '|', ('street2', 'ilike', word), '|', ('city', 'ilike', word), '|', ('state_id.name', 'ilike', word), ('country_id.name', 'ilike', word)], ['id'])]
            all_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', '')], ['id'])]
            # Find (partners that have a matching visit address OR brand name OR child category)
            res = partner_obj.sudo().search([
                ('is_company', '=', True),
                ('is_reseller', '=', True),
                ('child_ids.type', '=', 'visit'),
                ('child_ids', 'in', all_visit_ids),
                '|', '|', '|',
                    ('child_ids', 'in', matching_visit_ids),
                    ('child_category_ids.name', 'ilike', word),
                    ('brand_name', 'ilike', word),
                    '&',
                        ('name', 'ilike', word),
                        ('brand_name', '=', False),
                    ]).sorted(key=lambda p: (p.child_ids.filtered(lambda c: c.type == 'visit').mapped('city'), p.brand_name))
            return res

        if not partner:
            words = post.get('search_resellers')
            if words and words != '':
                resellers = self.get_resellers(words, [('is_company', '=', True), ('is_reseller', '=', True), ('child_ids.type', '=', 'visit')], search_partner)
                return request.website.render('reseller_dermanord.resellers', {'resellers': resellers})
            else:
                # ~ closest_ids = partner_obj.geoip_search('position', request.httprequest.remote_addr, 10)
                # ~ resellers = partner_obj.sudo().search([('is_reseller', '=', True), ('child_ids.type', '=', 'visit')])
                return request.website.render('reseller_dermanord.resellers', {'resellers': []})
        else:
            partner = partner_obj.sudo().search([('id', '=', int(partner)), ('is_reseller', '=', True), ('child_ids.type', '=', 'visit')])
            return request.website.render('reseller_dermanord.reseller', {
                'reseller': partner,
            })

    @http.route(['/resellers/search/<model("product.product"):product>'], type='http', auth="public", website=True)
    def resellers_search(self, product, **post):
        partner_obj = request.env['res.partner']
        has_webshop = post.get('has_webshop', False)
        all_parent_categories = []
        def get_all_parent_categories(category):
            if category.id not in all_parent_categories:
                all_parent_categories.append(category.id)
            if category.parent_id:
                get_all_parent_categories(category.parent_id)
            else:
                if category.id not in all_parent_categories:
                    all_parent_categories.append(category.id)
        for c in product.public_categ_ids:
            get_all_parent_categories(c)
        def search_partner(word):
            matching_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', ''), '|', ('street', 'ilike', word), '|', ('street2', 'ilike', word), '|', ('city', 'ilike', word), '|', ('zip', 'ilike', word), '|', ('state_id.name', 'ilike', word), ('country_id.name', 'ilike', word)], ['id'])]
            if has_webshop and has_webshop == 'has_webshop':
                res = partner_obj.sudo().search([
                    ('is_company', '=', True),
                    ('is_reseller', '=', True),
                    ('has_webshop', '=', True),
                    ('webshop_website', '!=', ''),
                    ('webshop_category_ids', 'in', all_parent_categories),
                    ('child_ids.type', '=', 'visit'),
                    ('child_ids', 'in', all_visit_ids),
                    '|', '|', '|',
                        ('child_ids', 'in', matching_visit_ids),
                        ('child_category_ids.name', 'ilike', word),
                        ('brand_name', 'ilike', word),
                        '&',
                            ('name', 'ilike', word),
                            ('brand_name', '=', False),
                        ]).sorted(key=lambda p: (p.child_ids.filtered(lambda c: c.type == 'visit').mapped('city'), p.brand_name))
            else:
                res = partner_obj.sudo().search([
                    ('is_company', '=', True),
                    ('is_reseller', '=', True),
                    ('webshop_category_ids', 'in', all_parent_categories),
                    ('child_ids.type', '=', 'visit'),
                    ('child_ids', 'in', all_visit_ids),
                    '|', '|', '|',
                        ('child_ids', 'in', matching_visit_ids),
                        ('child_category_ids.name', 'ilike', word),
                        ('brand_name', 'ilike', word),
                        '&',
                            ('name', 'ilike', word),
                            ('brand_name', '=', False),
                        ]).sorted(key=lambda p: (p.child_ids.filtered(lambda c: c.type == 'visit').mapped('city'), p.brand_name))
            return res

        words = post.get('search_resellers')
        if product:
            all_visit_ids = [p['id'] for p in partner_obj.sudo().search_read([('type', '=', 'visit'), ('street', '!=', '')], ['id'])]
            domain = [
                ('is_company', '=', True),
                ('is_reseller', '=', True),
                ('webshop_category_ids', 'in', all_parent_categories),
                ('child_ids.type', '=', 'visit'),
                ('child_ids', 'in', all_visit_ids),
            ]
            if has_webshop and has_webshop == 'has_webshop':
                domain += [('has_webshop', '=', True), ('webshop_website', '!=', '')]
            if words and words != '':
                if has_webshop and has_webshop == 'has_webshop':
                    resellers = self.get_resellers(words, domain, search_partner, webshop=True)
                else:
                    resellers = self.get_resellers(words, domain, search_partner, webshop=False)
                return request.website.render('reseller_dermanord.resellers_search_cosumer', {'resellers': resellers, 'product': product, 'has_webshop': has_webshop, 'not_found_msg': _('No reseller found') if len(resellers) == 0 else '', 'input': words})
            else: # without searching term, geo/IP search
                if request.session.get('geoip') and request.session.get('geoip', {}).get('longitude') and request.session.get('geoip', {}).get('latitude'): # Geo search
                    resellers = self.get_resellers_without_keyword(domain, tuple((float(request.session.get('geoip').get('longitude')), float(request.session.get('geoip').get('latitude')))), webshop=True if has_webshop == 'has_webshop' else False)
                else:
                    resellers = partner_obj.browse()
                # ~ resellers = partner_obj.sudo().browse(partner_obj.sudo().geoip_search('position', request.httprequest.remote_addr, domain))
                return request.website.render('reseller_dermanord.resellers_search_cosumer', {'resellers': resellers, 'product': product, 'has_webshop': has_webshop, 'not_found_msg': _('No reseller found') if len(resellers) == 0 else '', 'placeholder': '*'})
        return request.website.render('reseller_dermanord.resellers_search_cosumer', {'resellers': [], 'product': product})

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
