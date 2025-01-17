from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import cx_Oracle

DATABASE_CONFIG = {
    'user': 'USER1',
    'password': '1234',
    'dsn': 'localhost:1521/XEPDB1'
}

# Define the Blueprint
customer_management_bp = Blueprint('customer', __name__)

def get_db_connection():
    connection = cx_Oracle.connect(
        DATABASE_CONFIG['user'],
        DATABASE_CONFIG['password'],
        DATABASE_CONFIG['dsn']
    )
    return connection

@customer_management_bp.route('/customers', methods=['GET'])
def customers_index():
    if 'email' not in session:
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    query = 'SELECT * FROM CUSTOMERS ORDER BY CUST_ID'
    cursor.execute(query)
    customers = cursor.fetchall()
    conn.close()
    return render_template('view_customer_info.html', customers=customers)


@customer_management_bp.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    # Kullanıcının oturumunun doğruluğunu kontrol et
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add customer.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Country ID'leri çek
        cursor.execute("SELECT COUNTRY_ID FROM COUNTRIES")
        countries = [row[0] for row in cursor.fetchall()]

    except cx_Oracle.Error as error:
        current_app.logger.error(f"Error fetching countries: {str(error)}")
        countries = []
    
    finally:
        if conn:
            conn.close()

    if request.method == 'POST':
        # Form verilerini al
        first_name = request.form.get('cust_first_name', '').strip()
        last_name = request.form.get('cust_last_name', '').strip()
        gender = request.form.get('cust_gender', '').strip()
        year_of_birth = request.form.get('cust_year_of_birth', '').strip()
        marital_status = request.form.get('cust_marital_status', '').strip()
        street_address = request.form.get('cust_street_address', '').strip()
        postal_code = request.form.get('cust_postal_code', '').strip()
        city = request.form.get('cust_city', '').strip()
        country_id = request.form.get('country_id', '').strip()

        # Zorunlu alanların boş olup olmadığını kontrol et
        if not all([first_name, last_name, gender, year_of_birth, marital_status, 
                    street_address, postal_code, city, country_id]):
            error_message = "Tüm alanları doldurunuz."
            return render_template('add_customer.html', error=error_message, countries=countries)

        # Veritabanı bağlantısını aç
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # SQL sorgusu
            query = '''
                INSERT INTO CUSTOMERS (CUST_FIRST_NAME, CUST_LAST_NAME, CUST_GENDER, CUST_YEAR_OF_BIRTH, 
                                       CUST_MARITAL_STATUS, CUST_STREET_ADDRESS, CUST_POSTAL_CODE, CUST_CITY, COUNTRY_ID)
                VALUES (:first_name, :last_name, :gender, :year_of_birth, :marital_status, :street_address, 
                        :postal_code, :city, :country_id)
            '''
            cursor.execute(query, {
                'first_name': first_name, 'last_name': last_name, 'gender': gender, 
                'year_of_birth': year_of_birth, 'marital_status': marital_status, 
                'street_address': street_address, 'postal_code': postal_code,
                'city': city, 'country_id': country_id
            })
            conn.commit()
            current_app.logger.info(f"Customer {first_name} {last_name} added.")
            return redirect(url_for('customer.customers_index'))

        except cx_Oracle.Error as error:
            # Veritabanı hatası durumunda kullanıcıya mesaj göster
            current_app.logger.error(f"Error occurred while adding customer: {str(error)}")
            return render_template('add_customer.html', error=f"Hata oluştu: {str(error)}", countries=countries)

        finally:
            # Bağlantıyı kapat
            if conn:
                conn.close()

    # GET isteği için countries listesini template'e gönder
    return render_template('add_customer.html', error=None, countries=countries)




@customer_management_bp.route('/edit/<int:cust_id>', methods=['GET', 'POST'])
def edit_customer(cust_id):
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to edit customer.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        gender = request.form.get('gender')
        year_of_birth = request.form.get('year_of_birth')
        marital_status = request.form.get('marital_status')
        street_address = request.form.get('street_address')
        postal_code = request.form.get('postal_code')
        city = request.form.get('city')
        country_id = request.form.get('country_id')

        # Check for NULL values
        if not first_name or not last_name or not gender or not year_of_birth or not marital_status or not street_address or not postal_code or not city or not country_id:
            current_app.logger.error("One or more required fields are missing.")
            return render_template('view_customer_edit.html', customer={
                'CUST_ID': cust_id,
                'CUST_FIRST_NAME': first_name,
                'CUST_LAST_NAME': last_name,
                'CUST_GENDER': gender,
                'CUST_YEAR_OF_BIRTH': year_of_birth,
                'CUST_MARITAL_STATUS': marital_status,
                'CUST_STREET_ADDRESS': street_address,
                'CUST_POSTAL_CODE': postal_code,
                'CUST_CITY': city,
                'COUNTRY_ID': country_id
            }, error="One or more required fields are missing.")

        # Update customer details in CUSTOMERS table
        query = '''
            UPDATE CUSTOMERS 
            SET CUST_FIRST_NAME = :first_name, CUST_LAST_NAME = :last_name, CUST_GENDER = :gender, 
                CUST_YEAR_OF_BIRTH = :year_of_birth, CUST_MARITAL_STATUS = :marital_status, 
                CUST_STREET_ADDRESS = :street_address, CUST_POSTAL_CODE = :postal_code, 
                CUST_CITY = :city, COUNTRY_ID = :country_id
            WHERE CUST_ID = :cust_id
        '''
        cursor.execute(query, {
            'first_name': first_name, 'last_name': last_name, 'gender': gender, 'year_of_birth': year_of_birth,
            'marital_status': marital_status, 'street_address': street_address, 'postal_code': postal_code,
            'city': city, 'country_id': country_id, 'cust_id': cust_id
        })
        conn.commit()
        current_app.logger.info(f"Customer {cust_id} updated.")
        return redirect(url_for('customer.customers_index'))

    # Fetch customer data to populate the form
    query = 'SELECT * FROM CUSTOMERS WHERE CUST_ID = :cust_id'
    cursor.execute(query, {'cust_id': cust_id})
    customer = cursor.fetchone()

    conn.close()
    return render_template('view_customer_edit.html', customer={
        'CUST_ID': customer[0],
        'CUST_FIRST_NAME': customer[1],
        'CUST_LAST_NAME': customer[2],
        'CUST_GENDER': customer[3],
        'CUST_YEAR_OF_BIRTH': customer[4],
        'CUST_MARITAL_STATUS': customer[5],
        'CUST_STREET_ADDRESS': customer[6],
        'CUST_POSTAL_CODE': customer[7],
        'CUST_CITY': customer[8],
        'COUNTRY_ID': customer[9]
    })

@customer_management_bp.route('/delete/<int:cust_id>', methods=['POST'])
def delete_customer(cust_id):
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to delete customer.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

 # Müşteriyi silen sorgu
    customer_delete_query = 'DELETE FROM CUSTOMERS WHERE CUST_ID = :cust_id'
    cursor.execute(customer_delete_query, {'cust_id': cust_id})    
    conn.commit()
    conn.close()
    return redirect(url_for('customer.customers_index'))
