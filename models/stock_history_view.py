from odoo import api, fields, models, tools
from datetime import datetime, timedelta

class stock_history_view(models.Model):
    _name = 'stock.history.view'
    _auto = False

    id = fields.Integer(string='ID')
    product_template_id = fields.Many2one('product.template', string='Producto')
    location_id = fields.Many2one('stock.location', string='Location')
    location_name = fields.Char(string='Location Name')  # Campo añadido
    date = fields.Date(string='Fecha')
    income = fields.Float(string='Ingreso')
    outcome = fields.Float(string='Salida')
    qty = fields.Float(string='Balance')
    cumulative_balance = fields.Float(string='Acumulado')
    uom_id = fields.Many2one('uom.uom', string='UdM')
    categ_id = fields.Many2one('product.category', string='Categoria')
    
    # Campo para el botón (no se almacena en la vista)
    move_line_action = fields.Char(string="Acciones", compute='_compute_move_line_action')
    def _compute_move_line_action(self):
        for record in self:
            record.move_line_action = f"stock_history_view.action_view_move_lines_{record.id}"

    def action_view_move_lines(self):
        self.ensure_one()
        # Convertir la fecha Date a DateTime para el filtro
        start_date = datetime.combine(self.date, datetime.min.time())
        end_date = datetime.combine(self.date, datetime.max.time())
        
        return {
            'name': f"Movimientos del {self.date}",
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_mode': 'tree,form',
            'domain': [
                ('product_id.product_tmpl_id', '=', self.product_template_id.id),
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('state', '=', 'done')
            ],
            'context': {
                'search_default_groupby_location': True,
                'search_default_groupby_product': False
            }
        }

    def recreate_view(self, product_template_id, companies):
        tools.drop_view_if_exists(self._cr, 'stock_history_view')
        query = f"""
            CREATE OR REPLACE VIEW stock_history_view AS
            WITH daily_totals AS (
                SELECT
                    pp.id AS product_id,
                    sml.date::date AS date,
                    loc.id AS location_id,
                    loc.complete_name AS location_name,
                    -- Entradas diarias
                    SUM(CASE 
                        WHEN sl_dest.id = loc.id AND sl_src.usage != 'internal' 
                        THEN sml.quantity ELSE 0 
                    END) AS income,
                    -- Salidas diarias
                    SUM(CASE 
                        WHEN sl_src.id = loc.id AND sl_dest.usage != 'internal' 
                        THEN sml.quantity ELSE 0 
                    END) AS outcome,
                    -- Balance diario
                    SUM(CASE 
                        WHEN sl_dest.id = loc.id AND sl_src.usage != 'internal' THEN sml.quantity
                        WHEN sl_src.id = loc.id AND sl_dest.usage != 'internal' THEN -sml.quantity
                        ELSE 0 
                    END) AS qty
                FROM stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
                JOIN stock_location sl_src ON sm.location_id = sl_src.id
                JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                JOIN product_product pp ON pp.id = sml.product_id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN stock_location loc ON (
                    (sl_src.id = loc.id OR sl_dest.id = loc.id) AND
                    loc.usage = 'internal' AND
                    loc.company_id IN ({companies})
                )
                WHERE sm.state = 'done'
                AND pt.id = {product_template_id}
                AND sm.company_id IN ({companies})
                GROUP BY pp.id, sml.date::date, loc.id, loc.complete_name
            )
            
            SELECT 
                ROW_NUMBER() OVER () AS id,
                pt.id AS product_template_id,
                dt.location_id,
                dt.location_name,
                dt.date,
                dt.income,
                dt.outcome,
                dt.qty,
                SUM(dt.qty) OVER (
                    PARTITION BY dt.product_id, dt.location_id
                    ORDER BY dt.date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS cumulative_balance,
                pt.uom_id,
                pt.categ_id
            FROM daily_totals dt
            JOIN product_product pp ON pp.id = dt.product_id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            ORDER BY dt.location_name, dt.date
        """
        self._cr.execute(query)