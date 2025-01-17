import cx_Oracle
from config import DATABASE_CONFIG

def get_db_connection():
    connection = cx_Oracle.connect(
        DATABASE_CONFIG['user'],
        DATABASE_CONFIG['password'],
        DATABASE_CONFIG['dsn']
    )
    return connection
