from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from google.oauth2 import id_token
from google.auth.transport import requests
import cx_Oracle

DATABASE_CONFIG = {
    'user': 'USER1',
    'password': '1234',
    'dsn': 'localhost:1521/XEPDB1'
}

auth_bp = Blueprint('auth', __name__)

def get_db_connection():
    connection = cx_Oracle.connect(
        DATABASE_CONFIG['user'],
        DATABASE_CONFIG['password'],
        DATABASE_CONFIG['dsn']
    )
    return connection

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_type = request.form.get('login_type')

        # **1. Email ve Şifre ile Giriş**
        if login_type == "standard":
            email = request.form.get('email')
            password = request.form.get('password')

            conn = get_db_connection()
            cursor = conn.cursor()

            query = """
                SELECT USER_ROLE, USER_NAME 
                FROM USERS 
                WHERE USER_EMAIL = :email AND USER_PASSWORD = :password
            """
            cursor.execute(query, {'email': email, 'password': password})
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                user_role, user_name = user
                session['email'] = email
                session['role'] = user_role
                session['name'] = user_name

                # Kullanıcının rolüne göre yönlendirme
                if user_role.lower() == 'admin':
                    return redirect(url_for('dashboard.admin_dashboard'))
                else:
                    return redirect(url_for('dashboard.worker_dashboard'))
            else:
                return render_template('login.html', error_message="Invalid email or password.")

        # **2. Google ile Giriş**
        elif login_type == "google":
            google_token = request.form.get('google_token')
            try:
                # Google'dan kullanıcı kimliği doğrulama
                google_user = id_token.verify_oauth2_token(
                    google_token, requests.Request(),
                    "998396546977-t0hilul0lj44adp5osbaj31eulf4g8ek.apps.googleusercontent.com"
                )
                email = google_user.get('email')

                # Veritabanında CMP_EMAIL ile kullanıcıyı kontrol et
                conn = get_db_connection()
                cursor = conn.cursor()

                query = """
                    SELECT USER_ROLE, USER_NAME 
                    FROM USERS 
                    WHERE CMP_EMAIL = :email
                """
                cursor.execute(query, {'email': email})
                user = cursor.fetchone()

                cursor.close()
                conn.close()

                if user:
                    user_role, user_name = user
                    session['email'] = email
                    session['role'] = user_role
                    session['name'] = user_name

                    # Kullanıcının rolüne göre yönlendirme
                    if user_role.lower() == 'admin':
                        return redirect(url_for('dashboard.admin_dashboard'))
                    else:
                        return redirect(url_for('dashboard.worker_dashboard'))
                else:
                    return render_template('login.html', error_message="Unauthorized email. Access denied.")

            except ValueError as e:
                return render_template('login.html', error_message="Google login failed. Please try again.")

    # GET isteği ile login ekranını göster
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
