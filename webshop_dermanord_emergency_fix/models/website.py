from odoo import models, fields, api


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def sale_product_domain(self):
        return super(Website, self).sale_product_domain() + self.get_ma_product_domain()
    
    @api.model
    def _get_ma_group_ids(self):
        # TODO: Change ref to quicker method for fetching only id.
        af_id = self.env.ref('product_private.group_dn_af').id
        ht_id = self.env.ref('product_private.group_dn_ht').id
        spa_id = self.env.ref('product_private.group_dn_spa').id
        sk_id = self.env.ref('product_private.group_dn_sk').id
        return (af_id, ht_id, spa_id, sk_id)
        
    @api.model
    def get_ma_product_domain(self):
        """ Return the product domain for Maria Åkerberg customers.
        """
        af, ht, spa, sk = self.env.user.get_ma_groups()
        af_id, ht_id, spa_id, sk_id = self._get_ma_group_ids()
        group_ids = self.env.user.mapped('groups_id.id')
        if not set((af_id, ht_id, spa_id, sk_id)) & set(group_ids):
            # Not a customer
            return []
        domain = [
            '|',
                ('access_group_ids', '=', False),
                ('access_group_ids', 'in', group_ids)]
        return domain
