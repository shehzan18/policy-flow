def totals(conn, order_ids):
    out = []
    for oid in order_ids:
        cur = conn.execute("SELECT SUM(amount) FROM items WHERE order_id = ?", (oid,))
        out.append(cur.fetchone()[0])
    return out
