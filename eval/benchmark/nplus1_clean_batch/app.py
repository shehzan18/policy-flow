def totals(conn, order_ids):
    qs = ",".join("?" * len(order_ids))
    cur = conn.execute(f"SELECT order_id, SUM(amount) FROM items WHERE order_id IN ({qs}) GROUP BY order_id", order_ids)
    return dict(cur.fetchall())
