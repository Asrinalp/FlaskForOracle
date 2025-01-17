from flask import Blueprint, render_template, request, session, redirect, url_for, current_app
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

order_details_bp = Blueprint('order_details', __name__)

@order_details_bp.route('/order_details', methods=['GET', 'POST'])
def order_details():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to order details.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    order_details = []
    order_id = None

    try:
        if request.method == 'POST':
            order_id = request.form.get('order_id')
            if order_id:
                # Call stored procedure to fetch order details by order_id
                v_order_date = cursor.var(cx_Oracle.DATETIME)
                v_order_status = cursor.var(cx_Oracle.NUMBER)
                v_customer_name = cursor.var(cx_Oracle.STRING)
                v_order_total = cursor.var(cx_Oracle.NUMBER)

                cursor.callproc('GETORDERDETAILS', [
                    int(order_id), 
                    v_order_date, 
                    v_order_status, 
                    v_customer_name, 
                    v_order_total
                ])

                # Format results into a list of tuples for rendering
                order_details = [(
                    order_id, 
                    v_order_date.getvalue(), 
                    v_order_status.getvalue(), 
                    v_customer_name.getvalue(), 
                    v_order_total.getvalue()
                )]
                current_app.logger.info(f"Fetched order details for order_id: {order_id}")

        else:
            # Fetch all records if no order_id is provided
            cursor.execute("""
                SELECT 
                    o.order_id, 
                    o.order_date, 
                    o.order_mode, 
                    c.cust_first_name || ' ' || c.cust_last_name AS customer_name,
                    o.order_status, 
                    o.order_total, 
                    NVL(e.first_name || ' ' || e.last_name, '-') AS employee_name
                FROM orders o
                JOIN customers c ON o.customer_id = c.cust_id
                LEFT JOIN employees e ON o.employee_id = e.employee_id
            """)
            order_details = cursor.fetchall()
            current_app.logger.info("Fetched all order details.")

    except cx_Oracle.DatabaseError as e:
        current_app.logger.error(f"Database error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

    return render_template('order_details_index.html',
                           order_details=order_details,
                           order_id=order_id)

