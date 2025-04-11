from odoo import api, fields, models, tools
from datetime import date
from odoo.http import request
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_open_stock_history(self):
        dt_today = date.today()
        first_of_the_month = dt_today.replace(day=1)
        date_debut = first_of_the_month - relativedelta(months=12)
        companies = ','.join(map(str, self.env.companies.ids))

        self.env['stock.history.view'].recreate_view(self.id, companies)

        # Fetch the stock history records for the current product template
        list_stock_history_obj = self.env['stock.history.view'].search([('date', '>=', date_debut)])

        return {
            'name': "Stocks Histories",
            'res_model': 'stock.history.view',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'graph,pivot,tree',
            'domain': [('id', 'in', list_stock_history_obj.ids)],
            'target': 'current',
        }
