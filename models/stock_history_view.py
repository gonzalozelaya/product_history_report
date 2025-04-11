from odoo import api, fields, models, tools
from datetime import date
from odoo.http import request
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class stock_history_view(models.Model):
    _name = 'stock.history.view'
    _auto = False

    date = fields.Date('Date')
    income = fields.Float(string='Input', digits=(8, 6))
    outcome = fields.Float(string='Output', digits=(8, 6))
    qty = fields.Float(string='Stock Quantity uom', digits=(8, 6))

    product_template_id = fields.Many2one('product.template', string="Product", readonly=True)

    uom_id = fields.Many2one('uom.uom')
    categ_id = fields.Many2one('product.category', string="Category", readonly=True)

    def recreate_view(self, product_template_id, companies):
        tools.drop_view_if_exists(self._cr, 'stock_history_view')
        query = f"""
            CREATE VIEW stock_history_view AS (
                WITH income_outcome_cte AS (
                    SELECT
                        sm.product_id,
                        sml.date,
                        CASE WHEN sl_dest.usage = 'internal' THEN sml.qty_done ELSE 0 END AS income,
                        CASE WHEN sl_src.usage = 'internal' THEN sml.qty_done ELSE 0 END AS outcome
                    FROM stock_move sm
                    JOIN (
                        SELECT move_id, SUM(quantity) AS qty_done, MIN(date) AS date 
                        FROM stock_move_line sml
                        JOIN product_product pp ON pp.id = sml.product_id
                        JOIN product_template pt ON pp.product_tmpl_id = pt.id
                        WHERE pt.id = {product_template_id} and sml.company_id in ({companies}) 
                        GROUP BY move_id
                    ) sml ON sml.move_id = sm.id
                    JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
                    JOIN stock_location sl_src ON sm.location_id = sl_src.id
                    JOIN product_product pp ON pp.id = sm.product_id
                    JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    WHERE sm.state = 'done'
                    AND pt.id = {product_template_id} and sm.company_id in ({companies})
                ),

                income_outcome_cte_final AS (
                    SELECT 
                        product_id,
                        date_trunc('MONTH', (CURRENT_DATE - INTERVAL '1.1 year'))::DATE AS date,
                        SUM(income) AS income,
                        SUM(outcome) AS outcome
                    FROM income_outcome_cte
                    WHERE date <= date_trunc('MONTH', (CURRENT_DATE - INTERVAL '1.1 year'))::DATE
                    GROUP BY product_id

                    UNION ALL

                    SELECT *
                    FROM income_outcome_cte
                    WHERE date > date_trunc('MONTH', (CURRENT_DATE - INTERVAL '1.1 year'))::DATE
                ),

                date_series AS (
                    SELECT (generate_series(
                        date_trunc('MONTH', (CURRENT_DATE - INTERVAL '1.1 year'))::DATE,
                        (CURRENT_DATE + INTERVAL '1 month')::DATE,
                        '1 month'::INTERVAL
                    )::DATE - INTERVAL '1 day')::DATE AS date
                ),

                stock_history AS (
                    SELECT
                        p.product_id,
                        g.date,
                        SUM(COALESCE(i.income, 0)) AS income,
                        SUM(COALESCE(i.outcome, 0)) AS outcome
                    FROM date_series g
                    CROSS JOIN (
                        SELECT pp.id AS product_id 
                        FROM product_product pp
                        JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                        WHERE pt.active IS TRUE
                        AND pt.id = {product_template_id}
                    ) p
                    LEFT JOIN income_outcome_cte_final i ON TO_CHAR(g.date, 'YYYY-MM') = TO_CHAR(i.date, 'YYYY-MM') 
                        AND p.product_id = i.product_id
                    GROUP BY p.product_id, g.date
                    ORDER BY p.product_id, g.date
                )

                SELECT 
                    CONCAT(pt.id::TEXT, TO_CHAR(date, 'YYYYMMDD')) AS id,
                    pt.id AS product_template_id,
                    date,
                    income,
                    outcome,
                    ROUND(SUM(income - outcome) OVER (PARTITION BY product_id ORDER BY date), 3) AS qty,
                    pt.uom_id,
                    pt.categ_id
                FROM stock_history sh
                JOIN product_product pp ON pp.id = sh.product_id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
            )
        """
        self._cr.execute(query)
