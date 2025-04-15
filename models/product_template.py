from odoo import api, fields, models, tools
from datetime import date
from odoo.http import request
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_open_stock_history(self):
        companies = ','.join(map(str, self.env.companies.ids))
        self.env['stock.history.view'].recreate_view(self.id, companies)
        
        return {
            'name': "Histórico Diario por Ubicación",
            'res_model': 'stock.history.view',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,pivot,graph',
            'target': 'current',
            'context': {
                'group_by': ['location_name'],
                'graph_measure': ['cumulative_balance'],
                'graph_mode': 'line',  # Para ver la evolución diaria
                'pivot_measures': ['income', 'outcome', 'daily_qty']
            }
        }
