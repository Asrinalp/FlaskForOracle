from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import cx_Oracle

DATABASE_CONFIG = {
    'user': 'USER1',
    'password': '1234',
    'dsn': 'localhost:1521/XEPDB1'
}

def get_db_connection():
    connection = cx_Oracle.connect(
        DATABASE_CONFIG['user'],
        DATABASE_CONFIG['password'],
        DATABASE_CONFIG['dsn']
    )
    return connection

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/')
def inventory_index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to inventory index.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    filter_product_name = request.args.get('product_name')
    filter_warehouse_name = request.args.get('warehouse_name')

    query = '''
        SELECT 
            i.product_id,
            pi.product_name,
            w.warehouse_name,
            i.quantity_on_hand
        FROM 
            inventories i
        LEFT JOIN 
            warehouses w ON i.warehouse_id = w.warehouse_id
        LEFT JOIN 
            product_information pi ON i.product_id = pi.product_id
        WHERE 
            pi.product_name IS NOT NULL
    '''

    parameters = {}
    if filter_product_name:
        query += ' AND pi.product_name = :product_name'
        parameters['product_name'] = filter_product_name
    if filter_warehouse_name:
        query += ' AND w.warehouse_name = :warehouse_name'
        parameters['warehouse_name'] = filter_warehouse_name

    cursor.execute(query, parameters)
    inventories = cursor.fetchall()

    cursor.execute('SELECT DISTINCT product_name FROM product_information')
    products = cursor.fetchall()

    cursor.execute('SELECT DISTINCT warehouse_name FROM warehouses')
    warehouses = cursor.fetchall()

    conn.close()

    return render_template('inventory_index.html', inventories=inventories, products=products, warehouses=warehouses,
                           filter_product_name=filter_product_name, filter_warehouse_name=filter_warehouse_name)

@inventory_bp.route('/inventory/add', methods=('GET', 'POST'))
def add_edit_inventory():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add inventory.")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        product_id = request.form['product_id']
        warehouse_id = request.form['warehouse_id']
        quantity_on_hand = request.form['quantity_on_hand']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('''SELECT COUNT(*) FROM inventories 
                              WHERE product_id = :product_id AND warehouse_id = :warehouse_id''', 
                           {'product_id': product_id, 'warehouse_id': warehouse_id})
            exists = cursor.fetchone()[0] > 0

            if exists:
                cursor.execute('''UPDATE inventories 
                                  SET quantity_on_hand = quantity_on_hand + :quantity_on_hand 
                                  WHERE product_id = :product_id AND warehouse_id = :warehouse_id''', 
                               {'product_id': product_id, 'warehouse_id': warehouse_id, 'quantity_on_hand': quantity_on_hand})
                current_app.logger.info(f"Inventory updated for product {product_id} in warehouse {warehouse_id}.")
            else:
                cursor.execute('''INSERT INTO inventories (product_id, warehouse_id, quantity_on_hand) 
                                  VALUES (:product_id, :warehouse_id, :quantity_on_hand)''', 
                               {'product_id': product_id, 'warehouse_id': warehouse_id, 'quantity_on_hand': quantity_on_hand})
                current_app.logger.info(f"Product {product_id} added to warehouse {warehouse_id}.")

            conn.commit()
        except Exception as e:
            current_app.logger.error(f"Error while adding/updating inventory: {str(e)}")
        finally:
            conn.close()

        return redirect(url_for('inventory.inventory_index'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT warehouse_id, warehouse_name FROM warehouses")
        warehouse_ids = cursor.fetchall()
    except Exception as e:
        current_app.logger.error(f"Error fetching warehouse IDs: {str(e)}")
        warehouse_ids = []
    finally:
        conn.close()

    return render_template('inventory_add.html', warehouse_ids=warehouse_ids)



@inventory_bp.route('/inventory/delete/<int:product_id>', methods=('POST',))
def delete_inventory(product_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to delete product with ID {product_id}.")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM inventories WHERE product_id = :1', (product_id,))
        conn.commit()
        current_app.logger.info(f"Product {product_id} deleted by user {session['email']}.")
    except Exception as e:
        current_app.logger.error(f"Error deleting inventory product {product_id}: {str(e)}")
    finally:
        conn.close()

    return redirect(url_for('inventory.inventory_index'))
