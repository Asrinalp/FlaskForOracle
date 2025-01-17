from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import cx_Oracle
from datetime import datetime

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


employee_bp = Blueprint('employee', __name__)


@employee_bp.route('/')
def employees_index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to employee index.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Filtre değerlerini alın
    filter_job = request.args.get('job_id')
    filter_department = request.args.get('department_id')
    filter_manager = request.args.get('manager_id')

    # Dinamik SQL sorgusu oluşturma
    query = '''
        SELECT 
            e.employee_id,
            e.first_name || ' ' || e.last_name AS full_name,
            e.email,
            e.phone_number,
            j.job_title,
            e.salary,
            m.first_name || ' ' || m.last_name AS manager_name,
            d.department_name
        FROM 
            employees e
        LEFT JOIN 
            employees m ON e.manager_id = m.employee_id
        LEFT JOIN 
            departments d ON e.department_id = d.department_id
        LEFT JOIN 
            jobs j ON e.job_id = j.job_id
        WHERE 1=1
    '''
    # Filtrelere göre SQL sorgusunu genişlet
    parameters = {}
    if filter_job:
        query += ' AND e.job_id = :job_id'
        parameters['job_id'] = filter_job
    if filter_department:
        query += ' AND e.department_id = :department_id'
        parameters['department_id'] = filter_department
    if filter_manager:
        query += ' AND e.manager_id = :manager_id'
        parameters['manager_id'] = filter_manager

    # Sorguyu çalıştır
    cursor.execute(query, parameters)
    employees = cursor.fetchall()

    # Filter seçenekleri için veriler
    cursor.execute('SELECT job_id, job_title FROM jobs')
    jobs = cursor.fetchall()

    cursor.execute('SELECT department_id, department_name FROM departments')
    departments = cursor.fetchall()

    cursor.execute('''
        SELECT e.employee_id, e.first_name || ' ' || e.last_name AS manager_name
        FROM employees e
        WHERE e.employee_id IN (SELECT DISTINCT manager_id FROM employees WHERE manager_id IS NOT NULL)
    ''')
    managers = cursor.fetchall()

    conn.close()

    # Şablona veri gönderme
    current_app.logger.info(f"User {session['email']} accessed employee index.")
    return render_template(
        'employees_index.html',
        employees=employees,
        jobs=jobs,
        managers=managers,
        departments=departments,
        filter_job=filter_job,
        filter_department=filter_department,
        filter_manager=filter_manager
    )





@employee_bp.route('/add', methods=('GET', 'POST'))
def add_employee():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add employee.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch departments, managers, and jobs for dropdowns
    cursor.execute('SELECT department_id, department_name FROM departments')
    departments = cursor.fetchall()

    cursor.execute('''
        SELECT e.employee_id, e.first_name || ' ' || e.last_name AS manager_name
        FROM employees e
        WHERE e.employee_id IN (SELECT DISTINCT manager_id FROM employees WHERE manager_id IS NOT NULL)
    ''')
    managers = cursor.fetchall()

    cursor.execute('SELECT job_id, job_title FROM jobs')
    jobs = cursor.fetchall()

    if request.method == 'POST':
        employee_data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'email': request.form['email'],
            'phone_number': request.form['phone_number'],
            'job_id': request.form['job_id'],
            'salary': request.form['salary'],
            'manager_id': request.form['manager_id'],
            'department_id': request.form['department_id'],
            'hire_date': request.form['hire_date']
        }

        try:
            cursor.execute('''
                INSERT INTO employees (
                    first_name, last_name, email, 
                    phone_number, job_id, salary, 
                    manager_id, department_id, hire_date
                ) VALUES (
                    :first_name, :last_name, :email,
                    :phone_number, :job_id, :salary,
                    :manager_id, :department_id, TO_DATE(:hire_date, 'YYYY-MM-DD')
                )
            ''', employee_data)

            conn.commit()
            current_app.logger.info(f"Employee {employee_data['first_name']} {employee_data['last_name']} added successfully.")
            return redirect(url_for('employee.employees_index'))

        except cx_Oracle.DatabaseError as e:
            conn.rollback()
            current_app.logger.error(f"Database error occurred: {e}")
            return render_template('employees_add.html', departments=departments, managers=managers, jobs=jobs, error="Failed to add employee.")

    conn.close()
    return render_template('employees_add.html', departments=departments, managers=managers, jobs=jobs)



   

