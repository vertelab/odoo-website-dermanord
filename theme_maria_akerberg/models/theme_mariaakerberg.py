from odoo import models

class ThemeMariaAkerberg(models.AbstractModel):
    _inherit = 'theme.utils'

    def _theme_maria_akerberg_post_copy(self, mod):
        self.enable_view('website.template_header_default')
        self.enable_view('website.header_navbar_pills_style')
        self.env['web_editor.assets'].make_scss_customization('/website/static/src/scss/options/user_values.scss', {'header-links-style': "'block'"})
