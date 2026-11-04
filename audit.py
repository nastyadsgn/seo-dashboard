"""Аудит: правила поверх данных краулера + проверка битых ссылок."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from crawler import fetch

# (severity, code, описание)
SEV = {"error": 0, "warning": 1, "notice": 2}


def check_links(pages, workers=12, log=print):
    """Проверяет все уникальные ссылки (внутренние и внешние). Возвращает список битых."""
    sources = defaultdict(list)
    for pg in pages.values():
        for l in pg["internal_links"] + pg["external_links"]:
            sources[l["url"]].append((pg["url"], l["anchor"]))
    known = {u: p["status"] for u, p in pages.items()}
    todo = [u for u in sources if u not in known]
    # соцсети отвечают ботам 418/999/ERR — это защита, а не битая ссылка
    skip = ("vk.com", "vk.ru", "instagram.com", "facebook.com", "t.me", "linkedin.com", "wa.me", "whatsapp.com")
    todo = [u for u in todo if not any(s in urlparse(u).netloc for s in skip)]

    def head(u):
        r = fetch(u, timeout=15, method="HEAD")
        if r["status"] in (0, 403, 405, 429, 501):  # часть серверов не любит HEAD
            r = fetch(u, timeout=15, method="GET", max_bytes=1000)
        return u, r["status"], r["error"]

    status = dict(known)
    with ThreadPoolExecutor(workers) as ex:
        for u, st, err in ex.map(head, todo):
            status[u] = st
            if st >= 400 or st == 0:
                log(f"  битая: [{st or 'ERR'}] {u}")
    broken = []
    for u, st in status.items():
        if u in sources and (st >= 400 or st == 0):
            broken.append(dict(url=u, status=st, found_on=sources[u][:5],
                               external=urlparse(u).netloc != urlparse(next(iter(pages))).netloc))
    return broken


def run_audit(pages, site, broken):
    issues = []

    def add(sev, code, msg, url=None):
        issues.append(dict(severity=sev, code=code, message=msg, url=url))

    if not site["https"]:
        add("error", "no_https", "Сайт открывается не по HTTPS")
    if site["robots_status"] != 200:
        add("warning", "no_robots", f"robots.txt недоступен (код {site['robots_status']})")
    if not any(v == 200 for v in site["sitemaps"].values()):
        add("warning", "no_sitemap", "sitemap.xml не найден")

    titles, descs = defaultdict(list), defaultdict(list)
    for u, p in pages.items():
        if p.get("non_html"):
            continue
        if p["error"]:
            add("error", "fetch_error", f"Не удалось загрузить: {p['error']}", u)
            continue
        st = p["status"]
        if st >= 500:
            add("error", "status_5xx", f"Ошибка сервера {st}", u)
        elif st >= 400:
            add("error", "status_4xx", f"Страница отдаёт {st}", u)
        if len(p["redirects"]) > 1:
            add("warning", "redirect_chain", f"Цепочка редиректов ({len(p['redirects'])} шагов)", u)
        elif p["redirects"]:
            add("notice", "redirect", f"Редирект {p['redirects'][0][0]} → {p['redirects'][0][1]}", u)
        if st >= 400:
            continue

        t, d = p["title"], p["description"]
        if not t:
            add("error", "no_title", "Нет <title>", u)
        else:
            titles[t].append(u)
            if len(t) > 70:
                add("warning", "title_long", f"Title длиннее 70 символов ({len(t)})", u)
            elif len(t) < 20:
                add("notice", "title_short", f"Title короче 20 символов ({len(t)})", u)
        if not d:
            add("warning", "no_description", "Нет meta description", u)
        else:
            descs[d].append(u)
            if len(d) > 170:
                add("notice", "desc_long", f"Description длиннее 170 символов ({len(d)})", u)
            elif len(d) < 50:
                add("notice", "desc_short", f"Description короче 50 символов ({len(d)})", u)
        if not p["h1"]:
            add("error", "no_h1", "Нет заголовка H1", u)
        elif len(p["h1"]) > 1:
            add("warning", "multi_h1", f"Несколько H1 ({len(p['h1'])})", u)
        if "noindex" in p["robots_meta"].lower():
            add("warning", "noindex", "Страница закрыта от индексации (noindex)", u)
        if not p["canonical"]:
            add("notice", "no_canonical", "Не указан canonical", u)
        elif p["canonical"].rstrip("/") != p["final_url"].split("#")[0].rstrip("/") and "noindex" not in p["robots_meta"].lower():
            add("notice", "canonical_other", f"Canonical ведёт на другой URL: {p['canonical']}", u)
        if not p["viewport"]:
            add("warning", "no_viewport", "Нет meta viewport (проблемы на мобильных)", u)
        if not p["lang"]:
            add("notice", "no_lang", "Не указан атрибут lang у <html>", u)
        if not p["og"].get("og:title") or not p["og"].get("og:image"):
            add("notice", "no_og", "Нет Open Graph (og:title / og:image) — плохой превью в соцсетях", u)
        if p["words"] < 150:
            add("notice", "thin", f"Мало текста ({p['words']} слов)", u)
        if p["imgs_no_alt"]:
            add("notice", "img_alt", f"Картинок без alt: {p['imgs_no_alt']} из {p['imgs_total']}", u)
        if p["ms"] > 2000:
            add("warning", "slow_response", f"Медленный ответ сервера: {p['ms']} мс", u)
        if p["size"] > 2_000_000:
            add("warning", "heavy_html", f"Тяжёлый HTML: {p['size'] // 1024} КБ", u)
        if not p["schema_types"]:
            add("notice", "no_schema", "Нет микроразметки schema.org (JSON-LD)", u)
        if not any(l for l in p["internal_links"]):
            add("warning", "no_links", "Нет внутренних ссылок со страницы", u)

    for t, urls in titles.items():
        if len(urls) > 1:
            for u in urls:
                add("warning", "dup_title", f"Дубль title у {len(urls)} страниц: «{t[:60]}»", u)
    for d, urls in descs.items():
        if len(urls) > 1:
            for u in urls:
                add("notice", "dup_description", f"Дубль description у {len(urls)} страниц", u)

    # Сирoты и расхождения со sitemap
    linked = {l["url"] for p in pages.values() for l in p["internal_links"]}
    for u in site["sitemap_urls"]:
        if u not in pages and u not in linked:
            add("notice", "sitemap_not_crawled", "URL из sitemap не найден краулером", u)
        elif u in pages and u not in linked and len(pages) > 1 and u != next(iter(pages)):
            add("warning", "orphan", "Страница из sitemap, но на неё нет внутренних ссылок", u)
    sm = set(site["sitemap_urls"])
    if sm:
        for u, p in pages.items():
            if p["status"] == 200 and not p.get("non_html") and u not in sm and "noindex" not in p["robots_meta"].lower():
                add("notice", "not_in_sitemap", "Страница есть на сайте, но не в sitemap", u)

    for b in broken:
        where = ", ".join(w for w, _ in b["found_on"][:3])
        add("error" if not b["external"] else "warning", "broken_link",
            f"Битая {'внешняя' if b['external'] else 'внутренняя'} ссылка [{b['status'] or 'ERR'}] {b['url']} — на: {where}")

    issues.sort(key=lambda i: (SEV[i["severity"]], i["code"]))
    ok_pages = [p for p in pages.values() if p["status"] and p["status"] < 400 and not p.get("non_html")]
    errs = sum(1 for i in issues if i["severity"] == "error")
    warns = sum(1 for i in issues if i["severity"] == "warning")
    n = max(1, len(ok_pages))
    health = max(0, round(100 - (errs * 6 + warns * 2) / n * 4))
    return issues, min(100, health)
