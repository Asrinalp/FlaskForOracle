from flask import Blueprint, render_template, session, request, flash, current_app, redirect, url_for
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

user_bp = Blueprint('personal_info', __name__)

@user_bp.route('/personal_info', methods=['GET'])
def get_personal_info():
    connection = None
    user_info = {}

    try:
        connection = get_db_connection()
        if not connection:
            flash('Unable to connect to the database. Please try again later.', 'danger')
            return render_template('personal.information.html', user=user_info)

        cursor = connection.cursor()

        # Kullanıcı bilgilerini veritabanından al
        query = """
        SELECT user_id, user_name, user_role, user_email, user_password, cmp_email 
        FROM users 
        WHERE cmp_email = :email OR user_email = :email
        """
        email = session.get('email')
        cursor.execute(query, {'email': email})
        result = cursor.fetchone()

        if result:
            user_info = {
                'id': result[0],
                'name': result[1],
                'role': result[2],
                'user_email': result[3],
                'password': result[4],
                'cmp_email': result[5]
            }
        else:
            flash('User information not found.', 'warning')

    except cx_Oracle.Error as error:
        current_app.logger.error(f"Database error: {error}")
        flash('An error occurred while retrieving your information.', 'danger')

    finally:
        if connection:
            connection.close()

    return render_template('personal.information.html', user=user_info)

@user_bp.route('/update_user', methods=['POST'])
def update_user():
    connection = None

    try:
        # İstekten güncellenmiş bilgileri al
        user_data = request.get_json()
        updated_name = user_data.get('name')
        updated_password = user_data.get('password')
        user_id = user_data.get('id')

        if not updated_name or not updated_password or not user_id:
            return {'success': False, 'message': 'Name, password, and user ID cannot be empty.'}, 400

        # Veritabanına bağlan
        connection = get_db_connection()
        if not connection:
            return {'success': False, 'message': 'Unable to connect to the database.'}, 500
        
        cursor = connection.cursor()

        # Kullanıcı bilgisini güncelle
        update_query = """
        UPDATE users 
        SET user_name = :name, user_password = :password 
        WHERE user_id = :id
        """
        cursor.execute(update_query, {'name': updated_name, 'password': updated_password, 'id': user_id})

        connection.commit()

        return {'success': True, 'message': 'Information updated successfully.'}

    except cx_Oracle.DatabaseError as error:
        error_obj, = error.args
        current_app.logger.error(f"Database error: {error_obj.message}, SQLCode: {error_obj.code}, SQL: {error_obj.context}")
        return {'success': False, 'message': 'An error occurred while updating your information.'}, 500

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return {'success': False, 'message': 'An unexpected error occurred.'}, 500

    finally:
        if connection:
            try:
                connection.close()
            except cx_Oracle.Error as close_error:
                current_app.logger.warning(f"Error while closing the connection: {close_error}")

@user_bp.route('/all_users', methods=['GET','POST'])
def get_all_user_information():
    connection = None
    users_info = []

    try:
        connection = get_db_connection()
        if not connection:
            flash('Unable to connect to the database. Please try again later.', 'danger')
            return render_template('all_users.html', users=users_info)

        cursor = connection.cursor()

        # Tüm kullanıcı bilgilerini veritabanından al
        query = """
        SELECT user_id, user_name, user_role, user_email, user_password, cmp_email 
        FROM users
        """
        cursor.execute(query)
        results = cursor.fetchall()

        if results:
            for result in results:
                users_info.append({
                    'id': result[0],
                    'name': result[1],
                    'role': result[2],
                    'user_email': result[3],
                    'password': result[4],
                    'cmp_email': result[5]
                })
        else:
            flash('No users found.', 'warning')

    except cx_Oracle.Error as error:
        current_app.logger.error(f"Database error: {error}")
        flash('An error occurred while retrieving user information.', 'danger')

    finally:
        if connection:
            connection.close()

    return render_template('all_users.html', users=users_info)

@user_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def user_edit(user_id):
    connection = None
    user_info = {}

    try:
        connection = get_db_connection()
        if not connection:
            flash('Unable to connect to the database. Please try again later.', 'danger')
            return render_template('user_edit.html', user=user_info)

        cursor = connection.cursor()

        # Kullanıcı bilgilerini al
        query = """
        SELECT user_id, user_name, user_password, user_role, user_email, cmp_email 
        FROM users
        WHERE user_id = :id
        """
        cursor.execute(query, {'id': user_id})
        result = cursor.fetchone()

        if result:
            user_info = {
                'id': result[0],
                'name': result[1],
                'password': result[2],
                'role': result[3],
                'user_email': result[4],
                'cmp_email': result[5]
            }
        else:
            flash('User not found.', 'warning')

        # POST isteği ile verileri kaydetme
        if request.method == 'POST':
            user_name = request.form['user_name']
            user_role = request.form['user_role']
            user_email = request.form['user_email']
            company_email = request.form['company_email']

            # Veritabanını güncelleme
            update_query = """
            UPDATE users 
            SET user_name = :user_name, user_role = :user_role, user_email = :user_email, cmp_email = :company_email
            WHERE user_id = :user_id
            """
            cursor.execute(update_query, {
                'user_name': user_name,
                'user_role': user_role,
                'user_email': user_email,
                'company_email': company_email,
                'user_id': user_id
            })
            connection.commit()

            flash('User updated successfully!', 'success')
            return redirect(url_for('personal_info.get_all_user_information', user_id=user_id))

    except cx_Oracle.Error as error:
        current_app.logger.error(f"Database error: {error}")
        flash('An error occurred while retrieving or updating user information.', 'danger')

    finally:
        if connection:
            connection.close()

    return render_template('user_edit.html', user=user_info)

@user_bp.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
def user_delete(user_id):
    connection = None

    try:
        connection = get_db_connection()
        if not connection:
            flash('Unable to connect to the database. Please try again later.', 'danger')
            return redirect(url_for('personal_info.get_all_user_information'))

        cursor = connection.cursor()

        # Kullanıcıyı veritabanından silme
        delete_query = """
        DELETE FROM users WHERE user_id = :user_id
        """
        cursor.execute(delete_query, {'user_id': user_id})
        connection.commit()

        flash('User deleted successfully!', 'success')
        return redirect(url_for('personal_info.get_all_user_information'))

    except cx_Oracle.Error as error:
        current_app.logger.error(f"Database error: {error}")
        flash('An error occurred while deleting the user.', 'danger')

    finally:
        if connection:
            connection.close()

    return redirect(url_for('personal_info.get_all_user_information'))