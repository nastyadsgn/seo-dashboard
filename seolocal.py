"""SeoLocal — свой Seodile без сторонних сервисов.

  python seolocal.py audit  https://site.ru [--pages 200] [--speed 3]   # краулер + аудит + битые ссылки (+Lighthouse)
  python seolocal.py uptime https://site.ru [--loop 300]                # проверка доступности
  python seolocal.py track  [--port 8787]                               # сборщик трафика (для счётчика на сайте)
  python seolocal.py report https://site.ru                             # собрать отчёт из накопленных данных
"""
import argparse
import json
import os
import sys
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audit as A
import crawler as C
import report as R
import speed as S
import tracker as T
import uptime as U

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA, exist_ok=True)
DB = os.path.join(DATA, "seolocal.db")


def slug(url):
    return urlparse(url).netloc.replace(":", "_")


def build_report(url, pages=None, issues=None, health=None, broken=None, speed=None):
    path = os.path.join(DATA, slug(url) + "_audit.json")
    if pages is None:
        d = json.load(open(path, encoding="utf-8"))
        pages, issues, health, broken, speed = d["pages"], d["issues"], d["health"], d["broken"], d.get("speed")
    else:
        json.dump(dict(pages=pages, issues=issues, health=health, broken=broken, speed=speed),
                  open(path, "w", encoding="utf-8"), ensure_ascii=False)
    host = urlparse(url).netloc
    out = os.path.join(DATA, slug(url) + "_report.html")
    html = R.build(url, pages, issues, health, broken, uptime=U.stats(url, DB), speed=speed,
                   traffic=T.stats(DB, host) if T.stats(DB, host)["pageviews"] else None)
    open(out, "w", encoding="utf-8").write(html)
    return out


def build_dashboard(url, date=None, collect=False):
    """Снимок метрик в историю + docs/<сайт>/index.html по данным последнего аудита."""
    import dashboard as D
    import history as H
    root = os.path.dirname(os.path.abspath(__file__))
    d = json.load(open(os.path.join(DATA, slug(url) + "_audit.json"), encoding="utf-8"))
    host = urlparse(url).netloc
    cfg_path = os.path.join(root, "projects", slug(url) + ".json")
    cfg = json.load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else dict(name=host, url=url)
    tr = T.stats(DB, host)
    H.snapshot(slug(url), DATA, d["pages"], d["issues"], d["health"], d["broken"], d.get("speed"), U.stats(url, DB),
               tr if tr["pageviews"] else None, date)
    out_dir = os.path.join(root, "docs", slug(url))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    import collectors as CO
    if collect:
        CO.collect(host.replace("www.", ""), DATA, slug(url))
    open(out, "w", encoding="utf-8").write(D.build(cfg, H.load(slug(url), DATA), d, d.get("speed"), CO.latest(DATA, slug(url))))
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("dashboard").add_argument("url")
    w = sub.add_parser("weekly", help="аудит + снимок + дашборд (для планировщика)")
    w.add_argument("url")
    w.add_argument("--speed", type=int, default=2)
    a = sub.add_parser("audit")
    a.add_argument("url")
    a.add_argument("--pages", type=int, default=200)
    a.add_argument("--speed", type=int, default=0, help="сколько страниц проверить Lighthouse (0 — не проверять)")
    u = sub.add_parser("uptime")
    u.add_argument("url")
    u.add_argument("--loop", type=int, default=0, help="интервал в секундах")
    t = sub.add_parser("track")
    t.add_argument("--port", type=int, default=8787)
    r = sub.add_parser("report")
    r.add_argument("url")
    args = ap.parse_args()

    if args.cmd == "dashboard":
        print("Дашборд:", build_dashboard(C.norm(args.url)))
    elif args.cmd in ("audit", "weekly"):
        url = C.norm(args.url if args.url.startswith("http") else "https://" + args.url)
        if args.cmd == "weekly":
            args.pages = 150
        print("1/4 Обход сайта…")
        site = C.site_files(url)
        pages = C.crawl(url, max_pages=args.pages, seeds=site["sitemap_urls"])
        print("2/4 robots.txt и sitemap… ок")
        print("3/4 Проверка ссылок…")
        broken = A.check_links(pages)
        print("4/4 Аудит…")
        issues, health = A.run_audit(pages, site, broken)
        speed = None
        if args.speed:
            ok = [u for u, p in pages.items() if p["status"] == 200 and not p.get("non_html")][: args.speed]
            print(f"Lighthouse: {len(ok)} стр. (по ~1 мин каждая)…")
            speed = [S.lighthouse(x) for x in ok]
        U.check(url, DB)
        out = build_report(url, pages, issues, health, broken, speed)
        if args.cmd == "weekly":
            print("Дашборд:", build_dashboard(url, collect=True))
        e =sum(i["severity"] == "error" for i in issues)
        w = sum(i["severity"] == "warning" for i in issues)
        print(f"\nГотово. Страниц: {len(pages)}, здоровье: {health}/100, ошибок: {e}, предупреждений: {w}, битых ссылок: {len(broken)}")
        print("Отчёт:", out)
    elif args.cmd == "uptime":
        if args.loop:
            U.loop(args.url, DB, args.loop)
        else:
            print(U.check(args.url, DB))
    elif args.cmd == "track":
        T.serve(DB, args.port)
    elif args.cmd == "report":
        print("Отчёт:", build_report(C.norm(args.url)))


if __name__ == "__main__":
    main()
