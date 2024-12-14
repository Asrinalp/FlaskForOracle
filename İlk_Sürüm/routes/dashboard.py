from flask import Blueprint, render_template, session, redirect, url_for ,current_app
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
        current_app.logger.warning("Unauthorized access attempt to worker dashboard.")
        return redirect(url_for('auth.login'))
    current_app.logger.info(f"User {session['email']} accessed the worker dashboard.")
    return render_template('worker_dashboard.html')
