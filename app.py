from flask import Flask
from routes.auth import auth_bp
from routes.jobs import jobs_bp
from routes.dashboard import dashboard_bp
from routes.department import department_bp
from routes.employees import employee_bp
from routes.sales import sales_bp
from routes.inventory import inventory_bp
from routes.product_information import product_bp
from routes.users import user_bp
from routes.promotion import promotion_bp
from routes.costs import cost_bp
from routes.order_management import order_management_bp
from routes.order_details import order_details_bp
from routes.e_promotion import e_promotion_bp
from routes.view_customer_info import customer_management_bp
from routes.view_stock_status import view_stock_status_bp

import logging


# Blueprint'i uygulamaya kaydedin


app = Flask(__name__)
app.secret_key = 'my_secret_key'


# Blueprintleri kaydet"""
app.register_blueprint(auth_bp)
app.register_blueprint(jobs_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(department_bp, url_prefix='/department')
app.register_blueprint(employee_bp, url_prefix='/employee')
app.register_blueprint(sales_bp, url_prefix='/sales')
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(product_bp, url_prefix='/product')
app.register_blueprint(user_bp, url_prefix='/users')
app.register_blueprint(promotion_bp, url_prefix='/promotion')
app.register_blueprint(cost_bp, url_prefix='/costs')
app.register_blueprint(order_management_bp, url_prefix='/order')
app.register_blueprint(order_details_bp)
app.register_blueprint(e_promotion_bp)
app.register_blueprint(customer_management_bp)
app.register_blueprint(view_stock_status_bp)



logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('app.log'),
                        logging.StreamHandler()])

if __name__ == '__main__':
    app.run(debug=True, port=5001)
