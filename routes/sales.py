from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash,Response
import cx_Oracle
from io import StringIO
import csv
import pandas as pd
from werkzeug.utils import secure_filename
from io import StringIO
import chardet
import csv
import xml.etree.ElementTree as ET
import json
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

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/', methods=['GET', 'POST'])
def index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to sales index.")
        return redirect(url_for('auth.login'))

    # Get product_id from the POST request
    product_id = request.form.get('product_id', None)

    # If no product_id is provided, do not show the table
    if not product_id:
        return render_template('sales_index.html', sales=[], show_table=False)

    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500

    sales = []
    try:
        cursor = conn.cursor()
        ref_cursor = cursor.var(cx_Oracle.CURSOR)

        # Call the stored procedure
        cursor.callproc('GET_SALES_BY_PRODUCT', [int(product_id), ref_cursor])

        # Fetch all results from the ref cursor
        sales = ref_cursor.getvalue().fetchall()
        current_app.logger.info(f"Fetched sales for product_id: {product_id}")

    except cx_Oracle.Error as e:
        current_app.logger.error(f"Failed to fetch sales: {e}")
        return "Error fetching sales data", 500

    finally:
        conn.close()

    return render_template('sales_index.html', sales=sales, show_table=True)


from datetime import datetime

@sales_bp.route('/add', methods=('GET', 'POST'))
def add_sale():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add sale.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # ComboBox için gerekli verileri al
    products = cursor.execute("SELECT product_id, product_name FROM PRODUCT_INFORMATION").fetchall()
    channels = cursor.execute("SELECT channel_id, channel_desc FROM CHANNELS").fetchall()
    promos = cursor.execute("SELECT promo_id, promo_name FROM PROMOTIONS").fetchall()
    customers = cursor.execute("""
    SELECT cust_id, 
           (cust_first_name || ' ' || cust_last_name) AS full_name 
    FROM CUSTOMERS
    """).fetchall()
    if request.method == 'POST':
        # Form verilerini al
        
        product_id = request.form['product_id']
        cust_id = request.form['cust_id']
        channel_id = request.form['channel_id']
        promo_id = request.form['promo_id']
        quantity_sold = request.form['quantity_sold']
        amount_sold = request.form['amount_sold']
        time_id = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Validation vs.

        try:
            cursor.execute('''INSERT INTO SALES ( product_id, cust_id, time_id, channel_id, promo_id, quantity_sold, amount_sold) 
                       VALUES (:1, :2, :3, :4, :5, :6, :7)''', 
                       (product_id, cust_id, time_id, channel_id, promo_id, float(quantity_sold), float(amount_sold)))
            # Veritabanına başarılı bir şekilde veri eklenirse, işlemi commit edebilirsiniz.
            conn.commit()
        except Exception as e:
            # Hata durumunda, hatayı yazdırabilir veya loglayabilirsiniz.
            print(f"Bir hata oluştu: {e}")
            # Eğer gerekirse, işlemi geri alabilirsiniz.
            conn.rollback()

        conn.commit()
        conn.close()
        current_app.logger.info(f"Sale {product_id} added by user {session['email']}.")
        return redirect(url_for('sales.index'))

    return render_template('sales_add.html', products=products, channels=channels, promos=promos, customers=customers)

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

@sales_bp.route('/delete_by_date', methods=('POST',))
def delete_sales_by_date():
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to delete sales by date.")
        return redirect(url_for('auth.login'))

    # Tarih aralığını almak
    start_date = request.form.get('start_date')  # Başlangıç tarihi
    end_date = request.form.get('end_date')      # Bitiş tarihi

    # Tarihler formatlanacak
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        current_app.logger.warning("Geçersiz tarih formatı.")
        return render_template('sales_index.html', error="Geçersiz tarih formatı.")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Tarih aralığındaki satışları silme işlemi
        cursor.execute('''
            DELETE FROM SALES
            WHERE time_id BETWEEN :start_date AND :end_date
        ''', {'start_date': start_date, 'end_date': end_date})

        conn.commit()
        current_app.logger.info(f"Sales from {start_date} to {end_date} deleted by user {session['email']}.")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Error while deleting sales: {e}")
        return render_template('sales_index.html', error="Satışlar silinirken bir hata oluştu.")
    finally:
        conn.close()

    return redirect(url_for('sales.index'))

def handle_csv_upload_for_sales(file):
    raw_data = file.read()
    encoding = chardet.detect(raw_data)['encoding']
    csv_data = StringIO(raw_data.decode(encoding))
    df = pd.read_csv(csv_data)
    return process_dataframe_for_sales(df)



def process_dataframe_for_sales(df):
    # Kolon isimlerini küçült ve boşluklardan arındır
    df.columns = [col.strip().lower() for col in df.columns]

    # Gerekli kolonların kontrolü
    required_columns = ['product_id', 'cust_id', 'time_id', 'channel_id', 
                        'promo_id', 'quantity_sold', 'amount_sold']
    if not all(col in df.columns for col in required_columns):
        current_app.logger.warning("Eksik gerekli kolonlar mevcut.")
        return render_template('sales_index.html', error="Gerekli kolonlar eksik.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT INTO SALES (product_id, cust_id, time_id, channel_id, promo_id, quantity_sold, amount_sold)
                VALUES (:1, :2, :3, :4, :5, :6, :7)
            ''', (row['product_id'], row['cust_id'], row['time_id'],
                  row['channel_id'], row['promo_id'], float(row['quantity_sold']), 
                  float(row['amount_sold'])))
        conn.commit()
        current_app.logger.info("CSV verisi SALES tablosuna yüklendi.")
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"SALES verisi yüklenirken hata oluştu: {e}")
        return render_template('sales_index.html', error="Veri yüklenirken hata oluştu.")
    finally:
        conn.close()
    return redirect(url_for('sales.index'))


def generate_csv_for_sales(columns, rows):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)  # Kolon başlıklarını ekle
    for row in rows:
        writer.writerow(row)   # Her satırı CSV'ye ekle
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=sales_export.csv'
    return response


@sales_bp.route('/import', methods=['POST'])
def import_sales():
    if 'email' not in session:
        current_app.logger.warning("Yetkisiz erişim: satış verisi yüklemeye çalıştı.")
        return redirect(url_for('auth.login'))

    file = request.files.get('file')
    if not file:
        return redirect(url_for('sales.index'))

    filename = secure_filename(file.filename)
    file_ext = filename.split('.')[-1].lower()

    if file_ext == 'csv':
        return handle_csv_upload_for_sales(file)

    else:
        current_app.logger.warning(f"Desteklenmeyen dosya formatı: {file_ext}")
        return render_template('sales_index.html', error="Yalnızca CSV formatı desteklenir.")


@sales_bp.route('/export', methods=['GET'])
def export_sales():
    if 'email' not in session:
        current_app.logger.warning("Yetkisiz erişim: satış verisi dışa aktarmaya çalıştı.")
        return redirect(url_for('auth.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT product_id, cust_id, time_id, channel_id, promo_id, 
                   quantity_sold, amount_sold 
            FROM SALES
        ''')
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        return generate_csv_for_sales(columns, rows)
    except Exception as e:
        current_app.logger.error(f"Veri dışa aktarılırken hata oluştu: {str(e)}")
        return render_template('sales_index.html', error="Veri dışa aktarılırken hata oluştu.")