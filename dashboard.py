"""Дашборд проекта: один HTML-файл без внешних библиотек. Метрики из истории + этапы карты SEO-проекта."""
import html
import json

from stages_data import CTX, GOOGLE_STEPS, STAGE_DATA

E = html.escape

JS = r"""
const $=s=>document.querySelector(s),K=(s,i)=>'sl:'+D.host+':'+s+':'+i;
const ls={get:k=>{try{return localStorage.getItem(k)}catch(e){return null}},set:(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}}};
const esc=t=>t.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function copy(text,btn,label){navigator.clipboard.writeText(text).then(()=>{btn.textContent='Скопировано ✓';setTimeout(()=>btn.textContent=label,1800)}).catch(()=>{prompt('Скопируйте текст:',text)})}
function done(s){return s.actions.map((a,i)=>ls.get(K(s.id,i))==='1')}
function refresh(){let tot=0,ok=0;D.stages.forEach(s=>{const d=done(s),n=d.filter(Boolean).length;tot+=d.length;ok+=n;
 const c=$('#chip'+s.id);const all=n===d.length;c.textContent=all?'Этап закрыт':n?('В работе '+n+'/'+d.length):'Не начато';c.className='chip '+(all?'ok':n?'warn':'mute');
 s.actions.forEach((a,i)=>$('#row'+s.id+'_'+i).classList.toggle('done',d[i]));$('#close'+s.id).hidden=!all});
 const p=Math.round(ok*100/tot);$('#pct').textContent=p;$('#pbar').style.width=p+'%'}
D.stages.forEach((s,idx)=>{const b=$('#body'+s.id);const nxt=D.stages[idx+1];
 b.innerHTML=s.actions.map((a,i)=>'<label class=todo-i id=row'+s.id+'_'+i+'><input type=checkbox data-s='+s.id+' data-i='+i+(ls.get(K(s.id,i))==='1'?' checked':'')+'><span>'+esc(a)+'</span></label>').join('')+
 '<div class=row><button class=btn data-p='+idx+'>Скопировать промт для Claude</button><button class="btn ghost" id=close'+s.id+' data-c='+idx+' hidden>Этап закрыт — передать Claude</button></div>';});
document.addEventListener('change',e=>{const t=e.target;if(t.dataset&&t.dataset.s){ls.set(K(t.dataset.s,t.dataset.i),t.checked?'1':'0');refresh()}});
document.addEventListener('click',e=>{const t=e.target;if(t.dataset&&t.dataset.p!==undefined){const s=D.stages[t.dataset.p],d=done(s);
  copy(s.prompt+'\n\nСписок действий этапа:\n'+s.actions.map((a,i)=>(d[i]?'[x] ':'[ ] ')+a).join('\n'),t,'Скопировать промт для Claude')}
 if(t.dataset&&t.dataset.c!==undefined){const i=+t.dataset.c,s=D.stages[i],n=D.stages[i+1];
  copy('Проект: '+D.name+', сайт '+D.url+'.\nЭтап '+s.id+' «'+s.title+'» закрыт. Выполнено:\n'+s.actions.map(a=>'- '+a).join('\n')+'\n\nПроверь, всё ли сделано по сути (задай мне уточняющие вопросы, если данных не хватает), и зафиксируй результат этапа. '+(n?'Затем веди меня на этап '+n.id+' «'+n.title+'»:\n'+n.actions.map(a=>'- '+a).join('\n'):'Это последний этап: составь план на следующий месяц.'),t,'Этап закрыт — передать Claude')}});
refresh();

"""

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
:root{--bg:#f6f5f1;--card:#fff;--ink:#1d1d1b;--mute:#76746c;--line:#e6e3da;--accent:#1f5fd6;--ok:#1b7a3a;--warn:#a15c00;--bad:#b3261e;--info:#1a5fb4;--chip:#eeece5}
@media(prefers-color-scheme:dark){:root{--bg:#161614;--card:#201f1c;--ink:#ecebe6;--mute:#9a978d;--line:#34332e;--accent:#6ea3ff;--ok:#6fd08c;--warn:#e0a24d;--bad:#ef7d74;--info:#7db2f0;--chip:#2b2a26}}
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
.btn{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:8px 14px;font:600 14px system-ui;cursor:pointer}
@media(prefers-color-scheme:dark){.btn{color:#0b1b3a}}
.btn.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent)}.btn:disabled{opacity:.5}
.st{border-bottom:1px solid var(--line);padding:6px 0}.st>summary{display:grid;grid-template-columns:34px 1fr auto;gap:10px;align-items:center;list-style:none}
.st>summary::-webkit-details-marker{display:none}.todo-i{display:flex;gap:9px;align-items:flex-start;padding:4px 0}.todo-i input{margin-top:4px;accent-color:var(--accent)}
.todo-i.done span{color:var(--mute);text-decoration:line-through}.row{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 4px}
.ghost-note{font-size:12.5px;color:var(--mute);margin-top:6px}ol.steps{margin:8px 0 0 18px;padding:0}ol.steps li{margin:3px 0}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:var(--mute);margin-top:6px}.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px}
.grid2{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}h3.sec{font-size:15px;margin:18px 0 8px}
.hb{display:grid;grid-template-columns:minmax(90px,38%) 1fr auto;gap:8px;align-items:center;margin:6px 0;font-size:13.5px}.hl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ht{background:var(--chip);border-radius:5px;height:10px;overflow:hidden}.ht i{display:block;height:100%;border-radius:5px}
.pre{white-space:pre-wrap;background:var(--chip);border-radius:8px;padding:10px;font:12.5px/1.45 ui-monospace,Consolas,monospace;margin-top:8px}
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


MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
PALETTE = ["#1f5fd6", "#e8590c", "#2b8a3e", "#9c36b5", "#0c8599"]


def ru_date(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]}"


