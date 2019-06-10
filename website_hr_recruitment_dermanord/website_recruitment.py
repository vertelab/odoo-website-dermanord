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

from openerp import models, fields, api, _
from openerp import http
from openerp.http import request

import werkzeug
from openerp.addons.website_hr_recruitment.controllers.main import website_hr_recruitment

import logging
_logger = logging.getLogger(__name__)

class HrDepartment(models.Model):
    _inherit = 'hr.department'
    _order = 'sequence'
    
    website_published = fields.Boolean('Published')
    website_description = fields.Html('Website Description', translate=True)
    sequence = fields.Integer('Sequence')

#~ class HrEmployee(models.Model):
    #~ _inherit = 'hr.employee'
    
    #~ website_published = fields.Boolean('Published')
    #~ website_description = fields.html('Website Description', translate=True)
    #~ sequence = fields.Integer('Sequence')
class HrJob(models.Model):
    _inherit = 'hr.job'
    is_spontaneous = fields.Boolean('Spontaneous')
    

class WebsiteRecruitment(website_hr_recruitment):

    @http.route([
        '/jobs/start',
    ], type='http', auth="public", website=True)
    def start(self, **post):
        return request.website.render("website_hr_recruitment_dermanord.start", {})

    @http.route([
        '/jobs/career',
    ], type='http', auth="public", website=True)
    def career(self, **post):
        return request.website.render("website_hr_recruitment_dermanord.career", {})

    @http.route([
        '/jobs/departments',
    ], type='http', auth="public", website=True)
    def departments(self, **post):
        departments = request.env['hr.department'].sudo().search([('website_published', '=', True)])
        return request.website.render(
            "website_hr_recruitment_dermanord.departments",
            {
                'departments': departments,
            })

    @http.route([
        '/jobs/people',
    ], type='http', auth="public", website=True)
    def people(self, **post):
        #~ employees = request.env['hr.employee'].sudo().search([('website_published', '=', True)], order='sequence')
        return request.website.render("website_hr_recruitment_dermanord.people",
            {
                #~ 'employees': employees,
            })

# added debugging
    @http.route([
        '/jobs/apply/<model("hr.job"):job>',
    ], type='http', auth="public", website=True)
    def jobs_apply(self, job, **post):
        return super(WebsiteRecruitment, self).jobs_apply(job)


    def _get_applicant_files_fields(self):
        return super(WebsiteRecruitment, self)._get_applicant_files_fields() + ['letter_file']
        
    def _get_applicant_relational_fields(self):
        return super(WebsiteRecruitment, self)._get_applicant_relational_fields() + ['type_id', 'source_id', 'job_id']

    def _get_applicant_char_fields(self):
        return super(WebsiteRecruitment, self)._get_applicant_char_fields() + ['availability', 'salary_expected']
