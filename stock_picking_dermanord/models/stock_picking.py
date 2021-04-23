from openerp import models, fields, api, _
import datetime


import logging
_logger = logging.getLogger(__name__)


class stock_picking(models.Model):
    _inherit  = "stock.picking"

    # ~ @api.model
    # ~ def _set_min_date(self, field, value, arg):
        # ~ _logger.warn("#"*99)
        # ~ _logger.warn(value)
        # ~ _logger.warn("#"*99)
        # ~ super(stock_picking, self)._set_min_date(field, value, arg)

    # ~ @api.model
    # ~ def get_min_max_date(self, field_name, arg):
        # ~ res = super(stock_picking, self).get_min_max_date(cr, uid, ids, field_name, arg, context=None)
        # ~ _logger.warn("#"*99)
        # ~ _logger.warn(res)
        # ~ _logger.warn("#"*99)
        # ~ return res
    @api.model
    def get_next_picking_time(self, resource_calendar, date):
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
        return expected_date

    @api.model
    def create(self, vals):
        if 'date' in vals:
            date = vals['date']
            if date < fields.Datetime.now():
                date = fields.Datetime.now()
        else:
            date = fields.Datetime.now()
        # ~ _logger.warn(self.env['procurement.order'].read())
        _logger.warn("date: " + date)
        resource_calendar = self.env.ref('stock_picking_dermanord.picking_schedule')
        expected_date = self.get_next_picking_time(resource_calendar, date)
        vals['min_date'] = expected_date.strftime("%Y-%m-%d %H:%M:%S")
        _logger.warn("min_date: " + vals['min_date'])
        _logger.warn(vals)
        return super(stock_picking, self).create(vals)
        
        
        
# ~ class sale_order(models.Model):
    # ~ _inherit  = "sale.order"
    
    # ~ def action_done(self, cr, uid, ids, context=None):
        # ~ _logger.warn("action done"*99)
        # ~ for order in self.browse(cr, uid, ids, context=context):
            # ~ self.pool.get('sale.order.line').write(cr, uid, [line.id for line in order.order_line if line.state != 'cancel'], {'state': 'done'}, context=context)
        # ~ return self.write(cr, uid, ids, {'state': 'done'}, context=context)
        
    # ~ def action_ship_create(self, cr, uid, ids, context=None):
        # ~ """Create the required procurements to supply sales order lines, also connecting
        # ~ the procurements to appropriate stock moves in order to bring the goods to the
        # ~ sales order's requested location.

        # ~ :return: True
        # ~ """
        
        # ~ _logger.warn("Action_ship_create!"*50)
        # ~ context = dict(context or {})
        # ~ context['lang'] = self.pool['res.users'].browse(cr, uid, uid).lang
        # ~ procurement_obj = self.pool.get('procurement.order')
        # ~ sale_line_obj = self.pool.get('sale.order.line')
        # ~ for order in self.browse(cr, uid, ids, context=context):
            # ~ proc_ids = []
            # ~ vals = self._prepare_procurement_group(cr, uid, order, context=context)
            # ~ _logger.warn("action_vals: %s ",vals)
            # ~ if not order.procurement_group_id:
                # ~ group_id = self.pool.get("procurement.group").create(cr, uid, vals, context=context)
                # ~ order.write({'procurement_group_id': group_id})
                

            # ~ for line in order.order_line:
                # ~ if line.state == 'cancel':
                    # ~ continue
                # ~ #Try to fix exception procurement (possible when after a shipping exception the user choose to recreate)
                # ~ if line.procurement_ids:
                    # ~ #first check them to see if they are in exception or not (one of the related moves is cancelled)
                    # ~ procurement_obj.check(cr, uid, [x.id for x in line.procurement_ids if x.state not in ['cancel', 'done']])
                    # ~ line.refresh()
                    # ~ #run again procurement that are in exception in order to trigger another move
                    # ~ except_proc_ids = [x.id for x in line.procurement_ids if x.state in ('exception', 'cancel')]
                    # ~ procurement_obj.reset_to_confirmed(cr, uid, except_proc_ids, context=context)
                    # ~ proc_ids += except_proc_ids
                # ~ elif sale_line_obj.need_procurement(cr, uid, [line.id], context=context):
                    # ~ if (line.state == 'done') or not line.product_id:
                        # ~ continue
                    # ~ vals = self._prepare_order_line_procurement(cr, uid, order, line, group_id=order.procurement_group_id.id, context=context)
                    # ~ ctx = context.copy()
                    # ~ ctx['procurement_autorun_defer'] = True
                    # ~ proc_id = procurement_obj.create(cr, uid, vals, context=ctx)
                    # ~ proc_ids.append(proc_id)
            
            # ~ #Confirm procurement order such that rules will be applied on it
            # ~ #note that the workflow normally ensure proc_ids isn't an empty list
            # ~ _logger.warn("before create"*10)
            # ~ procurement_obj.run(cr, uid, proc_ids, context=context)
            # ~ _logger.warn("after create"*10)
            # ~ _logger.warn("picking:  %s", procurement_obj.read(cr, uid, ids, context))
            # ~ #if shipping was in exception and the user choose to recreate the delivery order, write the new status of SO
            # ~ if order.state == 'shipping_except':
                # ~ val = {'state': 'progress', 'shipped': False}

                # ~ if (order.order_policy == 'manual'):
                    # ~ for line in order.order_line:
                        # ~ if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            # ~ val['state'] = 'manual'
                            # ~ break
                # ~ order.write(val)
            # ~ _logger.warn("action end"*50)
        # ~ return True


