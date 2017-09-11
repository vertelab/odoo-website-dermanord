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

import logging
_logger = logging.getLogger(__name__)

class res_partner(models.Model):
    _inherit = 'res.partner'

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
        domain_append += [('category_id', 'in', request.env.ref('reseller_dermanord.reseller_tag').id)]
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
            if k not in ['post_form', 'order', 'webshop']:
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

    @http.route(['/resellers'], type='http', auth="public", website=True)
    def reseller(self, **post):
        word = post.get('search', False)
        domain = []
        domain += self.get_reseller_domain_append(post)
        order = ''
        if post.get('post_form') and post.get('post_form') == 'ok':
            request.session['form_values'] = post
            order = post.get('order', '')
        partners = request.env['res.partner'].sudo().search(domain, limit=20, order=order)
        if word and word != '':
            partners.filtered(lambda p: p.name in word)
        request.session['chosen_filter_qty'] = self.get_reseller_chosen_filter_qty(self.get_reseller_form_values())
        request.session['sort_name'] = self.get_reseller_chosen_order(self.get_reseller_form_values())[0]
        request.session['sort_order'] = self.get_reseller_chosen_order(self.get_reseller_form_values())[1]

        marker_tmp = """var marker%s = new google.maps.Marker({
                        title: '%s',
                        position: {lat: %s, lng: %s},
                        map: map,
                        icon: 'http://wiggum.vertel.se/dn_maps_marker.png'
                    });
                    """
        res = []
        for partner in partners:
            pos = partner.get_position()
            res.append(marker_tmp %(partner.id, partner.name.replace("'", ''), pos['lat'], pos['lng']))

        return request.website.render('reseller_dermanord.resellers', {
            'resellers': partners,
            'reseller_footer': True,
            'resellers_geo': res,
        })

    @http.route(['/reseller/<model("res.partner"):partner>'], type='http', auth="public", website=True)
    def reseller_partner(self, partner):
        return request.website.render('reseller_dermanord.reseller', {
            'reseller': partner,
            'reseller_footer': True,
        })