@employee_bp.route('/edit/<int:employee_id>', methods=('GET', 'POST'))
def edit_employee(employee_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to edit employee with ID {employee_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Çalışan bilgilerini al (gerekli sütunları seçiyoruz)
    cursor.execute(''' 
        SELECT e.employee_id, e.first_name, e.last_name, e.email, e.phone_number, e.job_id, e.salary, e.manager_id, e.department_id
        FROM employees e 
        WHERE e.employee_id = :employee_id
    ''', {'employee_id': employee_id})
    employee = cursor.fetchone()

    if not employee:
        conn.close()
        current_app.logger.error(f"Employee with ID {employee_id} not found.")
        return redirect(url_for('employee.employees_index'))

    # Departman bilgileri
    cursor.execute('SELECT department_id, department_name FROM departments')
    departments = cursor.fetchall()

    # Yöneticiler bilgisi
    cursor.execute('''
        SELECT e.employee_id, e.first_name || ' ' || e.last_name AS manager_name
        FROM employees e
        WHERE e.employee_id IN (SELECT DISTINCT manager_id FROM employees WHERE manager_id IS NOT NULL)
    ''')
    managers = cursor.fetchall()

    # Geliştirilmiş çalışan sorgusu (join işlemleri ile daha fazla veri)
    query = ''' 
        SELECT e.employee_id, e.first_name , e.last_name , e.email, e.phone_number, j.job_id, e.salary, m.first_name || ' ' || m.last_name AS manager_name, d.department_name 
        FROM employees e 
        LEFT JOIN employees m ON e.manager_id = m.employee_id 
        LEFT JOIN departments d ON e.department_id = d.department_id 
        LEFT JOIN jobs j ON e.job_id = j.job_id 
        WHERE e.employee_id = :employee_id
    '''
    cursor.execute(query, {'employee_id': employee_id})
    employee_details = cursor.fetchone()

    if not employee_details:
        conn.close()
        current_app.logger.error(f"Detailed information for employee with ID {employee_id} not found.")
        return redirect(url_for('employee.employees_index'))

    if request.method == 'POST':
        # Form verilerini al
        employee_data = {
            'p_first_name': request.form.get('first_name'),
            'p_last_name': request.form.get('last_name'),
            'p_email': request.form.get('email'),
            'p_phone_number': request.form.get('phone_number'),
            'p_job_id': request.form.get('job_id'),
            'p_salary': request.form.get('salary'),
            'p_manager_id': request.form.get('manager_id'),
            'p_department_id': request.form.get('department_id'),
            'p_employee_id': employee_id
        }

        # Ref cursor oluştur
        ref_cursor = cursor.var(cx_Oracle.CURSOR)

        # Saklı yordamı çağır
        cursor.callproc('update_employee', [
            employee_data['p_employee_id'],
            employee_data['p_first_name'],
            employee_data['p_last_name'],
            employee_data['p_email'],
            employee_data['p_phone_number'],
            employee_data['p_job_id'],
            employee_data['p_salary'],
            employee_data['p_manager_id'],
            employee_data['p_department_id']
        ])

        conn.commit()
        conn.close()
        current_app.logger.info(f"Employee {employee_id} updated by user {session['email']}.")
        return redirect(url_for('employee.employees_index'))

    conn.close()
    return render_template('employees_edit.html', employee=employee_details, departments=departments, managers=managers)



@employee_bp.route('/delete/<int:employee_id>', methods=['POST'])
def delete_employee(employee_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to delete employee with ID {employee_id}.")
        return redirect(url_for('auth.login'))  # Kullanıcı giriş yapmamışsa login sayfasına yönlendir

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Çalışan kaydını sil
        cursor.execute('DELETE FROM employees WHERE employee_id = :employee_id', {'employee_id': employee_id})
        conn.commit()
        current_app.logger.info(f"Employee {employee_id} deleted by user {session['email']}.")
    except cx_Oracle.DatabaseError as e:
        conn.rollback()
        current_app.logger.error(f"Error deleting employee {employee_id}: {e}")
    finally:
        conn.close()

    # Silme işleminden sonra çalışanlar listesine yönlendir
    return redirect(url_for('employee.employees_index'))


@employee_bp.route('/return_admin_dashboard')
def return_admin_dashboard():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to return to admin dashboard.")
        return redirect(url_for('auth.login'))  # Oturum yoksa login sayfasına yönlendir
    current_app.logger.info(f"User {session['email']} returned to admin dashboard.")
    return redirect(url_for('admin_dashboard'))  # Kullanıcı giriş yaptıysa dashboard'a yönlendir


@employee_bp.route('/filter', methods=['GET'])
def filter_employees():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to filter employees.")
        return redirect(url_for('auth.login'))

    # Tek filtre parametrelerini alın
    combined_filter = request.args.get('combined_filter')  # Örneğin: "job"
    sub_filter = request.args.get('sub_filter')            # Örneğin: "FI_MGR"

    conn = get_db_connection()
    cursor = conn.cursor()

    # Dinamik SQL sorgusu oluştur
    query = '''
        SELECT 
            e.employee_id,
            e.first_name || ' ' || e.last_name AS full_name,
            e.email,
            e.phone_number,
            j.job_title,
            e.salary,
            m.first_name || ' ' || m.last_name AS manager_name,
            d.department_name
        FROM 
            employees e
        LEFT JOIN 
            employees m ON e.manager_id = m.employee_id
        LEFT JOIN 
            departments d ON e.department_id = d.department_id
        LEFT JOIN 
            jobs j ON e.job_id = j.job_id
        WHERE 1=1
    '''
    parameters = {}

    # Filtreleme koşulunu dinamik olarak ekle
    if combined_filter == "job":
        query += ' AND e.job_id = :sub_filter'
        parameters['sub_filter'] = sub_filter
    elif combined_filter == "department":
        query += ' AND e.department_id = :sub_filter'
        parameters['sub_filter'] = sub_filter
    elif combined_filter == "manager":
        query += ' AND e.manager_id = :sub_filter'
        parameters['sub_filter'] = sub_filter

    cursor.execute(query, parameters)
    employees = cursor.fetchall()

    # Filter seçenekleri için veriler
    cursor.execute('SELECT job_id, job_title FROM jobs')
    jobs = cursor.fetchall()

    cursor.execute('SELECT department_id, department_name FROM departments')
    departments = cursor.fetchall()

    cursor.execute('''
        SELECT e.employee_id, e.first_name || ' ' || e.last_name AS manager_name
        FROM employees e
        WHERE e.employee_id IN (SELECT DISTINCT manager_id FROM employees WHERE manager_id IS NOT NULL)
    ''')
    managers = cursor.fetchall()

    conn.close()

    # Şablona sadece filtrelenmiş sonuçları gönder
    return render_template(
        'employees_index.html',
        employees=employees,
        jobs=jobs,
        managers=managers,
        departments=departments,
        combined_filter=combined_filter,
        sub_filter=sub_filter
    )