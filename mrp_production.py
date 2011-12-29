# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved.
#    
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import time
from datetime import datetime, timedelta, date
from dateutil import parser
from dateutil import rrule

class mrp_production(osv.osv):


    def onchange_production_dates(self, cr, uid, ids, begin_production_date, end_production_date, production_duration, context=None):
        """
            Returns duration and/or end date based on values passed
        """
        if context is None:
            context = {}
        value = {}
        if not begin_production_date:
            return value
        if not end_production_date and not production_duration:
            duration = 1.00
            value[production_duration] = duration

        start = datetime.strptime(begin_production_date, "%Y-%m-%d %H:%M:%S")
        if end_production_date and not production_duration:
            end = datetime.strptime(end_production_date, "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
            value[production_duration] = round(duration, 2)
        elif not end_production_date:
            end = start + timedelta(hours=production_duration)
            value[end_production_date] = end.strftime("%Y-%m-%d %H:%M:%S")
        elif end_production_date and production_duration:
            # we have both, keep them synchronized:
            # set duration based on end_date (arbitrary decision: this avoid
            # getting dates like 06:31:48 instead of 06:32:00)
            end = datetime.strptime(end_production_date, "%Y-%m-%d %H:%M:%S")
            diff = end - start
            duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
            value['production_duration'] = round(duration, 2)

        return {'value': value}

    _inherit = 'mrp.production'
    _columns = {
        'begin_production_date': fields.datetime('Begin production date', required=True),
        'end_production_date': fields.datetime('End production date', required=True),
        'production_duration': fields.float('Duration', digits_compute=dp.get_precision('Account')),
        'production_manpower': fields.one2many('mrp.production.manpower', 'production_id', 'Production manpower', required=True),
        'products_total_cost': fields.float('Material total cost', digits_compute=dp.get_precision('Account'), readonly=True),
        'unit_product_cost': fields.float('Material unit cost', digits_compute=dp.get_precision('Account'), readonly=True),
        'manpower_cost': fields.float('Manpower total cost', digits_compute=dp.get_precision('Account'), readonly=True),
        'manpower_unit_cost': fields.float('Manpower unit cost', digits_compute=dp.get_precision('Account'), readonly=True),
        'total_production_cost': fields.float('Total production cost', digits_compute=dp.get_precision('Account'), readonly=True),
        'unit_production_cost': fields.float('Unit production cost', digits_compute=dp.get_precision('Account'), readonly=True),
        'total_fixed_cost': fields.float('Total fixed cost', digits_compute=dp.get_precision('Account'), readonly=True),
        'totale_costi_accessori':fields.float('Totale Costi Prod.', digits_compute=dp.get_precision('Account'), readonly=True),
        'unit_fixed_cost': fields.float('Unit fixed cost', digits_compute=dp.get_precision('Account'), readonly=True),
        'new_standard_price': fields.float('New standard product price', digits_compute=dp.get_precision('Account'), readonly=True, help="New product price (only if its cost method is set to average)"),
    }
    _defaults = {
        'begin_production_date': lambda *a: time.strftime('%Y-%m-%d 08:00:00'),
        'end_production_date': lambda *a: time.strftime('%Y-%m-%d 13:00:00'),
        'production_duration': 5.0
    }

mrp_production()

class mrp_product_produce(osv.osv_memory):

    _inherit = 'mrp.product.produce'


    def do_produce(self, cr, uid, ids, context=None):
        """
        Inherits method for setting all new products and manpower costs for production
        """
        #Calculating manpower total and unitary cost
        if context.get('active_ids') and context['active_ids']:
            for production in self.pool.get('mrp.production').browse(cr, uid, context['active_ids']):
                manpower_cost = 0.0
                sum_products_cost = 0.0
                sum_fixed_cost = 0.0
                qty_finished_products = 0.0
                tot_products_cost  = 0.0
                unit_product_cost = 0.0
                tot_production_manpower_cost = 0.0
                unit_manpower_cost = 0.0
                sum_fixed_cost  = 0.0
                unit_fixed_cost  = 0.0
                total_production_cost = 0.0
                unit_production_cost  = 0.0
                new_product_standard_price  = 0.0
                dati=self.browse(cr,uid,ids)
                qty_finished_products= dati[0].product_qty

                #First of all, identify the main production product between all finished products
                main_product = False
                finished_products = production.move_created_ids
                for fin_prod in finished_products:
                    #qty_finished_products +=fin_prod.product_qty
                    if fin_prod.product_id.id == production.product_id.id:
                        main_product = fin_prod
                        
                if not main_product:
                    main_product = production
                #Gets product stock before producing...
                stock_before_producing = main_product.product_id.qty_available
                result = super(mrp_product_produce, self).do_produce(cr, uid, ids, context)

                #Manpower cost
                #disattivato per omaf 
                #number_of_workers = len(production.production_manpower)
                #if not number_of_workers > 0:
                #    raise osv.except_osv(_('Warning!'), _('There are no assigned workers to this production. Please, specify some before continuing...'))
                #for worker in production.production_manpower:
                #    manpower_cost += worker.employee_id.product_id.standard_price * worker.production_duration
                #tot_production_manpower_cost = manpower_cost
                #unit_manpower_cost = tot_production_manpower_cost / production.product_qty
                
                #Material cost ((list price consumed products * qty)/sum_qty)
                for consumed_product in production.move_lines2:
                    sum_products_cost += consumed_product.product_id.standard_price * consumed_product.product_qty
                    # aggiorna price unit sul movimento di magazzino
                    #import pdb;pdb.set_trace()
                    ok = self.pool.get('stock.move').write(cr,uid,[consumed_product.id],{'price_unit':consumed_product.product_id.standard_price})
                tot_products_cost = sum_products_cost
                if qty_finished_products<>0:
                    unit_product_cost = tot_products_cost / qty_finished_products
                # cerca negli articoli programmati i servizi che saranno aggiunto al costo di produzione
                #import pdb;pdb.set_trace()
                costi_generali = 0
                for schedulato in production.product_lines:                    
                    if schedulato.product_id.type == "service" :
                        costi_generali += schedulato.product_qty
                    

                #Fixed costs (sum of all fixed costs)
                for fixed_cost in production.fixed_costs:
                    sum_fixed_cost += fixed_cost.amount
                if qty_finished_products<>0:    
                 unit_fixed_cost = sum_fixed_cost / qty_finished_products

                #Total cost (Manpower cost + material cost + fixed cost + structural cost)
                #import pdb;pdb.set_trace()
                total_production_cost = tot_production_manpower_cost + tot_products_cost + sum_fixed_cost+costi_generali
                if qty_finished_products<>0:
                    unit_production_cost = (total_production_cost / qty_finished_products) + main_product.product_id.structural_cost + unit_fixed_cost
                    ok = self.pool.get('stock.move').write(cr,uid,[main_product.id],{'price_unit':unit_production_cost})
                #New product standard price (PMP) = ((product stock before producing * standard price) + (unit_production_cost * prod_qty)) / (stock before producing + produced_qty)
                if qty_finished_products<>0:
                    new_product_standard_price = ((stock_before_producing * main_product.product_id.standard_price) + (unit_production_cost * qty_finished_products))/ (stock_before_producing + qty_finished_products)

                #Updates cost management fields for this production
                vals_production = {
                    'products_total_cost': tot_products_cost,
                    'unit_product_cost': unit_product_cost,
                    'manpower_cost': tot_production_manpower_cost,
                    'manpower_unit_cost': unit_manpower_cost,
                    'total_fixed_cost': sum_fixed_cost,
                    'unit_fixed_cost': unit_fixed_cost,
                    'total_production_cost': total_production_cost,
                    'totale_costi_accessori':costi_generali,
                    'unit_production_cost': unit_production_cost,
                    'new_standard_price': new_product_standard_price
                }
                self.pool.get('mrp.production').write(cr, uid, [production.id], vals_production)

                #Finally we update product list_price and manpower fields accordingly
                vals_product = {}
                if main_product.product_id.cost_method == 'average':
                    vals_product['standard_price'] = new_product_standard_price

                vals_product['manpower_cost'] = unit_manpower_cost

                self.pool.get('product.product').write(cr, uid, main_product.product_id.id, vals_product)

                return result
                

mrp_product_produce()