# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2021 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models


class ThemeMariaAkerberg(models.AbstractModel):
    _inherit = "theme.utils"

    def _theme_maria_akerberg_post_copy(self, mod):
        self.enable_view("website.template_header_default")
        self.enable_view("website.header_navbar_pills_style")
        self.env["web_editor.assets"].make_scss_customization(
            "/website/static/src/scss/options/user_values.scss",
            {"header-links-style": "'block'"},
        )
