from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import cx_Oracle
import google_auth_oauthlib.flow
import os
import pathlib
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport import requests as google_requests
from googleapiclient.discovery import build


DATABASE_CONFIG = {
    'user': 'USER1',
    'password': '1234',
    'dsn': 'localhost:1521/XEPDB1'
}

# Google OAuth Configuration
GOOGLE_CLIENT_SECRETS_FILE = 'C:\\Users\\batur\\Downloads\\İlk_Sürüm\\client_secrets.json'
GOOGLE_CLIENT_ID = "520007776779-8esebgif304425mggfu9sootlqthd94o.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secrets.json")
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']

def get_db_connection():
    connection = cx_Oracle.connect(
        DATABASE_CONFIG['user'],
        DATABASE_CONFIG['password'],
        DATABASE_CONFIG['dsn']
    )
    return connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in session:
        current_app.logger.info(f"User {session['email']} already logged in. Redirecting to dashboard.")
        return redirect(url_for('dashboard.admin_dashboard'))

    if request.method == 'POST':
        if request.form.get('login_type') == 'standard':
            email = request.form.get('email')
            password = request.form.get('password')

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""SELECT * FROM USERS WHERE USER_EMAIL = :1 AND USER_PASSWORD = :2""", (email.strip(), password.strip()))
            user = cursor.fetchone()
            conn.close()

            current_app.logger.debug(f"Login attempt with email: {email}")

            if user:
                session['email'] = email
                session['name'] = f"{user[1]}|{user[2]}"
                if user[2] == 'Admin':
                    current_app.logger.info(f"User {email} logged in successfully with role {user[2]}.")
                    return redirect(url_for('dashboard.admin_dashboard'))
                elif user[2] == 'Employee':
                    current_app.logger.info(f"User {email} logged in successfully with role {user[2]}.")
                    return redirect(url_for('dashboard.worker_dashboard'))
                else:
                    error_message = 'Invalid role.'
                    current_app.logger.warning(f"Invalid role for user {email}.")
                    return render_template('login.html', error_message=error_message)
            else:
                error_message = 'Login failed. Please try again.'
                current_app.logger.warning(f"Failed login attempt with email: {email}")
                return render_template('login.html', error_message=error_message)

        elif request.form.get('login_type') == 'google':
            return redirect(url_for('auth.google_login'))

    return render_template('login.html')

@auth_bp.route('/google-login')
def google_login():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        client_secrets_file=client_secrets_file,
        scopes=GOOGLE_SCOPES,
        redirect_uri='http://127.0.0.1:5001/users/personal_info'
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    
    session['google_auth_state'] = state
    current_app.logger.debug(f"Authorization URL: {authorization_url}")  # Debug log for the URL.
    
    return redirect(authorization_url)

@auth_bp.route('/google-callback')
def google_callback():
    state = session.get('google_auth_state')
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=GOOGLE_SCOPES,
        state=state,  
        redirect_uri=url_for('auth.google-callback', _external=True)
    )
    
    try:
        flow.fetch_token(authorization_response=request.url)
        current_app.logger.info(f"Successfully fetched token for state {state}")
    except Exception as e:
        current_app.logger.error(f"Token fetch failed: {e}")
        return render_template('user_edit.html', error_message=f"Google authentication failed: {e}")

    credentials = flow.credentials

    try:
        user_info = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo', 
            headers={'Authorization': f'Bearer {credentials.token}'}
        ).json()
        current_app.logger.debug(f"User info fetched: {user_info}")
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching user info: {e}")
        return render_template('user_edit.html', error_message="Failed to fetch user info.")

    email = user_info.get('email')
    current_app.logger.debug(f"Google email: {email}")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT * FROM USERS WHERE USER_EMAIL = :1""", (email,))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['email'] = email
        session['name'] = f"{user[1]}|{user[2]}"
        
        current_app.logger.info(f"User {email} logged in successfully with role {user[2]}.")

        if user[2] == 'Admin':
            return redirect(url_for('dashboard.admin_dashboard'))
        elif user[2] == 'User':
            return redirect(url_for('dashboard.worker_dashboard'))
        else:
            current_app.logger.warning(f"User {email} has an invalid role. Redirecting to login.")
            return redirect(url_for('auth.login'))
    else:
        error_message = 'This Google account is not registered in the system.'
        current_app.logger.warning(f"Google email {email} not found in database.")
        return render_template('login.html', error_message=error_message)

@auth_bp.route('/logout')
def logout():
    session.pop('email', None)
    current_app.logger.info(f"User logged out.")
    return redirect(url_for('auth.login'))
