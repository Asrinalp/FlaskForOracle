from flask import Blueprint, render_template, session, redirect, url_for ,current_app
import cx_Oracle
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

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


dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/admin_dashboard')
def admin_dashboard():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to admin dashboard.")
        return redirect(url_for('auth.login'))
    current_app.logger.info(f"User {session['email']} accessed the admin dashboard.")
    return render_template('admin_dashboard.html')

@dashboard_bp.route('/worker_dashboard')
def worker_dashboard():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access to worker dashboard.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Toplam satışa göre ilk 5 çalışanı getir
        query = """
            SELECT 
                e.employee_id, 
                NVL(e.first_name || ' ' || e.last_name, 'N/A') AS employee_name, 
                SUM(NVL(o.order_total, 0)) AS total_sales
            FROM 
                employees e
            LEFT JOIN 
                orders o ON e.employee_id = o.employee_id
            GROUP BY 
                e.employee_id, e.first_name, e.last_name
            ORDER BY 
                total_sales DESC
            FETCH FIRST 5 ROWS ONLY
        """
        cursor.execute(query)
        top_employees = cursor.fetchall()

    except cx_Oracle.DatabaseError as e:
        current_app.logger.error(f"Database error occurred: {e}")
        top_employees = []
    finally:
        cursor.close()
        conn.close()

    return render_template('worker_dashboard.html', top_employees=top_employees)


@dashboard_bp.route('/logout')
def logout():
    session.clear()
    current_app.logger.info("User logged out successfully.")
    return redirect(url_for('auth.login'))

@dashboard_bp.route('/admin_dashboard/sales', methods=['GET', 'POST'])
def index_sales():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to sales page.")
        return redirect(url_for('auth.login'))
    
    try:
        # Veritabanı bağlantısını al
        connection = get_db_connection()
        cursor = connection.cursor()

        # Sales verilerini çekmek için SQL sorgusu
        cursor.execute("SELECT * FROM sales_view")  # Burada doğru tablo ve sütun isimlerini kullanmalısınız
        sales_data = cursor.fetchall()  # Veriyi çek

        # Ürün bazında grup yapma ve en fazla satılan 20 ürünü al
        cursor.execute("""
            SELECT product_name, COUNT(*) AS sales_count
            FROM sales_view
            GROUP BY product_name
            ORDER BY sales_count DESC
            FETCH FIRST 20 ROWS ONLY
        """)
        product_sales_data = cursor.fetchall()

        cursor.close()
        connection.close()

        current_app.logger.info(f"User {session['email']} accessed the sales page.")

        # Grafik oluşturma
        product_names = [item[0] for item in product_sales_data]
        sales_counts = [item[1] for item in product_sales_data]
        colors = plt.cm.viridis(np.linspace(0, 1, len(sales_counts)))
        fig, ax = plt.subplots()
        ax.barh(product_names, sales_counts, color=colors)
        ax.set_xlabel('Sales Count')
        ax.set_ylabel('Product Name')
        ax.set_title('Top 20 Products by Sales')

        # Grafik görselini base64 formatında kaydetme
        img = io.BytesIO()
        fig.savefig(img, format='png')
        img.seek(0)
        img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
        

        return render_template('admin_dashboard.html', sales_data=sales_data, img_base64=img_base64)

    except cx_Oracle.DatabaseError as e:
        current_app.logger.error(f"Database error: {e}")
        return render_template('error.html', error_message="Database error occurred.")
    

@dashboard_bp.route('/admin_dashboard/employee', methods=['GET', 'POST'])
def index_employee():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to employees page.")
        return redirect(url_for('auth.login'))
    
    try:
        # Veritabanı bağlantısını al
        connection = get_db_connection()
        cursor = connection.cursor()

        # Employee verilerini çekmek için SQL sorgusu
        cursor.execute("""
            SELECT 
                e.employee_id, 
                NVL(e.first_name || ' ' || e.last_name, 'N/A') AS employee_name, 
                SUM(NVL(o.order_total, 0)) AS total_sales
            FROM 
                employees e
            LEFT JOIN 
                orders o ON e.employee_id = o.employee_id
            GROUP BY 
                e.employee_id, e.first_name, e.last_name
            ORDER BY 
                total_sales DESC
            FETCH FIRST 5 ROWS ONLY
        """)
        employee_sales_data = cursor.fetchall()  # Veriyi çek

        cursor.close()
        connection.close()

        current_app.logger.info(f"User {session['email']} accessed the employees page.")

        # Grafik oluşturma
        employee_names = [item[1] for item in employee_sales_data]
        total_sales = [item[2] for item in employee_sales_data]
        colors = plt.cm.viridis(np.linspace(0, 1, len(total_sales)))
        fig, ax = plt.subplots()

        ax.barh(employee_names, total_sales, color=colors)
        ax.set_xlabel('Total Sales ($)')
        ax.set_ylabel('Employee Name')
        ax.set_title('Top 5 Employees by Order')

        # Grafik görselini base64 formatında kaydetme
        img = io.BytesIO()
        fig.savefig(img, format='png')
        img.seek(0)
        img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')

        return render_template('admin_dashboard.html', employee_sales_data=employee_sales_data, img_base64=img_base64)

    except cx_Oracle.DatabaseError as e:
        current_app.logger.error(f"Database error: {e}")
        return render_template('error.html', error_message="Database error occurred.")
    
