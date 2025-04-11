# -*- coding: utf-8 -*-
# from odoo import http


# class StockMovementReport(http.Controller):
#     @http.route('/stock_movement_report/stock_movement_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/stock_movement_report/stock_movement_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('stock_movement_report.listing', {
#             'root': '/stock_movement_report/stock_movement_report',
#             'objects': http.request.env['stock_movement_report.stock_movement_report'].search([]),
#         })

#     @http.route('/stock_movement_report/stock_movement_report/objects/<model("stock_movement_report.stock_movement_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('stock_movement_report.object', {
#             'object': obj
#         })
