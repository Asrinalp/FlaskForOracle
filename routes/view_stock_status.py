from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import cx_Oracle

DATABASE_CONFIG = {
    'user': 'USER1',
    'password': '1234',
    'dsn': 'localhost:1521/XEPDB1'
}

# Define the Blueprint
view_stock_status_bp = Blueprint('stock', __name__)

def get_db_connection():
    connection = cx_Oracle.connect(
        DATABASE_CONFIG['user'],
        DATABASE_CONFIG['password'],
        DATABASE_CONFIG['dsn']
    )
    return connection

@view_stock_status_bp.route('/view_stock_status', methods=['GET', 'POST'])
def view_stock_status():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to stock view.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Sorting logic
    sort_column = request.args.get('sort_column', 'PRODUCT_ID')
    sort_order = request.args.get('sort_order', 'ASC')

    # Filtering logic for a specific product
    product_id_filter = request.args.get('product_id')

    query = f'''
        SELECT 
            i.PRODUCT_ID, 
            p.PRODUCT_NAME, 
            i.WAREHOUSE_ID, 
            i.QUANTITY_ON_HAND 
        FROM INVENTORIES i
        JOIN PRODUCT_INFORMATION p ON i.PRODUCT_ID = p.PRODUCT_ID
        WHERE (:product_id_filter IS NULL OR i.PRODUCT_ID = :product_id_filter)
        ORDER BY {sort_column} {sort_order}
    '''
    cursor.execute(query, {'product_id_filter': product_id_filter})
    stocks = cursor.fetchall()

    conn.close()

    return render_template('view_stock_status.html', stocks=stocks, sort_column=sort_column, sort_order=sort_order, product_id_filter=product_id_filter)

@view_stock_status_bp.route('/edit_stock/<int:product_id>/<int:warehouse_id>', methods=['GET', 'POST'])
def edit_stock(product_id, warehouse_id):
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to stock edit.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_quantity = request.form.get('quantity_on_hand')

        try:
            update_query = '''
                UPDATE INVENTORIES
                SET QUANTITY_ON_HAND = :new_quantity
                WHERE PRODUCT_ID = :product_id AND WAREHOUSE_ID = :warehouse_id
            '''
            cursor.execute(update_query, {
                'new_quantity': new_quantity,
                'product_id': product_id,
                'warehouse_id': warehouse_id
            })
            conn.commit()
            current_app.logger.info(f"Stock updated for Product {product_id} in Warehouse {warehouse_id}.")
            return redirect(url_for('stock.view_stock_status'))
        except cx_Oracle.DatabaseError as e:
            current_app.logger.error(f"Database error: {e}")
            conn.rollback()

    # Fetch stock details for the given product and warehouse
    query = '''
        SELECT 
            i.PRODUCT_ID, 
            p.PRODUCT_NAME, 
            i.WAREHOUSE_ID, 
            i.QUANTITY_ON_HAND 
        FROM INVENTORIES i
        JOIN PRODUCT_INFORMATION p ON i.PRODUCT_ID = p.PRODUCT_ID
        WHERE i.PRODUCT_ID = :product_id AND i.WAREHOUSE_ID = :warehouse_id
    '''
    cursor.execute(query, {'product_id': product_id, 'warehouse_id': warehouse_id})
    stock = cursor.fetchone()

    conn.close()

    return render_template('edit_stock.html', stock=stock)
