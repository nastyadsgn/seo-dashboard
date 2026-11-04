"""Uptime-монитор: проверка доступности, история в SQLite."""
import sqlite3
import time

from crawler import fetch


def _db(path):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS uptime(ts INTEGER, url TEXT, status INT, ms INT, ok INT, error TEXT)")
    return con


def check(url, db_path):
    r = fetch(url, timeout=20)
    ok = 1 if 200 <= r["status"] < 400 else 0
    con = _db(db_path)
    con.execute("INSERT INTO uptime VALUES(?,?,?,?,?,?)", (int(time.time()), url, r["status"], r["ms"], ok, r["error"]))
    con.commit()
    con.close()
    return dict(ok=bool(ok), status=r["status"], ms=r["ms"], error=r["error"])


def loop(url, db_path, every=300, log=print):
    log(f"Слежу за {url} каждые {every} с. Остановить: Ctrl+C")
    while True:
        r = check(url, db_path)
        log(time.strftime("%H:%M:%S"), "OK" if r["ok"] else "ПАДЕНИЕ", r["status"], f"{r['ms']} мс", r["error"] or "")
        time.sleep(every)


def stats(url, db_path, days=30):
    con = _db(db_path)
    since = int(time.time()) - days * 86400
    rows = con.execute("SELECT ts,status,ms,ok,error FROM uptime WHERE url=? AND ts>=? ORDER BY ts", (url, since)).fetchall()
    con.close()
    if not rows:
        return None
    total = len(rows)
    up = sum(r[3] for r in rows)
    return dict(checks=total, uptime_pct=round(up * 100 / total, 2), avg_ms=round(sum(r[2] for r in rows) / total),
                last=rows[-1], downs=[r for r in rows if not r[3]][-10:])
