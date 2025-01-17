from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import cx_Oracle

DATABASE_CONFIG = {
    'user': 'USER1',
    'password': '1234',
    'dsn': 'localhost:1521/XEPDB1'
}

# Define the Blueprint
order_management_bp = Blueprint('order', __name__)

def get_db_connection():
    connection = cx_Oracle.connect(
        DATABASE_CONFIG['user'],
        DATABASE_CONFIG['password'],
        DATABASE_CONFIG['dsn']
    )
    return connection

@order_management_bp.route('/orders', methods=['GET'])
def orders_index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to orders list.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch filter and sorting parameters
    status_filter = request.args.get('order_status')
    sort_column = request.args.get('sort_column', 'o.order_id')  # Default sort column
    sort_order = request.args.get('sort_order', 'asc').lower()  # Default sort order

    # Define valid columns for sorting to avoid SQL injection
    valid_columns = {
        'order_id': 'o.order_id',
        'order_date': 'o.order_date',
        'customer_name': "c.cust_first_name || ' ' || c.cust_last_name",
        'customer_id': 'c.cust_id',
        'order_status': 'o.order_status'
    }

    # Base query with JOIN
    query = '''
        SELECT 
            o.order_id,
            o.order_date,
            c.cust_first_name || ' ' || c.cust_last_name AS customer_name,
            c.cust_id,
            o.order_status
        FROM orders o
        JOIN customers c ON o.customer_id = c.cust_id
        WHERE 1=1
    '''
    parameters = {}

    # Add status filter if provided
    if status_filter:
        query += ' AND o.order_status = :order_status'
        parameters['order_status'] = int(status_filter)

    # Validate and apply sorting
    if sort_column in valid_columns:
        query += f" ORDER BY {valid_columns[sort_column]} {sort_order}"

    # Log query for debugging
    current_app.logger.info(f"Executing query: {query} with params: {parameters}")

    try:
        cursor.execute(query, parameters)
        orders = cursor.fetchall()
    except cx_Oracle.DatabaseError as e:
        current_app.logger.error(f"Database error: {e}")
        orders = []
    finally:
        cursor.close()
        conn.close()

    # Pass sorting parameters to the template
    return render_template(
        'order_management_index.html',
        orders=orders,
        status_filter=status_filter,
        sort_column=sort_column,
        sort_order=sort_order
    )



@order_management_bp.route('/edit/<int:order_id>', methods=['GET', 'POST'])
def edit_order(order_id):
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to edit order.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    dbms_output = []  # DBMS_OUTPUT mesajlarını toplamak için

    if request.method == 'POST':
        # Yeni order_status değeri formdan alınıyor
        new_status = request.form.get('order_status')

        try:
            # DBMS_OUTPUT'u etkinleştir
            cursor.callproc("DBMS_OUTPUT.ENABLE")

            # Sipariş durumu güncelleme sorgusu
            query = '''
                UPDATE orders
                SET order_status = :order_status
                WHERE order_id = :order_id
            '''
            cursor.execute(query, {'order_status': new_status, 'order_id': order_id})
            conn.commit()

            # DBMS_OUTPUT mesajlarını oku
            status_var = cursor.var(cx_Oracle.NUMBER)
            line_var = cursor.var(cx_Oracle.STRING)

            while True:
                cursor.callproc('DBMS_OUTPUT.GET_LINE', (line_var, status_var))
                if status_var.getvalue() != 0:  # Eğer status 0 değilse (mesaj yok)
                    break
                dbms_output.append(line_var.getvalue())

            # Loglama
            current_app.logger.info(f"Order {order_id} updated to status {new_status} by {session['email']}.")

        except cx_Oracle.DatabaseError as e:
            current_app.logger.error(f"Database error: {e}")
            conn.rollback()
        finally:
            conn.close()

        # Güncel order_status ile aynı sayfayı tekrar render ediyoruz
        return render_template(
            'order_management_edit.html',
            order=(order_id, new_status),
            dbms_output=dbms_output  # DBMS_OUTPUT mesajlarını template'e aktarıyoruz
        )

    # Sipariş detaylarını çekiyoruz
    query = '''
        SELECT order_id, order_status
        FROM orders
        WHERE order_id = :order_id
    '''
    cursor.execute(query, {'order_id': order_id})
    order = cursor.fetchone()
    conn.close()

    if not order:
        current_app.logger.warning(f"Order {order_id} not found.")
        return redirect(url_for('order.orders_index'))

    return render_template(
        'order_management_edit.html',
        order=order,  # Mevcut order bilgileri
        dbms_output=dbms_output  # Varsayılan olarak boş bir liste
    )

@order_management_bp.route('/delete/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to delete order.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = 'DELETE FROM orders WHERE order_id = :order_id'
        cursor.execute(query, {'order_id': order_id})
        conn.commit()
        current_app.logger.info(f"Order {order_id} deleted by {session['email']}.")
    except cx_Oracle.DatabaseError as e:
        current_app.logger.error(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

    return redirect(url_for('order.orders_index'))

