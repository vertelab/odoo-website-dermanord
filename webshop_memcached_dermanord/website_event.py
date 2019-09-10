# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, Open Source Management Solution, third party addon
# Copyright (C) 2018- Vertel AB (<http://vertel.se>).
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
from openerp.addons.web.http import request
from openerp.addons.website_memcached import memcached

from openerp.addons.event_participant_dermanord.event_participant import website_event

import logging
_logger = logging.getLogger(__name__)

# Copied from odoo-website/website_memcached_event
# /event from website_memcached_event gets overwritten by odoo-event-extra/event_participant_dermanord

class website_event(website_event):
    
    # '/event'
    @memcached.route(
        key=lambda kw: '{db}/event{employee}{logged_in}{publisher}{designer}{lang}%s' % (
            request.env['event.event'].search_read(
                [('website_published', '=', True), ('memcached_time', '!=', False)],
                ['memcached_time'], limit=1, order='memcached_time desc'
            ) or [{'memcached_time': ''}])[0]['memcached_time']
    )
    def events(self, page=1, **searches):
        return super(website_event, self).events(page, **searches)
