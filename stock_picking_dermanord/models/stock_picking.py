from openerp import models, fields, api, _
import datetime
# ~ from openerp1.exceptions import except_orm, Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)


class stock_picking(models.Model):
    _inherit  = "stock.picking"

    @api.model
    def create(self, vals):
        date = vals['date']
        if date < fields.Datetime.now():
            date = fields.Datetime.now()
        resource_calendar = self.env.ref('stock_picking_dermanord.picking_schedule')
        order_date = fields.Datetime.from_string(date)
        start_date = order_date.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_date = order_date
        max_iterations = 100
        iterations = 0
        while True:
            iterations += 1
            daily_schedule = resource_calendar.get_working_intervals_of_day(start_date)
            _logger.warn(daily_schedule)
            if daily_schedule != [[]]:
                daily_start = daily_schedule[0][0][0]
                daily_end = daily_schedule[0][0][1]
                if order_date < daily_start:
                     expected_date = daily_end
                     break
            start_date += datetime.timedelta(days=1)
            if max_iterations < iterations:
                break
        vals['min_date'] = expected_date.strftime("%Y-%m-%d %H:%M:%S")
        return super(stock_picking, self).create(vals)
