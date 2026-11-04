"""Сбор метрик из Bing Webmaster, Яндекс Вебмастера и Яндекс Метрики (на сервере, ключи из переменных окружения).
Секреты: BING_API_KEY, YANDEX_TOKEN. Нет секрета — источник пропускается."""
import json
import os
import re
import time
import urllib.parse
import urllib.request


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def _days(n):
    t = time.time()
    return time.strftime("%Y-%m-%d", time.gmtime(t - n * 86400)), time.strftime("%Y-%m-%d", time.gmtime(t))


def _msdate(s):
    m = re.search(r"/Date\((\d+)", s or "")
    return int(m.group(1)) // 1000 if m else 0


def bing(host):
    key = os.environ.get("BING_API_KEY")
    if not key:
        return dict(source="bing", status="not_connected")
    base = "https://ssl.bing.com/webmaster/api.svc/json/"
    try:
        sites = [s["Url"] for s in _get(f"{base}GetUserSites?apikey={key}").get("d", [])]
        site = next((s for s in sites if host in s), None)
        if not site:
            return dict(source="bing", status="error", error=f"сайт {host} не найден в Bing Webmaster (есть: {', '.join(sites) or 'ничего'})")
        q = urllib.parse.quote(site, safe="")
        tr = _get(f"{base}GetRankAndTrafficStats?apikey={key}&siteUrl={q}").get("d", [])
        since = time.time() - 28 * 86400
        recent = [r for r in tr if _msdate(r.get("Date")) >= since]
        qs = {}
        for r in _get(f"{base}GetQueryStats?apikey={key}&siteUrl={q}").get("d", []):
            if _msdate(r.get("Date")) >= since:
                e = qs.setdefault(r["Query"], [0, 0, 0.0, 0])
                e[0] += r.get("Clicks", 0)
                e[1] += r.get("Impressions", 0)
                e[2] += r.get("AvgImpressionPosition", 0)
                e[3] += 1
        top = sorted(([k, v[0], v[1], round(v[2] / v[3], 1)] for k, v in qs.items()), key=lambda x: -x[2])[:20]
        return dict(source="bing", status="ok", site=site, clicks=sum(r.get("Clicks", 0) for r in recent),
                    impressions=sum(r.get("Impressions", 0) for r in recent), top_queries=top)
    except Exception as e:
        return dict(source="bing", status="error", error=str(e)[:200])


def yandex_webmaster(host):
    tok = os.environ.get("YANDEX_TOKEN")
    if not tok:
        return dict(source="yandex_webmaster", status="not_connected")
    h = {"Authorization": "OAuth " + tok}
    base = "https://api.webmaster.yandex.net/v4/user"
    try:
        uid = _get(base, h)["user_id"]
        hosts = _get(f"{base}/{uid}/hosts", h).get("hosts", [])
        hid = next((x["host_id"] for x in hosts if host in x["host_id"]), None)
        if not hid:
            return dict(source="yandex_webmaster", status="error", error=f"сайт {host} не найден в Вебмастере")
        hq = urllib.parse.quote(hid, safe="")
        summ = _get(f"{base}/{uid}/hosts/{hq}/summary", h)
        d1, d2 = _days(28)
        qp = urllib.parse.urlencode([("order_by", "TOTAL_SHOWS"), ("query_indicator", "TOTAL_SHOWS"), ("query_indicator", "TOTAL_CLICKS"),
                                     ("query_indicator", "AVG_SHOW_POSITION"), ("date_from", d1), ("date_to", d2), ("limit", 50)])
        qs = _get(f"{base}/{uid}/hosts/{hq}/search-queries/popular?{qp}", h).get("queries", [])
        top = [[x["query_text"], round(x["indicators"].get("TOTAL_CLICKS", 0)), round(x["indicators"].get("TOTAL_SHOWS", 0)),
                round(x["indicators"].get("AVG_SHOW_POSITION", 0), 1)] for x in qs]
        return dict(source="yandex_webmaster", status="ok", site=hid, sqi=summ.get("sqi"),
                    pages_in_search=summ.get("searchable_pages_count"), excluded=summ.get("excluded_pages_count"),
                    problems=summ.get("site_problems", {}), clicks=sum(t[1] for t in top), impressions=sum(t[2] for t in top),
                    top_queries=top[:20])
    except Exception as e:
        return dict(source="yandex_webmaster", status="error", error=str(e)[:200])


