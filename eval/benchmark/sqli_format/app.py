import sqlite3
def lookup(conn, email):
    cur = conn.cursor()
    q = "SELECT * FROM users WHERE email = '{}'".format(email)
    cur.execute(q)
    return cur.fetchone()