def line_chart(series):
    """series: [(подпись, [[YYYY-MM-DD, значение], ...])] -> SVG с несколькими линиями."""
    series = [(n, s) for n, s in series if s]
    if not series:
        return ""
    days = sorted({d for _, s in series for d, _ in s})
    mx = max(max(v for _, v in s) for _, s in series) or 1
    W, H, L, B, T = 760, 260, 38, 26, 10
    x = lambda d: L + (W - L - 10) * (days.index(d) / max(1, len(days) - 1))
    y = lambda v: T + (H - T - B) * (1 - v / mx)
    out = [f"<svg viewBox='0 0 {W} {H}' style='width:100%;height:auto' role=img aria-label='График по дням'>"]
    for i in range(5):
        v = mx * i / 4
        out.append(f"<line x1={L} x2={W - 10} y1={y(v):.1f} y2={y(v):.1f} stroke='var(--line)'/><text x={L - 6} y={y(v) + 4:.1f} text-anchor=end font-size=11 fill='var(--mute)'>{round(v)}</text>")
    for i, d in enumerate(days):
        if i % max(1, len(days) // 8) == 0 or i == len(days) - 1:
            out.append(f"<text x={x(d):.1f} y={H - 8} text-anchor=middle font-size=11 fill='var(--mute)'>{int(d[8:])}.{d[5:7]}</text>")
    for k, (name, s) in enumerate(series):
        c = PALETTE[k % len(PALETTE)]
        pts = " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in sorted(s))
        out.append(f"<polyline points='{pts}' fill=none stroke='{c}' stroke-width=2.4 stroke-linejoin=round/>")
        for d, v in s:
            out.append(f"<circle cx={x(d):.1f} cy={y(v):.1f} r=3 fill='{c}'><title>{E(name)}: {ru_date(d)} — {v}</title></circle>")
    out.append("</svg><div class=legend>" + "".join(f"<span><i style='background:{PALETTE[k % len(PALETTE)]}'></i>{E(n)}</span>" for k, (n, _) in enumerate(series)) + "</div>")
    return "".join(out)


def hbars(rows, color="var(--accent)"):
    """rows: [[подпись, число], ...] -> горизонтальные столбцы."""
    rows = [r for r in rows if r[1] is not None]
    if not rows:
        return "<div class=sub>Пока нет данных</div>"
    mx = max(r[1] for r in rows) or 1
    return "".join(f"<div class=hb><span class=hl>{E(str(n))}</span><div class=ht><i style='width:{max(2, v * 100 / mx):.0f}%;background:{color}'></i></div><b>{v}</b></div>" for n, v in rows)


def metrics_section(metrics):
    if not metrics:
        return ""
    src = {s["source"]: s for s in metrics["sources"]}
    ok = lambda k: src.get(k, {}).get("status") == "ok"
    d1, d2 = metrics.get("period", ["", ""])
    mname = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"][int(d1[5:7]) - 1] if d1 else ""
    h = [f"<h2>Поисковый трафик за {mname}</h2><div class=sub>Только переходы из поисковых систем, с {ru_date(d1)} по {ru_date(d2)}. "
         f"Обновляется раз в неделю по понедельникам (данные на {ru_date(metrics['date'])}).</div>"]
    cards = []
    ym, ga, gsc, bing, yw = (src.get(k, {}) for k in ("yandex_metrika", "google_ga4", "google_gsc", "bing", "yandex_webmaster"))
    if ym.get("status") == "ok":
        cards.append(("Визиты из поиска (Метрика)", ym["visits"], f"{ym['users']} посетителей · отказы {ym['bounce']}%" + (f" · глубина {ym['depth']} стр." if ym.get("depth") else "")))
    if ga.get("status") == "ok":
        cards.append(("Сеансы из поиска (GA4)", ga["sessions"], f"{ga['users']} пользователей · {ga['pageviews']} просмотров"))
    if gsc.get("status") == "ok":
        cards.append(("Клики Google", gsc["clicks"], f"{gsc['impressions']} показов"))
    if bing.get("status") == "ok":
        cards.append(("Клики Bing", bing["clicks"], f"{bing['impressions']} показов"))
    if yw.get("status") == "ok":
        qp = yw.get("queries_period") or [None, None]
        per = f" · за {ru_date(qp[0])} — {ru_date(qp[1])} (Яндекс отдаёт с задержкой)" if qp[0] and qp[1] else ""
        cards.append(("Клики Яндекса (Вебмастер)", yw["clicks"], f"{yw['impressions']} показов" + (f" · ИКС {yw['sqi']}" if yw.get("sqi") is not None else "") + per))
    h.append("<div class=grid style='margin-top:10px'>" + "".join(f"<div class=card><div class=k>{E(a)}</div><div class=v>{b}</div><div class=d>{E(c)}</div></div>" for a, b, c in cards) + "</div>")
    notes = []
    for k, label in (("yandex_metrika", "Яндекс Метрика"), ("yandex_webmaster", "Яндекс Вебмастер"), ("bing", "Bing Webmaster"),
                     ("google_gsc", "Google Search Console"), ("google_ga4", "Google Analytics 4")):
        s = src.get(k, {})
        if s.get("status") == "not_connected":
            notes.append(f"{label}: не подключено")
        elif s.get("status") == "error":
            notes.append(f"{label}: {s.get('error', 'ошибка')}")
    if notes:
        h.append("<div class=ghost-note style='margin-top:8px'>" + " · ".join(E(n) for n in notes) + "</div>")
    series = [("Метрика: визиты из поиска", ym.get("daily")), ("GA4: сеансы из поиска", ga.get("daily")),
              ("Google: клики", gsc.get("daily")), ("Bing: клики", bing.get("daily"))]
    chart = line_chart([(n, s) for n, s in series if s])
    if chart:
        h.append("<h3 class=sec>Динамика по дням</h3><div class=card>" + chart + "</div>")
    two = []
    if ym.get("engines"):
        two.append("<div class=card><h3 class=sec style='margin:0 0 8px'>Поисковые системы (визиты)</h3>" + hbars(ym["engines"]) + "</div>")
    goals = ym.get("goals") or []
    ggoals = ga.get("goals") or []
    if goals:
        two.append("<div class=card><h3 class=sec style='margin:0 0 8px'>Цели из поиска (Метрика)</h3>" + hbars(goals, "#2b8a3e") + "</div>")
    if ggoals:
        two.append("<div class=card><h3 class=sec style='margin:0 0 8px'>Ключевые события из поиска (GA4)</h3>" + hbars(ggoals, "#2b8a3e") + "</div>")
    if two:
        h.append("<div class=grid2 style='margin-top:12px'>" + "".join(two) + "</div>")
    for k, label in (("google_gsc", "Google"), ("bing", "Bing"), ("yandex_webmaster", "Яндекс")):
        s = src.get(k, {})
        if s.get("status") == "ok" and s.get("top_queries"):
            rows = "".join(f"<tr><td>{E(str(q[0]))}</td><td>{q[1]}</td><td>{q[2]}</td><td>{q[3]}</td></tr>" for q in s["top_queries"])
            h.append(f"<details><summary>Запросы в {label}</summary><div class=tw><table><tr><th>Запрос</th><th>Клики</th><th>Показы</th><th>Позиция</th></tr>{rows}</table></div></details>")
    h.append(other_traffic(ym, d1, d2))
    return "".join(h)


def other_traffic(ym, d1, d2):
    """Не только поиск: все источники, прямые заходы, соцсети, сайты-источники, UTM-метки."""
    if ym.get("status") != "ok" or not ym.get("all_sources"):
        return ""
    h = [f"<h2>Все источники трафика</h2><div class=sub>Яндекс Метрика, визиты с {ru_date(d1)} по {ru_date(d2)}. "
         f"Модель «последний значимый источник» — как в отчётах Метрики.</div>"]
    rows = "".join(f"<tr><td>{E(r[0])}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}%</td></tr>" for r in ym["all_sources"])
    total = sum(r[1] for r in ym["all_sources"]) or 1
    bars = hbars([[r[0], r[1]] for r in ym["all_sources"]])
    h.append("<div class=grid2 style='margin-top:10px'><div class=card><h3 class=sec style='margin:0 0 8px'>Откуда приходят</h3>" + bars + "</div>"
             "<div class=card><div class=tw style='border:0;padding:0'><table><tr><th>Источник</th><th>Визитов</th><th>Глубина, стр.</th><th>Отказы</th></tr>"
             + rows + f"</table></div><div class=sub style='margin-top:6px'>Всего визитов: {total}</div></div></div>")
    d = ym.get("direct") or {}
    if any(d.get(k) for k in ("pages", "cities", "devices")):
        h.append("<h3 class=sec>Прямые заходы: куда, откуда и с чего</h3>"
                 "<div class=sub>Метрика не видит, из какого именно места пришёл прямой заход (человек ввёл адрес, открыл закладку или приложение). "
                 "Поэтому показываем, на какие страницы заходят, из каких городов и с каких устройств.</div><div class=grid2 style='margin-top:10px'>")
        for title, key in (("На какие страницы", "pages"), ("Из каких городов", "cities"), ("С каких устройств", "devices")):
            if d.get(key):
                h.append(f"<div class=card><h3 class=sec style='margin:0 0 8px'>{title}</h3>" + hbars(d[key]) + "</div>")
        h.append("</div>")
    two = []
    if ym.get("social"):
        two.append("<div class=card><h3 class=sec style='margin:0 0 8px'>Социальные сети</h3>" + hbars(ym["social"], "#9c36b5") + "</div>")
    if ym.get("referrals"):
        two.append("<div class=card><h3 class=sec style='margin:0 0 8px'>Сайты, с которых перешли по ссылке</h3>" + hbars(ym["referrals"], "#0c8599") + "</div>")
    if two:
        h.append("<h3 class=sec>Соцсети и сайты-источники</h3><div class=grid2>" + "".join(two) + "</div>")
    if ym.get("utm"):
        rows = "".join(f"<tr><td>{E(r[0])}</td><td>{E(r[1])}</td><td>{E(r[2])}</td><td>{r[3]}</td></tr>" for r in ym["utm"])
        h.append("<h3 class=sec>UTM-метки</h3><div class=tw><table><tr><th>Источник (utm_source)</th><th>Канал (utm_medium)</th>"
                 f"<th>Кампания (utm_campaign)</th><th>Визитов</th></tr>{rows}</table></div>")
    else:
        h.append("<h3 class=sec>UTM-метки</h3><div class=sub>За этот период визитов с UTM-метками нет.</div>")
    return "".join(h)


def build(cfg, history, audit, speed=None, metrics=None):
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

    ctx = CTX.format(name=cfg["name"], url=cfg["url"])
    data = dict(name=cfg["name"], url=cfg["url"], host=cfg["url"].split("//")[-1].strip("/"),
                clientId=cfg.get("google_client_id", ""), googleSteps=GOOGLE_STEPS,
                stages=[dict(id=k, title=t, actions=STAGE_DATA[k]["actions"],
                             prompt=STAGE_DATA[k]["prompt"].format(ctx=ctx, name=cfg["name"], url=cfg["url"]))
                        for k, t, _ in STAGES])
    h.append(metrics_section(metrics))
    h.append(f"<h2>Карта проекта: <span id=pct>{pct}</span>% пройдено</h2><div class=card><div class=bar><i id=pbar style='width:{pct}%'></i></div>")
    for k, title, hint in STAGES:
        auto = f" · {st[k]['note']}" if st[k].get("note") else ""
        h.append(f"<details class=st id=st{k}><summary><span class=n>{k}</span><div><b>{E(title)}</b><div class=sub>{E(hint)}{E(auto)}</div></div>"
                 f"<span class='chip mute' id=chip{k}>Не начато</span></summary><div id=body{k}></div></details>")
    h.append("</div><div class=ghost-note>Отметки сохраняются в этом браузере. Технические метрики выше обновляются автоматически.</div>")
    h.append("<script>const D=" + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";" + JS + "</script>")

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
