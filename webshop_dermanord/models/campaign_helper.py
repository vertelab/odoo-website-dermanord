# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2018 Vertel AB (<http://vertel.se>).
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
from datetime import datetime, date, timedelta
import logging
_logger = logging.getLogger(__name__)

class crm_tracking_campaign_helper(models.Model):
    _name = 'crm.tracking.campaign.helper'

    country_id          = fields.Many2one(comodel_name='res.country')
    variant_id          = fields.Many2one(comodel_name='product.product', on_delete='cascade')
    product_id          = fields.Many2one(comodel_name='product.template', on_delete='cascade')
    campaign_id         = fields.Many2one(comodel_name='crm.tracking.campaign', on_delete='cascade')
    campaign_phase_id   = fields.Many2one(comodel_name='crm.tracking.phase', on_delete='cascade')
    for_reseller        = fields.Boolean(related='campaign_phase_id.reseller_pricelist')
    salon               = fields.Boolean(string='Salon', compute='compute_salon', store=True)
    
    @api.one
    @api.depends('campaign_id.phase_ids.reseller_pricelist')
    def compute_salon(self):
        # Salon offers don't have a consumer phase
        self.salon = not self.campaign_id.phase_ids.filtered(lambda p: not p.reseller_pricelist)

    @api.model
    def cron_daily_update(self):
        self.env['crm.tracking.campaign.helper'].search([]).unlink() # clear old records
        # This line was removed since "website_published" on campaigns only is used to decide wheter to show the campaign on the front page or not.
        # campaigns = self.env['crm.tracking.campaign'].search([('state', '=', 'open'), ('website_published', '=', True)]) # get all published campaigns
        campaigns = self.env['crm.tracking.campaign'].search([('state', '=', 'open')]) # get all campaigns
        
        for campaign in campaigns:
            self.update_campaign_helper(campaign)
        
        _logger.info('Cron job updating crm.tracking.campaign.helper done')
    
    @api.multi
    def update_campaign_helper(self,campaign):
        d = datetime.now()

        for phase in campaign.phase_ids:
            if (fields.Datetime.from_string(phase.start_date) < d): # check that phase is active (start date in past)
                if (not phase.end_date) or (phase.end_date and (fields.Datetime.from_string(phase.end_date)) > d): # (no end date or end date in future)
                    for campaignobj in  campaign.object_ids:
                        for country in campaign.country_ids:
                            if campaignobj.object_id._name == 'product.template':
                                self.env['crm.tracking.campaign.helper'].create({
                                    'country_id':           country.id,
                                    # ~ 'variant_id':           campaignobj.object_id.id,
                                    'product_id':           campaignobj.object_id.id,
                                    'campaign_id':          campaign.id,
                                    'campaign_phase_id':    phase.id,
                                })
                            elif campaignobj.object_id._name == 'product.product':
                                self.env['crm.tracking.campaign.helper'].create({
                                    'country_id':           country.id,
                                    'variant_id':           campaignobj.object_id.id,
                                    # ~ 'product_id':           campaignobj.object_id.product_tmpl_id.id,
                                    'campaign_id':          campaign.id,
                                    'campaign_phase_id':    phase.id,
                                })
                            elif campaignobj.object_id._name == 'product.public.category':
                                for product in self.env['product.template'].search([('public_categ_ids', 'in', self.object_id.id)]):
                                    self.env['crm.tracking.campaign.helper'].create({
                                        'country_id':           country.id,
                                        # ~ 'variant_id':           campaignobj.object_id.id,
                                        'product_id':           campaignobj.object_id.id,
                                        'campaign_id':          campaign.id,
                                        'campaign_phase_id':    phase.id,
                                    })

