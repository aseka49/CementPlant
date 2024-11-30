import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname='dinara', user='postgres', password='aseka', host='localhost'
    )