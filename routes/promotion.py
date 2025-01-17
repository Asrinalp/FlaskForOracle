from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
import cx_Oracle
from datetime import datetime

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

promotion_bp = Blueprint('promotion', __name__)

# Promosyonları listeleme
@promotion_bp.route('/', methods=['GET'])
def index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to promotion index.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500

    try:
        cursor = conn.cursor()
        query = '''SELECT p.promo_id , p.promo_name, psc.subcategory_name, pc.category_name, p.promo_cost, p.promo_begin_date, p.promo_end_date
    
        FROM PROMOTIONS p
        LEFT JOIN PROM_SUBCATEGORY psc 
            ON p.promo_subcategory_id = psc.subcategory_id
        LEFT JOIN PROM_CATEGORY pc
            ON p.promo_category_id = pc.category_id
        '''
    
        cursor.execute(query)
        promotions = cursor.fetchall()
    except cx_Oracle.Error as e:
        current_app.logger.error(f"Failed to fetch promotions: {e}")
        return "Error fetching promotions data", 500
    finally:
        conn.close()

    current_app.logger.info(f"User {session['email']} accessed promotion index.")
    return render_template('promo_index.html', promotions=promotions)


@promotion_bp.route('/add', methods=('GET', 'POST'))
def add_promo():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add promotion.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Kategori ve alt kategori bilgilerini al
    categories = cursor.execute('SELECT category_id, category_name FROM PROM_CATEGORY').fetchall()
    subcategories = cursor.execute('SELECT subcategory_id, subcategory_name FROM PROM_SUBCATEGORY').fetchall()

    if request.method == 'POST':
        promo_name = request.form['promo_name']
        promo_category_name = request.form['promo_category']
        promo_subcategory_name = request.form['promo_subcategory']
        promo_cost = request.form['promo_cost']
        promo_begin_date = request.form['promo_begin_date']
        promo_end_date = request.form['promo_end_date']
        begin_date = datetime.strptime(promo_begin_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(promo_end_date, '%Y-%m-%d').date()

        # Kategori ve alt kategori adlarını ID'ye dönüştür
        promo_category_id = cursor.execute(
            'SELECT category_id FROM PROM_CATEGORY WHERE category_name = :1', (promo_category_name,)
        ).fetchone()

        promo_subcategory_id = cursor.execute(
            'SELECT subcategory_id FROM PROM_SUBCATEGORY WHERE subcategory_name = :1', (promo_subcategory_name,)
        ).fetchone()

        # Eğer kategori veya alt kategori bulunamazsa hata mesajı döndür
        if not promo_category_id or not promo_subcategory_id:
            conn.close()
            current_app.logger.warning("Invalid category or subcategory selected.")
            return render_template('promotion_add.html', error="Invalid category or subcategory!", 
                                   categories=categories, subcategories=subcategories)

        # Sorgulardan dönen tuple'lardan ID değerlerini çıkar
        promo_category_id = promo_category_id[0]
        promo_subcategory_id = promo_subcategory_id[0]

        # Promosyon maliyetinin sayısal olup olmadığını kontrol et
        if not promo_cost.replace('.', '', 1).isdigit():
            conn.close()
            current_app.logger.warning(f"Invalid numeric value for promo cost.")
            return render_template('promotion_add.html', error="Cost must be a numeric value!", 
                                   categories=categories, subcategories=subcategories)

        # Promosyon adı kontrolü
        existing_promotion = cursor.execute(
            'SELECT * FROM PROMOTIONS WHERE promo_name = :1', (promo_name,)
        ).fetchone()
        if existing_promotion:
            conn.close()
            current_app.logger.warning(f"Attempt to add existing promotion {promo_name}.")
            return render_template('promotion_add.html', error="Promotion already exists!", 
                                   categories=categories, subcategories=subcategories)

        # Yeni promosyonu veritabanına ekle
        cursor.execute('''
            INSERT INTO PROMOTIONS (promo_name, promo_subcategory_id, promo_category_id, 
                                    promo_cost, promo_begin_date, promo_end_date)
            VALUES (:1, :2, :3, :4, TO_DATE(:5, 'YYYY-MM-DD'), TO_DATE(:6, 'YYYY-MM-DD'))
        ''', (promo_name, promo_subcategory_id, promo_category_id, 
              float(promo_cost), begin_date, end_date))

        conn.commit()
        conn.close()
        current_app.logger.info(f"Promotion {promo_name} added by user {session['email']}.")
        return redirect(url_for('promotion.index'))

    conn.close()
    return render_template('promotion_add.html', categories=categories, subcategories=subcategories)

# Promosyon düzenleme
@promotion_bp.route('/edit/<int:promo_id>', methods=('GET', 'POST'))
def edit_promo(promo_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to edit promotion {promo_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    promotion = cursor.execute('SELECT * FROM PROMOTIONS WHERE promo_id = :1', (promo_id,)).fetchone()
    if not promotion:
        conn.close()
        return "Promotion not found", 404

    if request.method == 'POST':
        promo_name = request.form['promo_name']
        promo_subcategory_id = request.form['promo_subcategory_id']
        promo_category_id = request.form['promo_category_id']
        promo_cost = request.form['promo_cost']
        promo_begin_date = request.form['promo_begin_date']
        promo_end_date = request.form['promo_end_date']

        cursor.execute('''
            UPDATE PROMOTIONS
            SET promo_name = :1, promo_subcategory_id = :2, promo_category_id = :3, 
                promo_cost = :4, promo_begin_date = TO_DATE(:5, 'YYYY-MM-DD'), 
                promo_end_date = TO_DATE(:6, 'YYYY-MM-DD')
            WHERE promo_id = :7
        ''', (promo_name, promo_subcategory_id, promo_category_id, 
              float(promo_cost), promo_begin_date, promo_end_date, promo_id))

        conn.commit()
        conn.close()
        current_app.logger.info(f"Promotion {promo_id} updated by user {session['email']}.")
        return redirect(url_for('promotion.index'))

    conn.close()
    return render_template('promotion_edit.html', promotion=promotion)

# Promosyon silme
@promotion_bp.route('/delete/<int:promo_id>', methods=('POST',))
def delete_promo(promo_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to delete promotion {promo_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM PROMOTIONS WHERE promo_id = :1', (promo_id,))
    conn.commit()
    conn.close()
    current_app.logger.info(f"Promotion {promo_id} deleted by user {session['email']}.")
    return redirect(url_for('promotion.index'))
