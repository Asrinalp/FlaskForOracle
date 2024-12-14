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

sales_bp = Blueprint('sales', __name__)

# Satışları listeleme
@sales_bp.route('/', methods=['GET', 'POST'])
def index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to sales index.")
        return redirect(url_for('auth.login'))

    # Eğer POST isteği varsa, product_id'yi alıyoruz
    product_id = request.form.get('product_id', None)
    
    # Eğer product_id seçilmediyse, tabloyu göstermiyoruz
    if not product_id:
        return render_template('sales_index.html', sales=[], show_table=False)

    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500

    try:
        cursor = conn.cursor()
        query = '''
            SELECT s.product_id, s.cust_id, s.channel_id, s.promo_id, 
                   s.quantity_sold, s.amount_sold,
                   ch.channel_desc, pr.promo_name
            FROM SALES s
            JOIN CHANNELS ch ON s.channel_id = ch.channel_id
            JOIN PROMOTIONS pr ON s.promo_id = pr.promo_id
            WHERE s.product_id = :product_id
            FETCH NEXT 50 ROWS ONLY
        '''
        cursor.execute(query, {'product_id': product_id})
        sales = cursor.fetchall()
    except cx_Oracle.Error as e:
        current_app.logger.error(f"Failed to fetch sales: {e}")
        return "Error fetching sales data", 500
    finally:
        conn.close()

    current_app.logger.info(f"User {session['email']} accessed sales index.")
    return render_template('sales_index.html', sales=sales, show_table=True)


@sales_bp.route('/add', methods=('GET', 'POST'))
def add_sale():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add sale.")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        sale_id = request.form['sale_id']
        product_id = request.form['product_id']
        quantity_sold = request.form['quantity_sold']
        amount_sold = request.form['amount_sold']

        if not quantity_sold.replace('.', '', 1).isdigit() or not amount_sold.replace('.', '', 1).isdigit():
            current_app.logger.warning(f"Invalid numeric values for sale {sale_id}.")
            return render_template('sales_add.html', error="Quantity and Amount must be numeric values!")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check for existing sale ID
        existing_sale = cursor.execute('SELECT * FROM SALES WHERE sale_id = :1', (sale_id,)).fetchone()
        if existing_sale:
            conn.close()
            current_app.logger.warning(f"Attempt to add existing sale ID {sale_id}.")
            return render_template('sales_add.html', error="Sale ID already exists!")

        # Check if product exists
        existing_product = cursor.execute('SELECT * FROM PRODUCTS WHERE product_id = :1', (product_id,)).fetchone()
        if not existing_product:
            conn.close()
            current_app.logger.warning(f"Attempt to add sale for non-existing product ID {product_id}.")
            return render_template('sales_add.html', error="Product ID does not exist!")

        cursor.execute('''
            INSERT INTO SALES (sale_id, product_id, quantity_sold, amount_sold)
            VALUES (:1, :2, :3, :4)
        ''', (sale_id, product_id, float(quantity_sold), float(amount_sold)))

        conn.commit()
        conn.close()
        current_app.logger.info(f"Sale {sale_id} added by user {session['email']}.")
        return redirect(url_for('sales.index'))

    return render_template('sales_add.html')

@sales_bp.route('/edit/<int:sale_id>', methods=('GET', 'POST'))
def edit_sale(sale_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to edit sale {sale_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    sale = cursor.execute('SELECT * FROM SALES WHERE product_id = :1', (sale_id,)).fetchone()
    if not sale:
        conn.close()
        return "Sale not found", 404

    if request.method == 'POST':
        product_id = request.form['product_id']
        quantity_sold = request.form['quantity_sold']
        amount_sold = request.form['amount_sold']

        cursor.execute('''
            UPDATE SALES
            SET product_id = :1, quantity_sold = :2, amount_sold = :3
            WHERE sale_id = :4
        ''', (product_id, float(quantity_sold), float(amount_sold), sale_id))

        conn.commit()
        conn.close()
        current_app.logger.info(f"Sale {sale_id} updated by user {session['email']}.")
        return redirect(url_for('sales.index'))

    conn.close()
    return render_template('sales_edit.html', sale=sale)

@sales_bp.route('/delete/<int:sale_id>', methods=('POST',))
def delete_sale(sale_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to delete sale {sale_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM SALES WHERE sale_id = :1', (sale_id,))
    conn.commit()
    conn.close()
    current_app.logger.info(f"Sale {sale_id} deleted by user {session['email']}.")
    return redirect(url_for('sales.index'))
