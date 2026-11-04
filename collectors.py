"""Сбор метрик ТОЛЬКО из поисковых систем за текущий месяц (с 1-го числа) + цели.
Секреты (переменные окружения): BING_API_KEY, YANDEX_TOKEN, GOOGLE_SA_JSON. Нет секрета — источник пропускается."""
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


def _period():
    """С 1-го числа текущего месяца по сегодня."""
    return time.strftime("%Y-%m-01"), time.strftime("%Y-%m-%d")


def _ago(n):
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() - n * 86400))


def _msdate(s):
    m = re.search(r"/Date\((\d+)", s or "")
    return int(m.group(1)) // 1000 if m else 0


def bing(host):
    key = os.environ.get("BING_API_KEY")
    if not key:
        return dict(source="bing", status="not_connected")
    base = "https://ssl.bing.com/webmaster/api.svc/json/"
    d1, _ = _period()
    since = time.mktime(time.strptime(d1, "%Y-%m-%d"))
    try:
        sites = [s["Url"] for s in _get(f"{base}GetUserSites?apikey={key}").get("d", [])]
        site = next((s for s in sites if host in s), None)
        if not site:
            return dict(source="bing", status="error", error=f"сайт {host} не найден в Bing Webmaster")
        q = urllib.parse.quote(site, safe="")
        tr = [r for r in _get(f"{base}GetRankAndTrafficStats?apikey={key}&siteUrl={q}").get("d", []) if _msdate(r.get("Date")) >= since]
        daily = sorted([[time.strftime("%Y-%m-%d", time.gmtime(_msdate(r["Date"]))), r.get("Clicks", 0)] for r in tr])
        qs = {}
        for r in _get(f"{base}GetQueryStats?apikey={key}&siteUrl={q}").get("d", []):
            if _msdate(r.get("Date")) >= since:
                e = qs.setdefault(r["Query"], [0, 0, 0.0, 0])
                e[0] += r.get("Clicks", 0)
                e[1] += r.get("Impressions", 0)
                e[2] += r.get("AvgImpressionPosition", 0)
                e[3] += 1
        top = sorted(([k, v[0], v[1], round(v[2] / v[3], 1)] for k, v in qs.items()), key=lambda x: -x[2])[:20]
        return dict(source="bing", status="ok", site=site, clicks=sum(r.get("Clicks", 0) for r in tr),
                    impressions=sum(r.get("Impressions", 0) for r in tr), daily=daily, top_queries=top)
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
        d1, d2 = _period()
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
    """Только переходы из поисковых систем + достижения целей."""
    tok = os.environ.get("YANDEX_TOKEN")
    if not tok:
        return dict(source="yandex_metrika", status="not_connected")
    h = {"Authorization": "OAuth " + tok}
    try:
        cs = _get("https://api-metrika.yandex.net/management/v1/counters", h).get("counters", [])
        c = next((x for x in cs if host in (x.get("site") or "") or host in (x.get("site2") or {}).get("site", "")), None)
        if not c:
            return dict(source="yandex_metrika", status="error", error=f"счётчик для {host} не найден")
        d1, d2 = _period()
        org = "ym:s:lastTrafficSource=='organic'"

        def stat(**kw):
            p = dict(ids=c["id"], date1=d1, date2=d2, filters=org, limit=100)
            p.update(kw)
            return _get("https://api-metrika.yandex.net/stat/v1/data?" + urllib.parse.urlencode(p), h)
        tot = stat(metrics="ym:s:visits,ym:s:users,ym:s:pageviews,ym:s:bounceRate").get("totals", [0, 0, 0, 0])
        daily = [[r["dimensions"][0]["name"], round(r["metrics"][0])] for r in
                 stat(metrics="ym:s:visits", dimensions="ym:s:date", sort="ym:s:date").get("data", [])]
        engines = [[r["dimensions"][0]["name"], round(r["metrics"][0])] for r in
                   stat(metrics="ym:s:visits", dimensions="ym:s:lastSearchEngineRoot", sort="-ym:s:visits", limit=10).get("data", [])]
        goals = []
        gl = _get(f"https://api-metrika.yandex.net/management/v1/counter/{c['id']}/goals", h).get("goals", [])[:15]
        if gl:
            names = {f"ym:s:goal{g['id']}reaches": g["name"] for g in gl}
            gt = stat(metrics=",".join(names)).get("totals", [])
            goals = sorted(([n, round(v)] for n, v in zip(names.values(), gt)), key=lambda x: -x[1])
        return dict(source="yandex_metrika", status="ok", counter=c["id"], visits=round(tot[0]), users=round(tot[1]),
                    pageviews=round(tot[2]), bounce=round(tot[3], 1), daily=daily, engines=engines, goals=goals)
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
                        error=f"у сервисного аккаунта нет доступа к {host} в Search Console")
        d1, _ = _period()
        d2 = max(d1, _ago(3))  # Google отдаёт данные с задержкой ~3 дня
        url = "https://www.googleapis.com/webmasters/v3/sites/" + urllib.parse.quote(site, safe="") + "/searchAnalytics/query"

        def q(dims, n=25):
            return s.post(url, json=dict(startDate=d1, endDate=d2, dimensions=dims, rowLimit=n)).json().get("rows", [])
        tot = (q([], 1) or [{}])[0]
        top = [[r["keys"][0], r["clicks"], r["impressions"], round(r["position"], 1)] for r in q(["query"])]
        daily = sorted([[r["keys"][0], r["clicks"]] for r in q(["date"], 40)])
        return dict(source="google_gsc", status="ok", site=site, clicks=round(tot.get("clicks", 0)),
                    impressions=round(tot.get("impressions", 0)), daily=daily, top_queries=top, last_date=d2)
    except Exception as e:
        return dict(source="google_gsc", status="error", error=str(e)[:200])


