"""HTML-отчёт одним файлом."""
import html
import time

E = html.escape
SEV_RU = {"error": "Ошибка", "warning": "Предупреждение", "notice": "Замечание"}
CODE_RU = {
    "no_title": "Нет title", "title_long": "Длинный title", "title_short": "Короткий title", "dup_title": "Дубли title",
    "no_description": "Нет description", "desc_long": "Длинный description", "desc_short": "Короткий description",
    "dup_description": "Дубли description", "no_h1": "Нет H1", "multi_h1": "Несколько H1", "noindex": "noindex",
    "no_canonical": "Нет canonical", "canonical_other": "Canonical на другой URL", "no_viewport": "Нет viewport",
    "no_lang": "Нет lang", "no_og": "Нет Open Graph", "thin": "Мало текста", "img_alt": "Картинки без alt",
    "slow_response": "Медленный ответ", "heavy_html": "Тяжёлый HTML", "no_schema": "Нет schema.org",
    "no_links": "Нет внутренних ссылок", "redirect": "Редирект", "redirect_chain": "Цепочка редиректов",
    "status_4xx": "Ошибка 4xx", "status_5xx": "Ошибка 5xx", "fetch_error": "Страница не загрузилась",
    "broken_link": "Битые ссылки", "orphan": "Страница-сирота", "not_in_sitemap": "Нет в sitemap",
    "sitemap_not_crawled": "Sitemap: URL не найден", "no_https": "Нет HTTPS", "no_robots": "Нет robots.txt",
    "no_sitemap": "Нет sitemap.xml",
}
CSS = """body{font:15px/1.5 system-ui,Segoe UI,sans-serif;margin:0;background:#f6f5f1;color:#1d1d1b}
main{max-width:1100px;margin:0 auto;padding:24px 16px 60px}h1{margin:0 0 4px}h2{margin:36px 0 10px}
.cards{display:flex;gap:12px;flex-wrap:wrap}.card{background:#fff;border-radius:10px;padding:14px 18px;min-width:130px;box-shadow:0 1px 3px #0001}
.card b{display:block;font-size:26px}.muted{color:#777}table{border-collapse:collapse;width:100%;background:#fff;border-radius:10px;overflow:hidden;font-size:13.5px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid #eee;vertical-align:top}th{background:#efede6}
.error{color:#b3261e}.warning{color:#a15c00}.notice{color:#555}.ok{color:#1b7a3a}
a{color:#1a5fb4;text-decoration:none;word-break:break-all}details{background:#fff;border-radius:10px;padding:8px 14px;margin:6px 0}
summary{cursor:pointer;font-weight:600}.bar{background:#2f6f4f;height:8px;border-radius:4px}"""


def _tbl(head, rows):
    return "<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>" + "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>"


def build(url, pages, issues, health, broken, uptime=None, speed=None, traffic=None):
    ok = [p for p in pages.values() if p["status"] and p["status"] < 400 and not p.get("non_html")]
    cnt = {s: sum(1 for i in issues if i["severity"] == s) for s in SEV_RU}
    h = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
         f"<title>SEO-отчёт {E(url)}</title><style>{CSS}</style><main>",
         f"<h1>SEO-отчёт: {E(url)}</h1><div class=muted>{time.strftime('%d.%m.%Y %H:%M')}</div><h2>Сводка</h2><div class=cards>",
         f"<div class=card><b class={'ok' if health >= 80 else 'warning' if health >= 50 else 'error'}>{health}</b>здоровье сайта</div>",
         f"<div class=card><b>{len(pages)}</b>страниц просканировано</div>",
         f"<div class=card><b class=error>{cnt['error']}</b>ошибок</div><div class=card><b class=warning>{cnt['warning']}</b>предупреждений</div>",
         f"<div class=card><b>{cnt['notice']}</b>замечаний</div><div class=card><b class=error>{len(broken)}</b>битых ссылок</div></div>"]

    # Аудит по типам
    by = {}
    for i in issues:
        by.setdefault((i["severity"], i["code"]), []).append(i)
    h.append("<h2>Аудит</h2>")
    for (sev, code), items in sorted(by.items(), key=lambda kv: (list(SEV_RU).index(kv[0][0]), -len(kv[1]))):
        rows = "".join(f"<tr><td><a href='{E(i['url'])}'>{E(i['url'])}</a></td><td>{E(i['message'])}</td></tr>" if i["url"]
                       else f"<tr><td colspan=2>{E(i['message'])}</td></tr>" for i in items)
        h.append(f"<details><summary class={sev}>{SEV_RU[sev]}: {E(CODE_RU.get(code, code))} — {len(items)}</summary><table>{rows}</table></details>")

    # Страницы
    h.append("<h2>Страницы</h2>")
    h.append(_tbl(["URL", "Код", "Title", "H1", "Слов", "Ответ, мс"],
                  [[f"<a href='{E(p['url'])}'>{E(p['url'])}</a>", p["status"] or "ERR", E(p["title"][:70]),
                    E((p["h1"] or [""])[0][:50]), p["words"], p["ms"]] for p in sorted(pages.values(), key=lambda x: x["url"])]))

    if uptime:
        h.append(f"<h2>Доступность</h2><div class=cards><div class=card><b>{uptime['uptime_pct']}%</b>uptime</div>"
                 f"<div class=card><b>{uptime['avg_ms']} мс</b>средний ответ</div><div class=card><b>{uptime['checks']}</b>проверок</div></div>")
    if speed:
        h.append("<h2>Скорость (Lighthouse, мобильная версия)</h2>")
        rows = []
        for s in speed:
            if s.get("error"):
                rows.append([E(s["url"]), E(s["error"]), "", "", "", ""])
            else:
                sc = s["scores"]
                rows.append([E(s["url"]), sc.get("performance"), sc.get("seo"), E(s["lcp"]), E(s["cls"]), E(s["tbt"])])
        h.append(_tbl(["Страница", "Скорость", "SEO", "LCP", "CLS", "TBT"], rows))
        for s in speed:
            if not s.get("error") and s["opportunities"]:
                h.append(f"<details><summary>Что ускорить: {E(s['url'])}</summary><ul>" +
                         "".join(f"<li>{E(o['title'])} {E(o['saving'])}</li>" for o in s["opportunities"]) + "</ul></details>")
    if traffic:
        h.append(f"<h2>Трафик (собственный счётчик, 28 дней)</h2><div class=cards><div class=card><b>{traffic['visitors']}</b>посетителей</div>"
                 f"<div class=card><b>{traffic['pageviews']}</b>просмотров</div>"
                 f"<div class=card><b>{traffic['mobile_pct'] if traffic['mobile_pct'] is not None else '—'}%</b>с телефонов</div></div>")
        mx = max([r[1] for r in traffic["by_day"]] or [1])
        h.append(_tbl(["День", "Просмотры", "Посетители", ""],
                      [[d, v, u, f"<div class=bar style='width:{int(v * 200 / mx)}px'></div>"] for d, v, u in traffic["by_day"]]))
        h.append("<h2>Источники</h2>" + _tbl(["Источник", "Тип", "Посетителей"], [[E(s), k, c] for s, k, c in traffic["sources"]]))
        h.append("<h2>Популярные страницы</h2>" + _tbl(["Страница", "Просмотров"], [[E(p), c] for p, c in traffic["top_pages"]]))
    h.append("</main>")
    return "".join(h)
