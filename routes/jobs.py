from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, Response
import cx_Oracle
from models.database import DATABASE_CONFIG
import pandas as pd
from werkzeug.utils import secure_filename
from io import StringIO
import chardet
import csv
import xml.etree.ElementTree as ET
import json




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


# Import Jobs Endpoint
@jobs_bp.route('/import', methods=['POST'])
def import_jobs():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to import jobs.")
        return redirect(url_for('auth.login'))

    file = request.files.get('file')
    if not file:
        return redirect(url_for('jobs.index'))

    filename = secure_filename(file.filename)
    file_ext = filename.split('.')[-1].lower()

    if file_ext == 'csv':
        return handle_csv_upload(file)
    elif file_ext == 'json':
        return handle_json_upload(file)
    elif file_ext == 'xml':
        return handle_xml_upload(file)
    else:
        current_app.logger.warning(f"Unsupported file format: {file_ext}")
        return render_template('jobs_index.html', error="Unsupported file format. Only CSV, JSON, and XML are allowed.")

def handle_csv_upload(file):
    try:
        raw_data = file.read()
        encoding = chardet.detect(raw_data)['encoding']
        csv_data = StringIO(raw_data.decode(encoding))
        df = pd.read_csv(csv_data)
        return process_dataframe(df)
    except Exception as e:
        return handle_upload_error(e)

def handle_json_upload(file):
    try:
        df = pd.read_json(file)
        return process_dataframe(df)
    except Exception as e:
        return handle_upload_error(e)

def handle_xml_upload(file):
    try:
        tree = ET.parse(file)
        root = tree.getroot()
        rows = []
        for job in root.findall('job'):
            rows.append({
                'job_id': job.find('job_id').text,
                'job_title': job.find('job_title').text,
                'min_salary': int(job.find('min_salary').text),
                'max_salary': int(job.find('max_salary').text),
            })
        df = pd.DataFrame(rows)
        return process_dataframe(df)
    except Exception as e:
        return handle_upload_error(e)

def process_dataframe(df):
    df.columns = [col.strip().lower() for col in df.columns]
    required_columns = ['job_id', 'job_title', 'min_salary', 'max_salary']
    if not all(col in df.columns for col in required_columns):
        current_app.logger.warning("Missing required columns.")
        return render_template('jobs_index.html', error="Required columns are missing.")

    conn = get_db_connection()
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute('INSERT INTO JOBS (job_id, job_title, min_salary, max_salary) VALUES (:1, :2, :3, :4)',
                       (row['job_id'], row['job_title'], int(row['min_salary']), int(row['max_salary'])))
    conn.commit()
    conn.close()
    return redirect(url_for('jobs.index'))

def handle_upload_error(e):
    current_app.logger.error(f"Error processing file: {str(e)}")
    return render_template('jobs_index.html', error="An error occurred while processing the file.")

# Export Jobs Endpoint
@jobs_bp.route('/export', methods=['GET'])
def export_jobs():
    if 'email' not in session:
        current_app.logger.warning("Unauthorized access attempt to export jobs.")
        return redirect(url_for('auth.login'))

    format_type = request.args.get('format', 'csv').lower()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT job_id, job_title, min_salary, max_salary FROM JOBS')
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        if format_type == 'csv':
            return generate_csv(columns, rows)
        elif format_type == 'json':
            return generate_json(columns, rows)
        elif format_type == 'xml':
            return generate_xml(columns, rows)
        else:
            current_app.logger.warning(f"Unsupported export format: {format_type}")
            return render_template('jobs_index.html', error="Unsupported export format.")
    except Exception as e:
        current_app.logger.error(f"Error exporting jobs: {str(e)}")
        return render_template('jobs_index.html', error="An error occurred while exporting data.")

def generate_csv(columns, rows):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=jobs_export.csv'
    return response

def generate_json(columns, rows):
    data = [dict(zip(columns, row)) for row in rows]
    response = Response(json.dumps(data, indent=4), mimetype='application/json')
    response.headers['Content-Disposition'] = 'attachment; filename=jobs_export.json'
    return response

def generate_xml(columns, rows):
    root = ET.Element("jobs")
    for row in rows:
        job_element = ET.SubElement(root, "job")
        for col_name, value in zip(columns, row):
            col_element = ET.SubElement(job_element, col_name)
            col_element.text = str(value)
    xml_string = ET.tostring(root, encoding='utf-8', method='xml')
    response = Response(xml_string, mimetype='application/xml')
    response.headers['Content-Disposition'] = 'attachment; filename=jobs_export.xml'
    return response