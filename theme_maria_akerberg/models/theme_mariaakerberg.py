from odoo import models


class ThemeMariaAkerberg(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_mariaakerberg_post_copy(self, mod):
        self.enable_view('website.template_header_default')