@dashboard_bp.route('/admin_dashboard/order', methods=['GET', 'POST'])
def index_order():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to order page.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    order_details = []
    top_20_orders_by_day = []

    try:
        # Fetch the top 20 days with the most orders
        cursor.execute("""
            SELECT 
                TO_CHAR(o.order_date, 'YYYY-MM-DD') AS order_day, 
                COUNT(o.order_id) AS order_count
            FROM orders o
            GROUP BY TO_CHAR(o.order_date, 'YYYY-MM-DD')
            ORDER BY order_count DESC
            FETCH FIRST 20 ROWS ONLY
        """)
        top_20_orders_by_day = cursor.fetchall()  # Get the top 20 days with the most orders
        current_app.logger.info("Fetched top 20 days with most orders.")

        # Generate graph data
        order_days = [item[0] for item in top_20_orders_by_day]
        order_counts = [item[1] for item in top_20_orders_by_day]
        colors = plt.cm.viridis(np.linspace(0, 1, len(order_counts)))  

        # Create the bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(order_days, order_counts, color=colors)
        ax.set_xlabel('Order Date')
        ax.set_ylabel('Order Count')
        ax.set_title('Top 20 Days with Most Orders')
        ax.set_xticklabels(order_days, rotation=45, ha="right")  # Rotate labels to fit

        # Format the graph as base64 for rendering in HTML
        img = io.BytesIO()
        fig.savefig(img, format='png')
        img.seek(0)
        img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')

        # Render the template and pass the data
        return render_template('admin_dashboard.html', top_20_orders_by_day=top_20_orders_by_day, img_base64=img_base64)

    except cx_Oracle.DatabaseError as e:
        current_app.logger.error(f"Database error: {e}")
        return render_template('error.html', error_message="Database error occurred.")
    finally:
        cursor.close()
        conn.close()

@dashboard_bp.route('/admin_dashboard/customer', methods=['GET', 'POST'])
def index_customer():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to customers page.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    customers = []
    country_data = []
    country_labels = []

    try:
        # Fetch country distribution for customers
        cursor.execute('''
            SELECT COUNTRY_ID, COUNT(*) 
            FROM CUSTOMERS
            GROUP BY COUNTRY_ID
            ORDER BY COUNT(*) DESC
        ''')
        country_data = cursor.fetchall()  # Fetch country and customer count
        
        # If there are more than 10 countries, sum up the rest into "Other"
        if len(country_data) > 10:
            top_10_countries = country_data[:10]
            other_countries_count = sum([item[1] for item in country_data[10:]])
            
            # Update labels and counts to include "Other"
            country_labels = [item[0] for item in top_10_countries] + ["Other"]
            country_counts = [item[1] for item in top_10_countries] + [other_countries_count]
        else:
            country_labels = [item[0] for item in country_data]
            country_counts = [item[1] for item in country_data]
        
        # Calculate total customers
        total_customers = sum(country_counts)

        # Calculate percentage for each country
        country_percentages = [(count / total_customers) * 100 for count in country_counts]

        # Create pie chart
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.pie(country_percentages, labels=country_labels, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)
        ax.set_title('Customer Distribution by Country')

        # Format the chart as base64 for rendering in HTML
        img = io.BytesIO()
        fig.savefig(img, format='png')
        img.seek(0)
        img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')

        current_app.logger.info("Generated pie chart for country distribution.")
        
        # Render the template and pass the data
        return render_template('admin_dashboard.html', 
                               customers=customers, 
                               country_data=country_data, 
                               img_base64=img_base64)

    except cx_Oracle.DatabaseError as e:
        current_app.logger.error(f"Database error: {e}")
        return render_template('error.html', error_message="Database error occurred.")
    finally:
        cursor.close()
        conn.close()