from odoo import api, fields, models, tools
from datetime import datetime, timedelta

class stock_history_view(models.Model):
    _name = 'stock.history.view'
    _auto = False

    date = fields.Date('Date')
    income = fields.Float(string='Entrada', digits=(8, 6))
    outcome = fields.Float(string='Salida', digits=(8, 6))
    qty = fields.Float(string='Cantidad', digits=(8, 6))
    product_template_id = fields.Many2one('product.template', string="Producto", readonly=True)
    uom_id = fields.Many2one('uom.uom')
    categ_id = fields.Many2one('product.category', string="Categoria del Producto", readonly=True)

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
            CREATE VIEW stock_history_view AS (
                WITH daily_movements AS (
                    SELECT
                        pp.id AS product_id,
                        sml.date::date AS date,
                        SUM(CASE WHEN sl_dest.usage = 'internal' THEN sml.quantity ELSE 0 END) AS income,
                        SUM(CASE WHEN sl_src.usage = 'internal' THEN sml.quantity ELSE 0 END) AS outcome
                    FROM stock_move_line sml
                    JOIN stock_move sm ON sm.id = sml.move_id
                    JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                    JOIN stock_location sl_src ON sm.location_id = sl_src.id
                    JOIN product_product pp ON pp.id = sml.product_id
                    JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    WHERE sm.state = 'done'
                    AND pt.id = {product_template_id}
                    AND sm.company_id IN ({companies})
                    GROUP BY pp.id, sml.date::date
                ),

                date_range AS (
                    SELECT 
                        generate_series(
                            (SELECT MIN(date) FROM daily_movements),
                            CURRENT_DATE,
                            '1 day'::interval
                        )::date AS date
                ),

                all_dates AS (
                    SELECT 
                        dr.date,
                        dm.product_id,
                        COALESCE(dm.income, 0) AS income,
                        COALESCE(dm.outcome, 0) AS outcome
                    FROM date_range dr
                    LEFT JOIN daily_movements dm ON dr.date = dm.date
                    WHERE dm.product_id IS NOT NULL OR EXISTS (
                        SELECT 1 FROM daily_movements WHERE product_id IN (
                            SELECT pp.id 
                            FROM product_product pp
                            JOIN product_template pt ON pp.product_tmpl_id = pt.id
                            WHERE pt.id = {product_template_id}
                        )
                    )
                )

                SELECT 
                    ROW_NUMBER() OVER () AS id,
                    pt.id AS product_template_id,
                    ad.date,
                    ad.income,
                    ad.outcome,
                    SUM(ad.income - ad.outcome) OVER (
                        PARTITION BY ad.product_id 
                        ORDER BY ad.date
                    ) AS qty,
                    pt.uom_id,
                    pt.categ_id
                FROM all_dates ad
                JOIN product_product pp ON pp.id = ad.product_id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                ORDER BY ad.date
            )
        """
        self._cr.execute(query)