from openerp import models, fields, api, _
import datetime
# ~ from openerp1.exceptions import except_orm, Warning, RedirectWarning
import logging
_logger = logging.getLogger(__name__)
class stock_picking(models.Model):
    _inherit  = "stock.picking"
    @api.model
    def _set_min_date(self, field, value, arg):
        _logger.warn("#"*99)
        _logger.warn(value)
        _logger.warn("#"*99)
        super(stock_picking, self)._set_min_date(field, value, arg)
    @api.model
    def get_min_max_date(self, field_name, arg):
        res = super(stock_picking, self).get_min_max_date(cr, uid, ids, field_name, arg, context=None)
        _logger.warn("#"*99)
        _logger.warn(res)
        _logger.warn("#"*99)
        return res
    @api.model
    def create(self, vals):
        if 'date' in vals:
            date = vals['date']
            if date < fields.Datetime.now():
                date = fields.Datetime.now()
        else:
            date = fields.Datetime.now()
        _logger.warn("date: " + date)
        resource_calendar = self.env.ref('stock_picking_dermanord.picking_schedule')
        order_date = fields.Datetime.from_string(date)
        start_date = order_date.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_date = order_date
        # set max iterations to stop any possibility of an infinite loop,
        # although it should never need more than a couple of iterations
        # in the case where there are multiple red days in a row
        max_iterations = 100
        iterations = 0
        while True:
            iterations += 1
            daily_schedule = resource_calendar.get_working_intervals_of_day(start_date)
            _logger.warn(daily_schedule)
            if daily_schedule != [[]]:
                daily_start = daily_schedule[0][0][0]
                if order_date < daily_start:
                     expected_date = daily_schedule[0][0][1]
                     break
            start_date += datetime.timedelta(days=1)
            if max_iterations < iterations:
                break
        vals['min_date'] = expected_date.strftime("%Y-%m-%d %H:%M:%S")
        _logger.warn("min_date: " + vals['min_date'])
        _logger.warn(vals)
        return super(stock_picking, self).create(vals)
