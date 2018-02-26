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
    top_image = fields.Binary(string='Top Image')
    type = fields.Selection(selection_add=[('visit', 'Visit')])

    #~ @api.one
    #~ def _is_reseller(self):
        #~ self.is_reseller = self.env['ir.model.data'].xmlid_to_object('reseller_dermanord.reseller_tag') in self.category_id

    #~ @api.model
    #~ def _search_is_reseller(self, operator, value):
        #~ resellers = self.env.search([('category_id', '=', self.env['ir.model.data'].xmlid_to_object('reseller_dermanord.reseller_tag').id)])
        #~ return [('id', 'in', [r.id for r in resellers])]

    @api.multi
    def get_position(self):
        #~ url = ''
        #~ if not self.partner_latitude and (self.street or self.street2):
            #~ url = u'https://maps.googleapis.com/maps/api/geocode/json?address=%s,%s,%s,%s' %(self.street if (self.street and not self.street2) else self.street2, self.zip, self.city, self.country_id.name)
            #~ try:
                #~ geo_info = urllib.urlopen(url.encode('ascii', 'xmlcharrefreplace')).read()
                #~ geo = json.loads(geo_info)
                #~ result = geo.get('results')
                #~ if len(result) > 0:
                    #~ geometry = result[0].get("geometry")
                    #~ if geometry:
                        #~ self.partner_latitude = geometry["location"]["lat"]
                        #~ self.partner_longitude = geometry["location"]["lng"]
            #~ except ValueError as e:
                #~ _logger.error(e)
        if self.partner_latitude == 0.0 and self.partner_longitude == 0.0:
            self.geo_localize()
        return {'lat': self.partner_latitude, "lng": self.partner_longitude}

    @api.multi
    def searchable_reseller(self):
        # is company and customer
        # has tag Hudterapeut eller SPA-terapeut, and has purchased more than 10000SEK(ex.moms) in last 12 months.
        # has other tags and purchase more than 2000SEK(ex.moms) once in last 12 months.
        self.is_reseller = False
        if (self.env['res.partner.category'].search([('name', '=', 'Hudterapeut')])[0] in self.category_id) or (self.env['res.partner.category'].search([('name', '=', 'SPA-Terapeut')])[0] in self.category_id):
            if sum(self.env['account.invoice'].search(['|', ('partner_id', '=', self.id), ('partner_id.child_ids', '=', self.id), ('date_invoice', '>=', fields.Date.to_string((date.today()-relativedelta(years=1))))]).mapped('amount_untaxed')) >= 10000.0:
                self.is_reseller = True
        else:
            if sum(self.env['account.invoice'].search(
                    ['|', ('partner_id', '=', self.id), ('partner_id.child_ids', '=', self.id), ('date_invoice', '>=', fields.Date.to_string((date.today()-relativedelta(years=1))))]
                    ).mapped('amount_untaxed')) > 2000.0:
                self.is_reseller = True

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

    @http.route(['/resellers/competence/<model("res.partner.category"):competence>',], type='http', auth="public", website=True)
    def reseller_competence(self, competence, **post):
        context = {'competence': competence}
        word = post.get('search')
        if word:
            context['resellers'] = request.env['res.partner'].sudo().search([
                ('is_reseller', '=', True),
                ('child_competence_ids', '=', competence.id),
                '|', ('name', 'ilike', word),
                '|', ('brand_name', 'ilike', word),
                '|', ('city', 'ilike', word),
                '|', ('state_id.name', 'ilike', word),
                '|', ('country_id.name', 'ilike', word),
                ('child_competence_ids.name', 'ilike', word)])
        else:
            context['resellers'] = request.env['res.partner'].sudo().search([
                ('is_reseller', '=', True),
                ('child_competence_ids', '=', competence.id)])
        return request.website.render('reseller_dermanord.resellers', context)

    @http.route([
        '/resellers',
        #~ '/resellers/country/<model("res.country"):country>',
        #~ '/resellers/city/<string:city>',
        #~ '/resellers/competence/<model("res.partner.category"):competence>',
        '/reseller/<int:partner>',
    ], type='http', auth="public", website=True)
    def reseller(self, partner=None, country=None, city='', competence=None, **post):
        if not partner:
            word = post.get('search', False)
            if word and word != '':
                resellers = request.env['res.partner'].sudo().search(['&', ('is_reseller', '=', True), '|', ('name', 'ilike', word), '|', ('brand_name', 'ilike', word), '|', ('city', 'ilike', word), '|', ('state_id.name', 'ilike', word), '|', ('country_id.name', 'ilike', word), ('child_category_ids.name', 'ilike', word)])
                return request.website.render('reseller_dermanord.resellers', {'resellers': resellers})
            else:
                closest_ids = request.env['res.partner'].geoip_search('position', request.httprequest.remote_addr, 10)
                resellers = request.env['res.partner'].sudo().search(['&', ('is_reseller', '=', True), ('id', 'in', closest_ids)])
                return request.website.render('reseller_dermanord.resellers', {'resellers': resellers})
        else:
            partner = request.env['res.partner'].sudo().browse(int(partner))
            return request.website.render('reseller_dermanord.reseller', {
                'reseller': partner,
            })

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

    @http.route(['/home/<model("res.users"):home_user>/info_update',], type='http', auth="user", website=True)
    def info_update(self, home_user=None, **post):
        # update data for main partner
        self.validate_user(home_user)
        if home_user == request.env.user:
            home_user = home_user.sudo()
        home_user.email = post.get('email')
        home_user.login = post.get('login')
        if post.get('confirm_password'):
            home_user.password = post.get('password')
        if home_user.partner_id.commercial_partner_id.is_reseller:
            commercial_partner = home_user.partner_id.commercial_partner_id
            commercial_partner.brand_name = post.get('brand_name')
            commercial_partner.website_short_description = post.get('website_short_description')
            if post.get('top_image'):
                commercial_partner.top_image = base64.encodestring(post.get('top_image').read())
            if post.get('monday_open_time'):

                monday = commercial_partner.opening_hours_ids.filtered(lambda o: o.dayofweek == 'monday')
                if not monday:
                    monday = request.env['opening.hours'].create({'partner_id': commercial_partner.id, 'dayofweek': 'monday'})
                monday.open_time = self.get_time_float(post.get('monday_open_time') or '0.0')
                monday.close_time = self.get_time_float(post.get('monday_close_time') or '0.0')
                monday.break_start = self.get_time_float(post.get('monday_break_start') or '0.0')
                monday.break_stop = self.get_time_float(post.get('monday_break_stop') or '0.0')
                monday.close = True if post.get('monday_close') == '1' else False

                tuesday = commercial_partner.opening_hours_ids.filtered(lambda o: o.dayofweek == 'tuesday')
                if not tuesday:
                    tuesday = request.env['opening.hours'].create({'partner_id': commercial_partner.id, 'dayofweek': 'tuesday'})
                tuesday.open_time = self.get_time_float(post.get('tuesday_open_time') or '0.0')
                tuesday.close_time = self.get_time_float(post.get('tuesday_close_time') or '0.0')
                tuesday.break_start = self.get_time_float(post.get('tuesday_break_start') or '0.0')
                tuesday.break_stop = self.get_time_float(post.get('tuesday_break_stop') or '0.0')
                tuesday.close = True if post.get('tuesday_close') == '1' else False

                wednesday = commercial_partner.opening_hours_ids.filtered(lambda o: o.dayofweek == 'wednesday')
                if not wednesday:
                    wednesday = request.env['opening.hours'].create({'partner_id': commercial_partner.id, 'dayofweek': 'wednesday'})
                wednesday.open_time = self.get_time_float(post.get('wednesday_open_time') or '0.0')
                wednesday.close_time = self.get_time_float(post.get('wednesday_close_time') or '0.0')
                wednesday.break_start = self.get_time_float(post.get('wednesday_break_start') or '0.0')
                wednesday.break_stop = self.get_time_float(post.get('wednesday_break_stop') or '0.0')
                wednesday.close = True if post.get('wednesday_close') == '1' else False

                thursday = commercial_partner.opening_hours_ids.filtered(lambda o: o.dayofweek == 'thursday')
                if not thursday:
                    thursday = request.env['opening.hours'].create({'partner_id': commercial_partner.id, 'dayofweek': 'thursday'})
                thursday.open_time = self.get_time_float(post.get('thursday_open_time') or '0.0')
                thursday.close_time = self.get_time_float(post.get('thursday_close_time') or '0.0')
                thursday.break_start = self.get_time_float(post.get('thursday_break_start') or '0.0')
                thursday.break_stop = self.get_time_float(post.get('thursday_break_stop') or '0.0')
                thursday.close = True if post.get('thursday_close') == '1' else False

                friday = commercial_partner.opening_hours_ids.filtered(lambda o: o.dayofweek == 'friday')
                if not friday:
                    friday = request.env['opening.hours'].create({'partner_id': commercial_partner.id, 'dayofweek': 'friday'})
                friday.open_time = self.get_time_float(post.get('friday_open_time') or '0.0')
                friday.close_time = self.get_time_float(post.get('friday_close_time') or '0.0')
                friday.break_start = self.get_time_float(post.get('friday_break_start') or '0.0')
                friday.break_stop = self.get_time_float(post.get('friday_break_stop') or '0.0')
                friday.close = True if post.get('friday_close') == '1' else False

                saturday = commercial_partner.opening_hours_ids.filtered(lambda o: o.dayofweek == 'saturday')
                if not saturday:
                    saturday = request.env['opening.hours'].create({'partner_id': commercial_partner.id, 'dayofweek': 'saturday'})
                saturday.open_time = self.get_time_float(post.get('saturday_open_time') or '0.0')
                saturday.close_time = self.get_time_float(post.get('saturday_close_time') or '0.0')
                saturday.break_start = self.get_time_float(post.get('saturday_break_start') or '0.0')
                saturday.break_stop = self.get_time_float(post.get('saturday_break_stop') or '0.0')
                saturday.close = True if post.get('saturday_close') == '1' else False

                sunday = commercial_partner.opening_hours_ids.filtered(lambda o: o.dayofweek == 'sunday')
                if not sunday:
                    sunday = request.env['opening.hours'].create({'partner_id': commercial_partner.id, 'dayofweek': 'sunday'})
                sunday.open_time = self.get_time_float(post.get('sunday_open_time') or '0.0')
                sunday.close_time = self.get_time_float(post.get('sunday_close_time') or '0.0')
                sunday.break_start = self.get_time_float(post.get('sunday_break_start') or '0.0')
                sunday.break_stop = self.get_time_float(post.get('sunday_break_stop') or '0.0')
                sunday.close = True if post.get('sunday_close') == '1' else False


        return werkzeug.utils.redirect("/home/%s" % home_user.id)

    def get_time_float(self, time):
        return (math.floor(float(time)) + (float(time)%1)/0.6) if time else 0.0


class website(models.Model):
    _inherit = 'website'

    @api.model
    def get_float_time(self, time):
        return ("%.2f" %(math.floor(float(time)) + (float(time)%1)*0.6)) if time else 0.0
