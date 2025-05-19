import cx_Oracle

def get_connection():
    return cx_Oracle.connect("USER/PASSWORD@192.168.0.5:1521/oracle")
