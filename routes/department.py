from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
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


department_bp = Blueprint('department', __name__)

@department_bp.route('/')
def index_dpr():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to department index.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # employees ve departments tablolarını joinle
    query = '''
        SELECT 
            d.department_id, 
            d.department_name, 
            e.first_name || ' ' || e.last_name AS manager_name, 
            l.city
        FROM 
            departments d
        LEFT JOIN 
            employees e 
        ON 
            d.manager_id = e.employee_id
        LEFT JOIN 
            locations l
        ON 
            l.location_id = d.location_id
    '''
    cursor.execute(query)
    departments = cursor.fetchall()
    
    conn.close()
    current_app.logger.info(f"User {session['email']} accessed department index.")
    return render_template('department_index.html', departments=departments)


@department_bp.route('/add', methods=('GET', 'POST'))
def add_department():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add department.")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        department_id = request.form['department_id']
        department_name = request.form['department_name']
        manager_id = request.form['manager_id']
        location_id = request.form['location_id']

        # Location ID'nin geçerliliğini kontrol et
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM LOCATIONS WHERE location_id = :location_id', {'location_id': location_id})
        location_count = cursor.fetchone()[0]
        
        if location_count == 0:
            # Eğer location_id geçerli değilse, hata mesajı göster
            current_app.logger.warning(f"Invalid location_id {location_id} for department {department_name}.")
            return render_template('department_add.html', error="Invalid location ID. Please check the location ID.")
        
        # Eğer location_id geçerli ise, department verisini ekle
        cursor.execute(''' 
            INSERT INTO departments (department_id, department_name, manager_id, location_id) 
            VALUES (:department_id, :department_name, :manager_id, :location_id)
        ''', {
            'department_id': department_id,
            'department_name': department_name,
            'manager_id': manager_id,
            'location_id': location_id
        })

        conn.commit()
        conn.close()
        current_app.logger.info(f"Department {department_name} added by user {session['email']}.")
        return redirect(url_for('department.index_dpr'))

    return render_template('department_add.html')



@department_bp.route('/edit/<int:department_id>', methods=('GET', 'POST'))
def edit_department(department_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to edit department with ID {department_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Departman bilgilerini al
    department = cursor.execute('SELECT * FROM departments WHERE department_id = :department_id', 
                                {'department_id': department_id}).fetchone()

    if request.method == 'POST':
        department_name = request.form['department_name']
        manager_id = request.form['manager_id']
        location_id = request.form['location_id']

        # Parametreleri doğru bir şekilde geçirin
        cursor.execute('''
            UPDATE departments 
            SET department_name = :department_name, 
                manager_id = :manager_id, 
                location_id = :location_id 
            WHERE department_id = :department_id
        ''', {
            'department_name': department_name,
            'manager_id': manager_id,
            'location_id': location_id,
            'department_id': department_id
        })
        
        conn.commit()
        conn.close()
        current_app.logger.info(f"Department {department_id} updated by user {session['email']}.")
        return redirect(url_for('department.index_dpr'))

    conn.close()
    return render_template('department_edit.html', department=department)

@department_bp.route('/delete/<int:department_id>', methods=('POST',))
def delete_department(department_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to delete department with ID {department_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM departments WHERE department_id = :1', (department_id,))
    conn.commit()
    conn.close()
    current_app.logger.info(f"Department {department_id} deleted by user {session['email']}.")
    return redirect(url_for('department.index_dpr'))

# Admin_Dashboarda Geçiş
@department_bp.route('/return_admin_dashboard')
def return_admin_dashboard():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to return to admin dashboard.")
        return redirect(url_for('auth.login'))
    current_app.logger.info(f"User {session['email']} returned to admin dashboard.")
    return redirect(url_for('admin_dashboard'))
