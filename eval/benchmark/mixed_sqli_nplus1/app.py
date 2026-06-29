def report(conn, ids):
    rows = []
    for i in ids:
        cur = conn.execute("SELECT * FROM t WHERE id = '" + str(i) + "'")
        rows.append(cur.fetchone())
    return rows