def yandex_metrika(host):
    tok = os.environ.get("YANDEX_TOKEN")
    if not tok:
        return dict(source="yandex_metrika", status="not_connected")
    h = {"Authorization": "OAuth " + tok}
    try:
        cs = _get("https://api-metrika.yandex.net/management/v1/counters", h).get("counters", [])
        c = next((x for x in cs if host in (x.get("site") or "") or host in (x.get("site2") or {}).get("site", "")), None)
        if not c:
            return dict(source="yandex_metrika", status="error", error=f"счётчик для {host} не найден")
        p = urllib.parse.urlencode(dict(ids=c["id"], metrics="ym:s:visits,ym:s:users,ym:s:pageviews,ym:s:bounceRate",
                                        dimensions="ym:s:lastTrafficSource", date1="28daysAgo", date2="today", limit=10))
        d = _get(f"https://api-metrika.yandex.net/stat/v1/data?{p}", h)
        tot = d.get("totals", [0, 0, 0, 0])
        src = [[r["dimensions"][0]["name"], round(r["metrics"][0])] for r in d.get("data", [])]
        return dict(source="yandex_metrika", status="ok", counter=c["id"], visits=round(tot[0]), users=round(tot[1]),
                    pageviews=round(tot[2]), bounce=round(tot[3], 1), sources=src)
    except Exception as e:
        return dict(source="yandex_metrika", status="error", error=str(e)[:200])


def _google():
    raw = os.environ.get("GOOGLE_SA_JSON")
    if not raw:
        return None
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account
    scopes = ["https://www.googleapis.com/auth/webmasters.readonly", "https://www.googleapis.com/auth/analytics.readonly"]
    return AuthorizedSession(service_account.Credentials.from_service_account_info(json.loads(raw), scopes=scopes))


def google_gsc(host):
    try:
        s = _google()
        if s is None:
            return dict(source="google_gsc", status="not_connected")
        sites = [x["siteUrl"] for x in s.get("https://www.googleapis.com/webmasters/v3/sites").json().get("siteEntry", [])]
        site = next((x for x in sites if x in (f"sc-domain:{host}", f"https://{host}/", f"https://www.{host}/")), None)
        if not site:
            return dict(source="google_gsc", status="error",
                        error=f"у сервисного аккаунта нет доступа к {host} в Search Console (видит: {', '.join(sites) or 'ничего'})")
        d1, _ = _days(31)
        _, d2 = _days(3)
        url = "https://www.googleapis.com/webmasters/v3/sites/" + urllib.parse.quote(site, safe="") + "/searchAnalytics/query"

        def q(dims, n=25):
            return s.post(url, json=dict(startDate=d1, endDate=d2, dimensions=dims, rowLimit=n)).json().get("rows", [])
        tot = (q([], 1) or [{}])[0]
        top = [[r["keys"][0], r["clicks"], r["impressions"], round(r["position"], 1)] for r in q(["query"])]
        return dict(source="google_gsc", status="ok", site=site, clicks=round(tot.get("clicks", 0)),
                    impressions=round(tot.get("impressions", 0)), top_queries=top)
    except Exception as e:
        return dict(source="google_gsc", status="error", error=str(e)[:200])


def google_ga4(host):
    try:
        s = _google()
        if s is None:
            return dict(source="google_ga4", status="not_connected")
        prop = None
        for a in s.get("https://analyticsadmin.googleapis.com/v1beta/accountSummaries").json().get("accountSummaries", []):
            for p in a.get("propertySummaries", []):
                for st in s.get(f"https://analyticsadmin.googleapis.com/v1beta/{p['property']}/dataStreams").json().get("dataStreams", []):
                    if host in st.get("webStreamData", {}).get("defaultUri", ""):
                        prop = p["property"]
        if not prop:
            return dict(source="google_ga4", status="error", error=f"у сервисного аккаунта нет доступа к ресурсу GA4 для {host}")
        body = dict(dateRanges=[dict(startDate="28daysAgo", endDate="today")], metrics=[dict(name="sessions"), dict(name="activeUsers"), dict(name="screenPageViews")],
                    dimensions=[dict(name="sessionDefaultChannelGroup")])
        r = s.post(f"https://analyticsdata.googleapis.com/v1beta/{prop}:runReport", json=body).json()
        rows = r.get("rows", [])
        ch = [[x["dimensionValues"][0]["value"], int(x["metricValues"][0]["value"])] for x in rows]
        tot = [sum(int(x["metricValues"][i]["value"]) for x in rows) for i in range(3)]
        return dict(source="google_ga4", status="ok", property=prop, sessions=tot[0], users=tot[1], pageviews=tot[2], sources=ch)
    except Exception as e:
        return dict(source="google_ga4", status="error", error=str(e)[:200])


def collect(host, data_dir, slug):
    res = [bing(host), yandex_webmaster(host), yandex_metrika(host), google_gsc(host), google_ga4(host)]
    d = os.path.join(data_dir, "metrics", slug)
    os.makedirs(d, exist_ok=True)
    json.dump(dict(date=time.strftime("%Y-%m-%d"), sources=res), open(os.path.join(d, time.strftime("%Y-%m-%d") + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
    return res


def latest(data_dir, slug):
    d = os.path.join(data_dir, "metrics", slug)
    if not os.path.isdir(d):
        return None
    files = sorted(os.listdir(d))
    return json.load(open(os.path.join(d, files[-1]), encoding="utf-8")) if files else None