def google_ga4(host):
    """Только Organic Search + ключевые события (цели)."""
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
        d1, d2 = _period()
        flt = dict(filter=dict(fieldName="sessionDefaultChannelGroup", stringFilter=dict(value="Organic Search", matchType="EXACT")))

        def rep(dims, mets, **kw):
            body = dict(dateRanges=[dict(startDate=d1, endDate=d2)], dimensions=[dict(name=d) for d in dims],
                        metrics=[dict(name=m) for m in mets], dimensionFilter=flt, limit=100)
            body.update(kw)
            return s.post(f"https://analyticsdata.googleapis.com/v1beta/{prop}:runReport", json=body).json()
        t = rep([], ["sessions", "activeUsers", "screenPageViews"]).get("rows", [{"metricValues": [{"value": 0}] * 3}])[0]["metricValues"]
        daily = sorted([[x["dimensionValues"][0]["value"][:4] + "-" + x["dimensionValues"][0]["value"][4:6] + "-" + x["dimensionValues"][0]["value"][6:],
                         int(x["metricValues"][0]["value"])] for x in rep(["date"], ["sessions"]).get("rows", [])])
        goals = sorted([[x["dimensionValues"][0]["value"], int(float(x["metricValues"][0]["value"]))]
                        for x in rep(["eventName"], ["keyEvents"]).get("rows", []) if float(x["metricValues"][0]["value"]) > 0], key=lambda g: -g[1])
        return dict(source="google_ga4", status="ok", property=prop, sessions=int(t[0]["value"]), users=int(t[1]["value"]),
                    pageviews=int(t[2]["value"]), daily=daily, goals=goals)
    except Exception as e:
        return dict(source="google_ga4", status="error", error=str(e)[:200])


def collect(host, data_dir, slug):
    res = [bing(host), yandex_webmaster(host), yandex_metrika(host), google_gsc(host), google_ga4(host)]
    d = os.path.join(data_dir, "metrics", slug)
    os.makedirs(d, exist_ok=True)
    period = _period()
    json.dump(dict(date=time.strftime("%Y-%m-%d"), period=period, sources=res),
              open(os.path.join(d, time.strftime("%Y-%m-%d") + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
    return res


def latest(data_dir, slug):
    d = os.path.join(data_dir, "metrics", slug)
    if not os.path.isdir(d):
        return None
    files = sorted(os.listdir(d))
    return json.load(open(os.path.join(d, files[-1]), encoding="utf-8")) if files else None
