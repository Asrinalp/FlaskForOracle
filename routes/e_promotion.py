from flask import Blueprint, render_template, request, redirect, url_for, session
import cx_Oracle

# Veritabanı yapılandırması
DATABASE_CONFIG = {
    'user': 'USER1',
    'password': '1234',
    'dsn': 'localhost:1521/XEPDB1'
}

# Blueprint tanımı
e_promotion_bp = Blueprint('promotions', __name__)

# Veritabanı bağlantısı
def get_db_connection():
    try:
        connection = cx_Oracle.connect(
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            dsn=DATABASE_CONFIG['dsn']
        )
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Ana Rota - Promosyonlar Listesi
@e_promotion_bp.route('/promotion', methods=['GET'])
def promotion():
    return redirect(url_for('promotions.view_promotions'))

@e_promotion_bp.route('/promotions', methods=['GET'])
def view_promotions():
    if 'email' not in session:
        return redirect(url_for('auth.login'))

    # Filtreleme parametresi
    promo_id_filter = request.args.get('promo_id', '').strip()

    # Sıralama parametreleri
    sort_column = request.args.get('sort_column', 'PROMO_ID')
    sort_order = request.args.get('sort_order', 'ASC')

    # ASC veya DESC dönüşümlü sıralama
    next_sort_order = 'DESC' if sort_order == 'ASC' else 'ASC'

    # Güvenli sıralama sütunları
    allowed_columns = ['PROMO_ID', 'PROMO_NAME', 'PROMO_COST', 'PROMO_CATEGORY_ID', 'PROMO_BEGIN_DATE', 'PROMO_END_DATE', 'USAGE_COUNT']
    if sort_column not in allowed_columns:
        sort_column = 'PROMO_ID'

    # SQL sorgusu
    query = f"""
        SELECT 
            p.PROMO_ID, 
            p.PROMO_NAME, 
            p.PROMO_COST, 
            p.PROMO_CATEGORY_ID, 
            p.PROMO_BEGIN_DATE, 
            p.PROMO_END_DATE,
            NVL(COUNT(s.PROMO_ID), 0) AS USAGE_COUNT
        FROM PROMOTIONS p
        LEFT JOIN SALES s ON p.PROMO_ID = s.PROMO_ID
        WHERE (:promo_id IS NULL OR p.PROMO_ID = :promo_id)
        GROUP BY p.PROMO_ID, p.PROMO_NAME, p.PROMO_COST, 
                 p.PROMO_CATEGORY_ID, p.PROMO_BEGIN_DATE, p.PROMO_END_DATE
        ORDER BY {sort_column} {sort_order}
    """

    promotions = []
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, {'promo_id': promo_id_filter if promo_id_filter else None})
                promotions = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching promotions: {e}")
        finally:
            conn.close()

    return render_template(
        'e_promotion.html',
        promotions=promotions,
        promo_id_filter=promo_id_filter,
        sort_column=sort_column,
        sort_order=sort_order,
        next_sort_order=next_sort_order
    )

# Promosyon Performans Görüntüleme
@e_promotion_bp.route('/promotions/performance/<int:promo_id>')
def promotion_performance(promo_id):
    if 'email' not in session:
        return redirect(url_for('auth.login'))

    query = """
        SELECT 
            NVL(c.UNIT_COST, 0) AS UNIT_COST,
            NVL(c.UNIT_PRICE, 0) AS UNIT_PRICE,
            NVL(SUM(s.QUANTITY_SOLD * c.UNIT_COST), 0) AS TOTAL_COST,
            NVL(SUM(s.QUANTITY_SOLD * c.UNIT_PRICE), 0) AS TOTAL_REVENUE,
            NVL(SUM((c.UNIT_PRICE - c.UNIT_COST) * s.QUANTITY_SOLD), 0) AS TOTAL_PROFIT
        FROM SALES s
        JOIN COSTS c ON s.PRODUCT_ID = c.PRODUCT_ID AND s.PROMO_ID = c.PROMO_ID
        WHERE s.PROMO_ID = :promo_id
        GROUP BY c.UNIT_COST, c.UNIT_PRICE
    """
    performance = None
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, {'promo_id': promo_id})
                performance = cursor.fetchone()
        except Exception as e:
            print(f"Error fetching performance: {e}")
        finally:
            conn.close()

    return render_template(
        'promotion_performance.html', 
        promo_id=promo_id, 
        performance=performance, 
        no_info=performance is None
    )


