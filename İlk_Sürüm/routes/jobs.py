from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import cx_Oracle
from models.database import DATABASE_CONFIG


def get_db_connection():
    connection = cx_Oracle.connect(
        DATABASE_CONFIG['user'],
        DATABASE_CONFIG['password'],
        DATABASE_CONFIG['dsn']
    )
    return connection


jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/')
def index():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to jobs index.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    jobs = cursor.execute('SELECT * FROM JOBS').fetchall()
    conn.close()
    current_app.logger.info(f"User {session['email']} accessed jobs index.")
    return render_template('jobs_index.html', jobs=jobs)

@jobs_bp.route('/add', methods=('GET', 'POST'))
def add_job():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to add job.")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        job_id = request.form['job_id']
        job_title = request.form['job_title']
        min_salary = request.form['min_salary']
        max_salary = request.form['max_salary']

        # Ensure salary values are numeric
        if not min_salary.isdigit() or not max_salary.isdigit():
            current_app.logger.warning(f"Invalid salary values entered for job {job_id}: min_salary={min_salary}, max_salary={max_salary}.")
            return render_template('jobs_add.html', error="Salary values must be numeric!", job_id=job_id, job_title=job_title,
                                   min_salary=min_salary, max_salary=max_salary)

        # Convert salary values to integers
        min_salary = int(min_salary)
        max_salary = int(max_salary)

        conn = get_db_connection()
        cursor = conn.cursor()

        # JOB_ID check
        existing_job = cursor.execute('SELECT * FROM JOBS WHERE job_id = :1', (job_id,)).fetchone()
        if existing_job:
            conn.close()
            current_app.logger.warning(f"Attempt to add existing job ID {job_id}.")
            return render_template('jobs_add.html', error="Job ID already exists!", job_id=job_id, job_title=job_title, 
                                   min_salary=min_salary, max_salary=max_salary)
        # Salary check
        if min_salary > max_salary:
            conn.close()
            current_app.logger.warning(f"Salary validation failed for job {job_id}: min_salary={min_salary} > max_salary={max_salary}.")
            return render_template('jobs_add.html', error="Minimum salary cannot be greater than maximum salary", job_id=job_id, job_title=job_title
                            ,max_salary=max_salary   )
        if min_salary <= 0:
            conn.close()
            current_app.logger.warning(f"Invalid minimum salary for job {job_id}: min_salary={min_salary}. Must be greater than zero.")
            return render_template('jobs_add.html', error="Minimum salary cannot be zero or less than zero", job_id=job_id, job_title=job_title,
                            max_salary=max_salary)
        if max_salary <= 0:
            conn.close()
            current_app.logger.warning(f"Invalid maximum salary for job {job_id}: max_salary={max_salary}. Must be greater than zero.")
            return render_template('jobs_add.html', error="Maximum salary cannot be zero or less than zero", job_id=job_id, job_title=job_title,
                            min_salary=min_salary)
        # If no issues, proceed with insertion
        cursor.execute('INSERT INTO JOBS (job_id, job_title, min_salary, max_salary) VALUES (:1, :2, :3, :4)',
                       (job_id, job_title, min_salary, max_salary))
        conn.commit()
        conn.close()
        current_app.logger.info(f"Job {job_id} ({job_title}) added by user {session['email']}.")
        return redirect(url_for('jobs.index'))
    
    return render_template('jobs_add.html')


@jobs_bp.route('/edit/<string:job_id>', methods=('GET', 'POST'))
def edit_job(job_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to edit job with ID {job_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    job = cursor.execute('SELECT * FROM JOBS WHERE job_id = :1', (job_id,)).fetchone()

    if request.method == 'POST':
        job_title = request.form['job_title']
        min_salary = request.form['min_salary']
        max_salary = request.form['max_salary']

        # Convert salary values to integers
        min_salary = int(min_salary)
        max_salary = int(max_salary)

        # Salary check
        if min_salary > max_salary:
            conn.close()
            current_app.logger.warning(f"Salary validation failed for job {job_id}: min_salary={min_salary} > max_salary={max_salary}.")
            return render_template('jobs_add.html', error="Minimum salary cannot be greater than maximum salary", job_id=job_id, job_title=job_title
                                )
        if min_salary <= 0:
            conn.close()
            current_app.logger.warning(f"Invalid minimum salary for job {job_id}: min_salary={min_salary}. Must be greater than zero.")
            return render_template('jobs_add.html', error="Minimum salary cannot be zero or less than zero", job_id=job_id, job_title=job_title,
                            max_salary=max_salary)
        if max_salary <= 0:
            conn.close()
            current_app.logger.warning(f"Invalid maximum salary for job {job_id}: max_salary={max_salary}. Must be greater than zero.")
            return render_template('jobs_add.html', error="Maximum salary cannot be zero or less than zero", job_id=job_id, job_title=job_title,
                            min_salary=min_salary)

        cursor.execute('UPDATE JOBS SET job_title = :1, min_salary = :2, max_salary = :3 WHERE job_id = :4',
                       (job_title, min_salary, max_salary, job_id))
        conn.commit()
        conn.close()
        current_app.logger.info(f"Job {job_id} updated by user {session['email']}.")
        return redirect(url_for('jobs.index'))

    conn.close()
    return render_template('jobs_edit.html', job=job)

@jobs_bp.route('/delete/<string:job_id>', methods=('POST',))
def delete_job(job_id):
    if 'email' not in session:
        current_app.logger.warning(f"Unauthorized access attempt to delete job with ID {job_id}.")
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM JOBS WHERE job_id = :1', (job_id,))
    conn.commit()
    conn.close()
    current_app.logger.info(f"Job {job_id} deleted by user {session['email']}.")
    return redirect(url_for('jobs.index'))

# Admin_Dashboarda Geçiş
@jobs_bp.route('/return_admin_dashboard')
def return_admin_dashboard():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to return to admin dashboard.")
        return redirect(url_for('auth.login'))  # Oturum yoksa login sayfasına yönlendir
    current_app.logger.info(f"User {session['email']} returned to admin dashboard.")
    return redirect(url_for('admin_dashboard'))  # Kullanıcı giriş yaptıysa dashboard'a yönlendir
