from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import cx_Oracle

DATABASE_CONFIG = {
    'user': 'USER1',
    'password': '1234',
    'dsn': 'localhost:1521/XEPDB1'
}

def get_db_connection():
    try:
        connection = cx_Oracle.connect(
            DATABASE_CONFIG['user'],
            DATABASE_CONFIG['password'],
            DATABASE_CONFIG['dsn']
        )
        return connection
    except cx_Oracle.DatabaseError as e:
        current_app.logger.error(f"Database connection failed: {e}")
        raise

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/inventory', methods=['GET','POST'])
def inventory_index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt.")
        return redirect(url_for('auth.login'))

    query = '''
        SELECT 
            i.product_id,
            pi.product_name,
            w.warehouse_name,
            i.quantity_on_hand
        FROM inventories i
        LEFT JOIN warehouses w
            ON i.warehouse_id = w.warehouse_id
        LEFT JOIN product_information pi
            ON i.product_id = pi.product_id
        WHERE pi.product_name IS NOT NULL
    '''
    parameters = {}

    

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, parameters)
        inventory_data = cursor.fetchall()

        cursor.execute('SELECT DISTINCT product_id, product_name FROM product_information')
        product_name = cursor.fetchall()

        cursor.execute('SELECT DISTINCT warehouse_id, warehouse_name FROM warehouses')
        warehouses = cursor.fetchall()
    except Exception as e:
        current_app.logger.error(f"Error fetching data: {str(e)}")
        inventory_data, product_name, warehouses = [], [], []
    finally:
        conn.close()

    current_app.logger.info(f"User {session['email']} accessed inventory page with filters.")
    
    return render_template('inventory_index.html', 
                           inventory_data=inventory_data, 
                           product_name=product_name, 
                           warehouses=warehouses,
    )


@inventory_bp.route('/inventory/add', methods=('GET', 'POST'))
def add_inventory():
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

            cursor.execute('''SELECT COUNT(*) FROM inventories WHERE product_id = :product_id AND warehouse_id = :warehouse_id''', 
                           {'product_id': product_id, 'warehouse_id': warehouse_id})

            exists = cursor.fetchone()[0] > 0

            if exists:
                cursor.execute('''UPDATE inventories SET quantity_on_hand = quantity_on_hand + :quantity_on_hand 
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
        cursor.execute("SELECT DISTINCT warehouse_id FROM inventories")
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


@inventory_bp.route('/inventory/filter', methods=['GET','POST'])
def filter_inventories():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to filter inventories.")
        return redirect(url_for('auth.login'))

    combined_filter = request.args.get('combined_filter')
    sub_filter = request.args.get('sub_filter')

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

    # Eğer combined_filter ve sub_filter varsa, bunları sorguya dahil et
    if combined_filter and sub_filter:
        if combined_filter == 'product_name':
            query += ' AND pi.product_name = :sub_filter'
        elif combined_filter == 'warehouse_name':
            query += ' AND w.warehouse_name = :sub_filter'
        elif combined_filter == 'warehouse_id' and sub_filter.isdigit():
            query += ' AND w.warehouse_id = :sub_filter'
            sub_filter = int(sub_filter)  # Numarik değer için dönüştür
        else:
            current_app.logger.error(f"Invalid filter combination: {combined_filter}, {sub_filter}")
            return redirect(url_for('inventory.inventory_index'))

        parameters['sub_filter'] = sub_filter  # Parametreyi ekle


    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, parameters)
        inventory = cursor.fetchall()

        cursor.execute('SELECT DISTINCT product_id, product_name FROM product_information')
        product_name = cursor.fetchall()

        cursor.execute('SELECT warehouse_id, warehouse_name FROM warehouses')
        warehouses = cursor.fetchall()
    except Exception as e:
        current_app.logger.error(f"Error while filtering: {str(e)}")
        inventory, product_name, warehouses = [], [], []
    finally:
        conn.close()

    current_app.logger.info(f"User {session['email']} applied filter: {combined_filter} with value: {sub_filter}")

    return render_template('inventory_index.html',
                           inventory_data=inventory,
                           product_name=product_name,
                           warehouses=warehouses,
                           combined_filter=combined_filter,
                           sub_filter=sub_filter)