class product_product(models.Model):
    _inherit = "product.product"
    is_offer_product_consumer = fields.Boolean(compute='_is_offer_product', search='_search_is_offer_product_consumer')
    is_offer_product_reseller = fields.Boolean(compute='_is_offer_product', search='_search_is_offer_product_reseller')

    @api.one
    def _is_offer_product(self):
        self.is_offer_product_reseller = bool(self.env['crm.tracking.campaign.helper'].sudo().search([('variant_id' , '=', self.id), ('for_reseller', '=', True), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)]))
        if not self.is_offer_product_reseller:
            self.is_offer_product_reseller = bool(self.env['crm.tracking.campaign.helper'].sudo().search([('product_id' , '=', self.product_tmpl_id.id), ('for_reseller', '=', True), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)]))
        self.is_offer_product_consumer = bool(self.env['crm.tracking.campaign.helper'].sudo().search([('variant_id' , '=', self.id), ('for_reseller', '=', False), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)]))
        if not self.is_offer_product_consumer:
            self.is_offer_product_consumer = bool(self.env['crm.tracking.campaign.helper'].sudo().search([('product_id' , '=', self.product_tmpl_id.id), ('for_reseller', '=', False), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)]))

    @api.model
    def _search_is_offer_product_reseller(self, op, value):
        # only supports op: =; value: True, False
        if value:
            ret = self.env['crm.tracking.campaign.helper'].sudo().search([('variant_id', '=', self.id), ('for_reseller', '=', True), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
            if not ret:
                ret = self.env['crm.tracking.campaign.helper'].sudo().search([('product_id', '=', self.product_tmpl_id.id), ('for_reseller', '=', True), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
        else:
            ret = self.env['crm.tracking.campaign.helper'].sudo().search([('variant_id', '=', self.id), ('for_reseller', '!=', True), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
            if not ret:
                ret = self.env['crm.tracking.campaign.helper'].sudo().search([('product_id', '=', self.product_tmpl_id.id), ('for_reseller', '!=', True), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
        
        return bool(ret)

    @api.model
    def _search_is_offer_product_consumer(self, op, value):
        # only supports op: =; value: True, False
        if value:
            ret = self.env['crm.tracking.campaign.helper'].sudo().search([('variant_id', '=', self.id), ('for_reseller', '=', False), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
            if not ret:
                ret = self.env['crm.tracking.campaign.helper'].sudo().search([('product_id', '=', self.product_tmpl_id.id), ('for_reseller', '=', False), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
        else:
            ret = self.env['crm.tracking.campaign.helper'].sudo().search([('variant_id', '=', self.id), ('for_reseller', '!=', False), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
            if not ret:
                ret = self.env['crm.tracking.campaign.helper'].sudo().search([('product_id', '=', self.product_tmpl_id.id), ('for_reseller', '!=', False), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
        return bool(ret)

class product_template(models.Model):
    _inherit = "product.template"
    
    is_offer_product_consumer = fields.Boolean(compute='_is_offer_product', search='_search_is_offer_product_consumer')
    is_offer_product_reseller = fields.Boolean(compute='_is_offer_product', search='_search_is_offer_product_reseller')
    
    @api.one
    def _is_offer_product(self):
        self.is_offer_product_reseller = bool(self.env['crm.tracking.campaign.helper'].sudo().search(['|',('product_id' , '=', self.id), ('variant_id', 'in', self.product_variant_ids.mapped('id')), ('for_reseller', '=', True), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)]))
        self.is_offer_product_consumer = bool(self.env['crm.tracking.campaign.helper'].sudo().search(['|',('product_id' , '=', self.id), ('variant_id', 'in', self.product_variant_ids.mapped('id')), ('for_reseller', '=', False), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)]))

    @api.model
    def _search_is_offer_product_reseller(self, op, value):
        # only supports op: =, value: True
        if value:
            ret = self.env['crm.tracking.campaign.helper'].sudo().search([('product_id', '=', self.id), ('for_reseller', '=', True), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
        else:
            ret = self.env['crm.tracking.campaign.helper'].sudo().search([('product_id', '=', self.id), ('for_reseller', '!=', True), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
        return bool(ret)

    @api.model
    def _search_is_offer_product_consumer(self, op, value):
        # only supports op: =, value: True
        if value:
            ret = self.env['crm.tracking.campaign.helper'].sudo().search([('product_id', '=', self.id), ('for_reseller', '=', False), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
        else:
            ret = self.env['crm.tracking.campaign.helper'].sudo().search([('product_id', '=', self.id), ('for_reseller', '!=', False), ('country_id', '=', self.env.user.partner_id.commercial_partner_id.country_id.id)])
        return bool(ret)
