from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
import cx_Oracle

# Veritabanı yapılandırması
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
    except cx_Oracle.Error as e:
        current_app.logger.error(f"Database connection failed: {e}")
        return None

cost_bp = Blueprint('costs', __name__)

@cost_bp.route('/', methods=['GET', 'POST'])
def index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to cost index.")
        return redirect(url_for('auth.login'))

    # Get product_id from the POST request
    product_id = request.form.get('product_id', None)

    # If no product_id is provided, do not show the table
    if not product_id:
        return render_template('cost_index.html', costs=[], show_table=False)

    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500

    costs = []
    try:
        cursor = conn.cursor()
        ref_cursor = cursor.var(cx_Oracle.CURSOR)

        # Call the stored procedure
        cursor.callproc('GET_COSTS_BY_PRODUCT', [int(product_id), ref_cursor])

        # Fetch all results from the ref cursor
        costs = ref_cursor.getvalue().fetchall()
        current_app.logger.info(f"Fetched costs for product_id: {product_id}")

    except cx_Oracle.Error as e:
        current_app.logger.error(f"Failed to fetch costs: {e}")
        return "Error fetching cost data", 500

    finally:
        conn.close()

    return render_template('cost_index.html', costs=costs, show_table=True)


# Maliyet ekleme
@cost_bp.route('/add', methods=('GET', 'POST'))
def add_cost():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add cost.")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        product_id = request.form['product_id']
        unit_cost = request.form['unit_cost']
        unit_price = request.form['unit_price']
        channel = request.form['promo_id']
        promo_id = request.form['channel_id']
        time_id = request.form['time_id']
        # Sayısal değerlerin doğruluğunu kontrol et
        if not unit_cost.replace('.', '', 1).isdigit() or not unit_price.replace('.', '', 1).isdigit():
            current_app.logger.warning(f"Invalid numeric values for product {product_id}.")
            return render_template('cost_add.html', error="Unit Cost and Unit Price must be numeric values!")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Ürün mevcut mu kontrol et
        existing_product = cursor.execute('SELECT * FROM PRODUCT_INFORMATION WHERE product_id = :1', (product_id,)).fetchone()
        if not existing_product:
            conn.close()
            current_app.logger.warning(f"Attempt to add cost for non-existing product ID {product_id}.")
            return render_template('cost_add.html', error="Product ID does not exist!")

        
           # Yeni veri ekleme
        cursor.execute('''
            BEGIN
                -- INSERT statement
                INSERT INTO COSTS (product_id, time_id, promo_id, channel_id, unit_cost, unit_price)
                VALUES (:1, :2, :3, :4, :5, :6);
            EXCEPTION
                WHEN OTHERS THEN
                    -- Hata mesajı ve hata kodunu çekme
                    DBMS_OUTPUT.PUT_LINE('Error Message: ' || SQLERRM);
                    DBMS_OUTPUT.PUT_LINE('Error Code: ' || SQLCODE);
            END;             
            ''', (product_id, time_id, promo_id, channel, float(unit_cost), float(unit_price)))


        conn.commit()
        conn.close()
        current_app.logger.info(f"Cost for product {product_id} added by user {session['email']}.")
        return redirect(url_for('costs.index'))

    return render_template('cost_add.html')

# Maliyet güncelleme
@cost_bp.route('/edit/<int:product_id>', methods=('GET', 'POST'))
def edit_cost(product_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to edit cost for product {product_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cost = cursor.execute('SELECT * FROM COSTS WHERE product_id = :1', (product_id,)).fetchone()
    if not cost:
        conn.close()
        return "Cost not found", 404

    if request.method == 'POST':
        unit_cost = request.form['unit_cost']
        unit_price = request.form['unit_price']

        cursor.execute('''
            UPDATE COSTS
            SET unit_cost = :1, unit_price = :2
            WHERE product_id = :3
        ''', (float(unit_cost), float(unit_price), product_id))

        conn.commit()
        conn.close()
        current_app.logger.info(f"Cost for product {product_id} updated by user {session['email']}.")
        return redirect(url_for('cost.index'))

    conn.close()
    return render_template('cost_edit.html', cost=cost)

# Maliyet silme
@cost_bp.route('/delete/<int:product_id>', methods=('POST',))
def delete_cost(product_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to delete cost for product {product_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM COSTS WHERE product_id = :1', (product_id,))
    conn.commit()
    conn.close()
    current_app.logger.info(f"Cost for product {product_id} deleted by user {session['email']}.")
    return redirect(url_for('cost.index'))
