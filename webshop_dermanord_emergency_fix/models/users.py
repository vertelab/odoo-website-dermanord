from odoo import models, fields, api

class Users(models.Model):
    _inherit = 'res.users'
    
    def get_ma_groups(self):
        """ Return the Maria Åkerberg customer group memberships for
            this user.
            :returns: tuple of booleans. (af, ht, spa, sk).
        """
        af = self.has_group('webshop_dermanord.group_dn_af')
        ht = self.has_group('webshop_dermanord.group_dn_ht')
        spa = self.has_group('webshop_dermanord.group_dn_spa')
        sk = self.has_group('webshop_dermanord.group_dn_sk')
        return (af, ht, spa, sk)
