"""Дашборд проекта: один HTML-файл без внешних библиотек. Метрики из истории + этапы карты SEO-проекта."""
import html

E = html.escape

STAGES = [
    ("0", "Контекст, доступы, цели", "Метрика/GA4/GTM, цели проверены, сверка с CRM"),
    ("1", "Baseline и точки роста", "Вебмастер/GSC за 3–6 мес, конкуренты, AI-выдача"),
    ("2", "Семантика: маркеры → ядро", "30–50 маркеров → 300–500, разговорный слой"),
    ("3", "Чистка семантики", "минус-слова, б/у, регионы, дубли; лист «исключено»"),
    ("4", "Интент и кластеры по SERP", "порог 5 URL, проверка ИИ"),
    ("5", "Посадочные под кластеры", "один интент — одна страница"),
    ("6", "Прогноз трафика и заявок", "промт 3.4, топ-3 / топ-10"),
    ("7", "Каналы SEO / PPC / GEO + backlog", "приоритет, владелец, срок"),
    ("8", "Технический аудит", "индексация, редиректы, скорость, разметка"),
    ("9", "Контент и страницы", "ТЗ → черновик → эксперт → фактчек"),
    ("10", "Доверие и поведение", "сниппеты, коммерческие блоки, слабые страницы"),
    ("11", "Внешние сигналы", "ссылки, упоминания, отзывы"),
    ("12", "Local SEO / филиалы", "NAP, карты, страницы филиалов"),
    ("13", "Ежемесячный цикл", "данные → гипотеза → внедрение → проверка"),
]
STATUS = {"done": ("Готово", "ok"), "progress": ("В работе", "warn"), "todo": ("Не начато", "mute"), "auto": ("Авто", "info")}

# метрика: (ключ, подпись, «меньше — лучше», суффикс)
KPIS = [("health", "Здоровье сайта", False, "/100"), ("errors", "Ошибки", True, ""), ("warnings", "Предупреждения", True, ""),
        ("broken", "Битые ссылки", True, ""), ("avg_ms", "Ответ сервера", True, " мс"), ("pages", "Страниц найдено", False, ""),
        ("uptime_pct", "Uptime", False, "%"), ("perf", "Скорость (Lighthouse)", False, "/100")]

CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#1d1d1b;--mute:#76746c;--line:#e6e3da;--accent:#2f6f4f;--ok:#1b7a3a;--warn:#a15c00;--bad:#b3261e;--info:#1a5fb4;--chip:#eeece5}
@media(prefers-color-scheme:dark){:root{--bg:#161614;--card:#201f1c;--ink:#ecebe6;--mute:#9a978d;--line:#34332e;--accent:#6fbf92;--ok:#6fd08c;--warn:#e0a24d;--bad:#ef7d74;--info:#7db2f0;--chip:#2b2a26}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:22px 16px 70px}h1{font-size:24px;margin:0}h2{font-size:18px;margin:34px 0 10px}
.sub{color:var(--mute);font-size:13px}.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.k{color:var(--mute);font-size:12.5px}.v{font-size:28px;font-weight:700;line-height:1.2}.d{font-size:12.5px}
.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}.info{color:var(--info)}.mute{color:var(--mute)}
svg.sp{display:block;margin-top:6px;width:100%;height:34px}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:var(--mute);font-weight:600;font-size:12px}
.tw{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow-x:auto;padding:4px 8px}
.chip{display:inline-block;padding:1px 9px;border-radius:99px;background:var(--chip);font-size:12px;font-weight:600}
.stage{display:grid;grid-template-columns:34px 1fr auto;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--line)}
.stage:last-child{border:0}.n{font-weight:700;color:var(--mute)}a{color:var(--info);text-decoration:none;word-break:break-all}
.bar{height:8px;background:var(--chip);border-radius:5px;overflow:hidden;margin-top:8px}.bar i{display:block;height:100%;background:var(--accent)}
details{border-top:1px solid var(--line);padding:8px 0}summary{cursor:pointer;font-weight:600}
@media(max-width:560px){.v{font-size:24px}.stage{grid-template-columns:28px 1fr}.stage .chip{grid-column:2}}
"""

CODE_RU = {
    "no_title": "Нет title", "no_h1": "Нет H1", "multi_h1": "Несколько H1", "dup_title": "Дубли title",
    "no_description": "Нет description", "dup_description": "Дубли description", "noindex": "Закрыто noindex",
    "status_4xx": "Страницы с 4xx", "status_5xx": "Страницы с 5xx", "broken_link": "Битые ссылки", "slow_response": "Медленный ответ",
    "no_og": "Нет Open Graph", "img_alt": "Картинки без alt", "no_canonical": "Нет canonical", "no_schema": "Нет schema.org",
    "thin": "Мало текста", "orphan": "Страницы-сироты", "redirect_chain": "Цепочки редиректов", "no_viewport": "Нет viewport",
    "title_long": "Длинный title", "desc_long": "Длинный description", "not_in_sitemap": "Нет в sitemap",
}
HOWTO = {  # что делать по карте проекта
    "no_h1": "Добавить один H1 с главным запросом страницы (этап 9)", "dup_title": "Переписать title под интент каждой страницы (этап 10, промт сниппета)",
    "no_description": "Написать description 120–160 симв. с УТП (этап 10)", "broken_link": "Исправить/удалить ссылки (этап 8)",
    "status_4xx": "Восстановить страницу или поставить 301 (этап 8)", "slow_response": "Сжать картинки, убрать лишние скрипты Tilda (этап 8)",
    "noindex": "Проверить: закрыто намеренно или по ошибке (этап 10)", "no_og": "Заполнить соц-превью в настройках страницы",
    "img_alt": "Добавить alt к ключевым картинкам", "orphan": "Дать внутренние ссылки со связанных страниц (этап 9)",
}


def spark(vals, bad_up=True):
    pts = [v for v in vals if v is not None]
    if len(pts) < 2:
        return "<svg class=sp></svg>"
    lo, hi = min(pts), max(pts)
    rng = (hi - lo) or 1
    n = len(vals)
    xy = [(i * 100 / (n - 1), 30 - (v - lo) * 26 / rng) for i, v in enumerate(vals) if v is not None]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    return (f"<svg class=sp viewBox='0 0 100 34' preserveAspectRatio='none'><polyline points='{d}' fill='none' "
            f"stroke='var(--accent)' stroke-width='1.8' vector-effect='non-scaling-stroke'/></svg>")


def delta(cur, prev, lower_better, suf):
    if cur is None or prev is None or cur == prev:
        return "<span class=mute>без изменений</span>" if cur is not None and prev is not None else "<span class=mute>—</span>"
    diff = cur - prev
    good = (diff < 0) == lower_better
    return f"<span class={'ok' if good else 'bad'}>{'▲' if diff > 0 else '▼'} {abs(diff):g}{suf} к прошлой неделе</span>"


def build(cfg, history, audit, speed=None):
    cur = history[-1]
    prev = history[-2] if len(history) > 1 else None
    stages = cfg.get("stages", {})
    # авто-статус этапа 8 из аудита
    st = {k: dict(stages.get(k, {})) for k, _, _ in STAGES}
    for k in st:
        st[k].setdefault("status", "todo")
    st["8"].setdefault("note", f"автоматически: здоровье {cur['health']}/100, ошибок {cur['errors']}")
    done = sum(1 for s in st.values() if s["status"] == "done")
    prog = sum(1 for s in st.values() if s["status"] == "progress")
    pct = round((done + prog * 0.5) * 100 / len(STAGES))

    h = [f"<!doctype html><html lang=ru><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
         f"<title>SEO-дашборд — {E(cfg['name'])}</title><style>{CSS}</style><main>",
         f"<h1>{E(cfg['name'])}</h1><div class=sub><a href='{E(cfg['url'])}'>{E(cfg['url'])}</a> · {E(cfg.get('cms', ''))} · "
         f"обновлено {E(cur['date'])} · снимков в истории: {len(history)}</div>"]

    h.append("<h2>Ключевые метрики</h2><div class=grid>")
    for key, label, lower, suf in KPIS:
        v = cur.get(key)
        h.append(f"<div class=card><div class=k>{label}</div><div class=v>{'—' if v is None else f'{v:g}'}<span class=sub style='font-size:14px'>{suf if v is not None else ''}</span></div>"
                 f"<div class=d>{delta(v, prev.get(key) if prev else None, lower, suf)}</div>{spark([x.get(key) for x in history])}</div>")
    if cur.get("visitors") is not None:
        h.append(f"<div class=card><div class=k>Посетители (счётчик)</div><div class=v>{cur['visitors']}</div><div class=d>{cur['pageviews']} просмотров</div></div>")
    h.append("</div>")

    h.append(f"<h2>Карта проекта: {pct}% пройдено</h2><div class=card><div class=bar><i style='width:{pct}%'></i></div>")
    for k, title, hint in STAGES:
        lab, cls = STATUS[st[k]["status"]]
        note = st[k].get("note") or hint
        h.append(f"<div class=stage><span class=n>{k}</span><div><b>{E(title)}</b><div class=sub>{E(note)}</div></div><span class='chip {cls}'>{lab}</span></div>")
    h.append("</div><div class=sub style='margin-top:6px'>Статусы этапов меняются в файле проекта; технические метрики обновляются сами каждый понедельник.</div>")

    by = {}
    for i in audit["issues"]:
        by.setdefault((i["severity"], i["code"]), []).append(i)
    order = {"error": 0, "warning": 1, "notice": 2}
    rows = []
    for (sev, code), items in sorted(by.items(), key=lambda kv: (order[kv[0][0]], -len(kv[1]))):
        if code in ("sitemap_not_crawled",):
            continue
        cls = {"error": "bad", "warning": "warn", "notice": "mute"}[sev]
        urls = "".join(f"<div><a href='{E(i['url'])}'>{E(i['url'])}</a></div>" for i in items[:8] if i.get("url"))
        more = f"<div class=sub>…и ещё {len(items) - 8}</div>" if len(items) > 8 else ""
        rows.append(f"<tr><td class={cls}><b>{E(CODE_RU.get(code, code))}</b></td><td>{len(items)}</td>"
                    f"<td>{E(HOWTO.get(code, ''))}<details><summary class=sub>Где</summary>{urls}{more}</details></td></tr>")
    h.append("<h2>Что чинить (из аудита)</h2><div class=tw><table><tr><th>Проблема</th><th>Шт.</th><th>Что делать и где</th></tr>" + "".join(rows) + "</table></div>")

    if audit["broken"]:
        h.append("<h2>Битые ссылки</h2><div class=tw><table><tr><th>Код</th><th>Ссылка</th><th>Найдена на</th></tr>" + "".join(
            f"<tr><td>{b['status'] or 'ERR'}</td><td>{E(b['url'][:90])}</td><td><a href='{E(b['found_on'][0][0])}'>{E(b['found_on'][0][0])}</a></td></tr>"
            for b in audit["broken"]) + "</table></div>")
    if speed:
        h.append("<h2>Скорость (Lighthouse, мобильная)</h2><div class=tw><table><tr><th>Страница</th><th>Скорость</th><th>SEO</th><th>LCP</th><th>CLS</th></tr>" + "".join(
            f"<tr><td>{E(s['url'])}</td><td>{s['scores']['performance']}</td><td>{s['scores']['seo']}</td><td>{E(s['lcp'])}</td><td>{E(s['cls'])}</td></tr>"
            for s in speed if not s.get("error")) + "</table></div>")
    pages = sorted(audit["pages"].values(), key=lambda p: -p["ms"])[:12]
    h.append("<h2>Самые медленные страницы</h2><div class=tw><table><tr><th>URL</th><th>Код</th><th>Ответ, мс</th><th>Слов</th></tr>" + "".join(
        f"<tr><td><a href='{E(p['url'])}'>{E(p['url'])}</a></td><td>{p['status']}</td><td>{p['ms']}</td><td>{p['words']}</td></tr>" for p in pages) + "</table></div>")
    h.append("</main></html>")
    return "".join(h)
