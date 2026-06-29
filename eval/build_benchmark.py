"""Generates a labeled benchmark of code fixtures for evaluating PolicyGate.

Run once:  python eval/build_benchmark.py
Creates eval/benchmark/<case_id>/<file>.py and eval/benchmark/labels.json
Each label is a list of [rule_id, filename] pairs that SHOULD be detected.
Clean cases have an empty expected list (used to measure false positives / precision).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "benchmark")

# (case_id, {filename: content}, expected[[rule_id, filename]])
CASES = [
    # ---- SEC-SQLI positives ----
    ("sqli_concat", {"app.py":
        'import sqlite3\n'
        'def get(conn, uid):\n'
        '    cur = conn.cursor()\n'
        '    cur.execute("SELECT * FROM users WHERE id = \'" + uid + "\'")\n'
        '    return cur.fetchone()\n'},
     [["SEC-SQLI", "app.py"]]),
    ("sqli_fstring", {"app.py":
        'import sqlite3\n'
        'def find(conn, name):\n'
        '    cur = conn.cursor()\n'
        '    cur.execute(f"SELECT * FROM users WHERE name = \'{name}\'")\n'
        '    return cur.fetchall()\n'},
     [["SEC-SQLI", "app.py"]]),
    ("sqli_format", {"app.py":
        'import sqlite3\n'
        'def lookup(conn, email):\n'
        '    cur = conn.cursor()\n'
        '    q = "SELECT * FROM users WHERE email = \'{}\'".format(email)\n'
        '    cur.execute(q)\n'
        '    return cur.fetchone()\n'},
     [["SEC-SQLI", "app.py"]]),
    # ---- SEC-SQLI clean (negative) ----
    ("sqli_clean_param", {"app.py":
        'import sqlite3\n'
        'def get(conn, uid):\n'
        '    cur = conn.cursor()\n'
        '    cur.execute("SELECT * FROM users WHERE id = ?", (uid,))\n'
        '    return cur.fetchone()\n'},
     []),

    # ---- SEC-VALIDATION positives ----
    ("validation_raw_body", {"app.py":
        'from fastapi import FastAPI, Request\n'
        'app = FastAPI()\n'
        '@app.post("/users")\n'
        'async def create(request: Request):\n'
        '    data = await request.json()\n'
        '    return {"created": data["name"]}\n'},
     [["SEC-VALIDATION", "app.py"]]),
    ("validation_raw_param", {"app.py":
        'from fastapi import FastAPI\n'
        'app = FastAPI()\n'
        '@app.get("/calc")\n'
        'def calc(value):\n'
        '    return {"result": int(value) * 2}\n'},
     [["SEC-VALIDATION", "app.py"]]),
    # ---- SEC-VALIDATION clean ----
    ("validation_clean_pydantic", {"app.py":
        'from fastapi import FastAPI\n'
        'from pydantic import BaseModel\n'
        'app = FastAPI()\n'
        'class User(BaseModel):\n'
        '    name: str\n'
        '@app.post("/users")\n'
        'def create(user: User):\n'
        '    return {"created": user.name}\n'},
     []),

    # ---- PERF-NPLUSONE positives ----
    ("nplus1_loop_query", {"app.py":
        'def totals(conn, order_ids):\n'
        '    out = []\n'
        '    for oid in order_ids:\n'
        '        cur = conn.execute("SELECT SUM(amount) FROM items WHERE order_id = ?", (oid,))\n'
        '        out.append(cur.fetchone()[0])\n'
        '    return out\n'},
     [["PERF-NPLUSONE", "app.py"]]),
    ("nplus1_orm_loop", {"app.py":
        'def enrich(session, users):\n'
        '    for u in users:\n'
        '        u.profile = session.query(Profile).filter_by(user_id=u.id).first()\n'
        '    return users\n'},
     [["PERF-NPLUSONE", "app.py"]]),
    # ---- PERF-NPLUSONE clean ----
    ("nplus1_clean_batch", {"app.py":
        'def totals(conn, order_ids):\n'
        '    qs = ",".join("?" * len(order_ids))\n'
        '    cur = conn.execute(f"SELECT order_id, SUM(amount) FROM items WHERE order_id IN ({qs}) GROUP BY order_id", order_ids)\n'
        '    return dict(cur.fetchall())\n'},
     []),

    # ---- TEST-COVERAGE positives (non-test file, no test present) ----
    ("coverage_untested_fn", {"calc.py":
        'def discount(price, pct):\n'
        '    if pct < 0 or pct > 100:\n'
        '        raise ValueError("bad pct")\n'
        '    return price * (1 - pct / 100)\n'},
     [["TEST-COVERAGE", "calc.py"]]),
    ("coverage_untested_two", {"bank.py":
        'def transfer(acct, amount):\n'
        '    if amount <= 0:\n'
        '        raise ValueError\n'
        '    acct.balance -= amount\n'
        '    return acct.balance\n'},
     [["TEST-COVERAGE", "bank.py"]]),
    # ---- TEST-COVERAGE clean (test present alongside) ----
    ("coverage_clean_tested", {
        "calc.py":
        'def discount(price, pct):\n'
        '    return price * (1 - pct / 100)\n',
        "test_calc.py":
        'from calc import discount\n'
        'def test_discount():\n'
        '    assert discount(100, 10) == 90\n'},
     []),

    # ---- Mixed: two real violations in one file ----
    ("mixed_sqli_nplus1", {"app.py":
        'def report(conn, ids):\n'
        '    rows = []\n'
        '    for i in ids:\n'
        '        cur = conn.execute("SELECT * FROM t WHERE id = \'" + str(i) + "\'")\n'
        '        rows.append(cur.fetchone())\n'
        '    return rows\n'},
     [["SEC-SQLI", "app.py"], ["PERF-NPLUSONE", "app.py"]]),

    # ---- Fully clean files (strong precision signal: must flag NOTHING) ----
    ("clean_pure_math", {"util.py":
        'def add(a, b):\n'
        '    return a + b\n'
        'def mul(a, b):\n'
        '    return a * b\n',
        "test_util.py":
        'from util import add, mul\n'
        'def test_add(): assert add(2, 3) == 5\n'
        'def test_mul(): assert mul(2, 3) == 6\n'},
     []),
    ("clean_string_helpers", {"text.py":
        'def slugify(s):\n'
        '    return s.strip().lower().replace(" ", "-")\n',
        "test_text.py":
        'from text import slugify\n'
        'def test_slugify(): assert slugify(" Hi There ") == "hi-there"\n'},
     []),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    labels = {}
    for case_id, files, expected in CASES:
        cdir = os.path.join(OUT, case_id)
        os.makedirs(cdir, exist_ok=True)
        for fname, content in files.items():
            with open(os.path.join(cdir, fname), "w", encoding="utf-8") as f:
                f.write(content)
        labels[case_id] = {"files": list(files), "expected": expected}
    with open(os.path.join(OUT, "labels.json"), "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)

    pos = sum(1 for _, _, e in CASES if e)
    neg = sum(1 for _, _, e in CASES if not e)
    print(f"built {len(CASES)} cases -> {OUT}")
    print(f"  {pos} cases with violations, {neg} clean cases (for precision)")
    print(f"  total labeled violations: {sum(len(e) for _,_,e in CASES)}")


if __name__ == "__main__":
    main()