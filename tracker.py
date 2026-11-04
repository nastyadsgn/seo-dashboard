"""Собственный счётчик трафика: маленький сервер-сборщик + JS-сниппет для сайта.
IP не сохраняется. Источник определяется по referrer (поисковики прячут сами запросы — это ограничение интернета, а не инструмента).
"""
import json
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SNIPPET = """(function(){try{
var s=document.currentScript,u=s.src.replace(/\\/t\\.js.*$/,'');
var k='sl_sid',id=localStorage.getItem(k);if(!id){id=Math.random().toString(36).slice(2)+Date.now().toString(36);localStorage.setItem(k,id);}
var q=new URLSearchParams({p:location.pathname+location.search,r:document.referrer,s:id,w:screen.width,h:location.hostname,t:document.title.slice(0,120)});
var img=new Image();img.src=u+'/hit?'+q.toString();
}catch(e){}})();"""

ENGINES = {"google.": "Google", "yandex.": "Яндекс", "ya.ru": "Яндекс", "bing.com": "Bing", "duckduckgo.com": "DuckDuckGo",
           "mail.ru": "Mail.ru", "t.me": "Telegram", "vk.com": "VK", "instagram.com": "Instagram", "facebook.com": "Facebook",
           "youtube.com": "YouTube"}
SEARCH = {"Google", "Яндекс", "Bing", "DuckDuckGo", "Mail.ru"}
GIF = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"


def classify(ref, own_host):
    if not ref:
        return "Прямой заход", "direct"
    host = urlparse(ref).netloc.lower()
    if own_host and own_host in host:
        return "Внутренний", "internal"
    for key, name in ENGINES.items():
        if key in host:
            return name, ("search" if name in SEARCH else "social")
    return host or "Прямой заход", "referral"


def _db(path):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS hits(ts INT, host TEXT, path TEXT, title TEXT, source TEXT, kind TEXT, sid TEXT, width INT)")
    con.execute("CREATE INDEX IF NOT EXISTS i_hits ON hits(host, ts)")
    return con


def serve(db_path, port=8787, log=print):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/t.js":
                body = SNIPPET.encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript")
                self.send_header("Cache-Control", "max-age=3600")
                self.end_headers()
                self.wfile.write(body)
            elif u.path == "/hit":
                q = {k: v[0] for k, v in parse_qs(u.query).items()}
                host = q.get("h", "")
                name, kind = classify(q.get("r", ""), host)
                con = _db(db_path)
                con.execute("INSERT INTO hits VALUES(?,?,?,?,?,?,?,?)",
                            (int(time.time()), host, q.get("p", "/")[:300], q.get("t", ""), name, kind, q.get("s", "")[:40],
                             int(q.get("w", 0) or 0)))
                con.commit()
                con.close()
                self.send_response(200)
                self.send_header("Content-Type", "image/gif")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(GIF)
            else:
                self.send_response(404)
                self.end_headers()

    log(f"Сборщик трафика: http://0.0.0.0:{port}/t.js  (Ctrl+C — остановить)")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


def stats(db_path, host, days=28):
    con = _db(db_path)
    since = int(time.time()) - days * 86400
    q = lambda sql, *a: con.execute(sql, (host, since, *a)).fetchall()
    out = dict(
        pageviews=q("SELECT COUNT(*) FROM hits WHERE host=? AND ts>=?")[0][0],
        visitors=q("SELECT COUNT(DISTINCT sid) FROM hits WHERE host=? AND ts>=?")[0][0],
        by_day=q("SELECT date(ts,'unixepoch','localtime'),COUNT(*),COUNT(DISTINCT sid) FROM hits WHERE host=? AND ts>=? GROUP BY 1 ORDER BY 1"),
        top_pages=q("SELECT path,COUNT(*) c FROM hits WHERE host=? AND ts>=? GROUP BY 1 ORDER BY c DESC LIMIT 15"),
        sources=q("SELECT source,kind,COUNT(DISTINCT sid) c FROM hits WHERE host=? AND ts>=? GROUP BY 1,2 ORDER BY c DESC LIMIT 15"),
        mobile_pct=None)
    tot = q("SELECT COUNT(*) FROM hits WHERE host=? AND ts>=? AND width>0")[0][0]
    if tot:
        out["mobile_pct"] = round(q("SELECT COUNT(*) FROM hits WHERE host=? AND ts>=? AND width>0 AND width<768")[0][0] * 100 / tot)
    con.close()
    return out
