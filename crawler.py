"""Краулер: обходит сайт по внутренним ссылкам и собирает SEO-данные страниц."""
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag, urlparse

UA = "Mozilla/5.0 (compatible; SeoLocal/1.0)"


def fetch(url, timeout=20, method="GET", max_bytes=3_000_000):
    """Возвращает dict: status, final_url, headers, body(str), ms, redirects, error."""
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept-Language": "ru,en;q=0.8"})
    hops = []

    class Track(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, r, fp, code, msg, headers, newurl):
            hops.append((code, newurl))
            return super().redirect_request(r, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(Track)
    t0 = time.time()
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read(max_bytes) if method == "GET" else b""
            ct = r.headers.get("Content-Type", "")
            m = re.search(r"charset=([\w-]+)", ct)
            enc = m.group(1) if m else "utf-8"
            try:
                body = raw.decode(enc, errors="replace")
            except LookupError:
                body = raw.decode("utf-8", errors="replace")
            return dict(status=r.status, final_url=r.geturl(), headers={k.title(): v for k, v in r.headers.items()}, body=body,
                        size=len(raw), ms=int((time.time() - t0) * 1000), redirects=hops, error=None)
    except urllib.error.HTTPError as e:
        return dict(status=e.code, final_url=url, headers={k.title(): v for k, v in (e.headers or {}).items()}, body="", size=0,
                    ms=int((time.time() - t0) * 1000), redirects=hops, error=None)
    except Exception as e:  # DNS, timeout, SSL
        return dict(status=0, final_url=url, headers={}, body="", size=0,
                    ms=int((time.time() - t0) * 1000), redirects=hops, error=str(e)[:200])


class PageParser(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.title = ""
        self.meta = {}
        self.canonical = None
        self.h = {"h1": [], "h2": [], "h3": []}
        self.links = []          # (href, rel, anchor)
        self.imgs = []           # (src, alt)
        self.ld = []             # JSON-LD сырой текст
        self.lang = None
        self.hreflang = []
        self.text = []
        self._cur = None
        self._buf = []
        self._skip = 0
        self._a = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag in ("title", "h1", "h2", "h3"):
            self._cur, self._buf = tag, []
        elif tag == "meta":
            k = (a.get("name") or a.get("property") or "").lower()
            if k:
                self.meta[k] = a.get("content", "")
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if rel == "canonical":
                self.canonical = urljoin(self.base, a.get("href", ""))
            elif rel == "alternate" and a.get("hreflang"):
                self.hreflang.append(a["hreflang"])
        elif tag == "a" and a.get("href"):
            self._a = [a["href"], (a.get("rel") or "").lower(), []]
        elif tag == "img":
            self.imgs.append((a.get("src") or a.get("data-original") or "", a.get("alt")))
        elif tag == "script":
            self._skip += 1
            if (a.get("type") or "").lower() == "application/ld+json":
                self._cur, self._buf = "ld", []
        elif tag == "style":
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        if tag == "a" and self._a:
            href, rel, parts = self._a
            self.links.append((href, rel, " ".join("".join(parts).split())))
            self._a = None
        if self._cur == tag or (self._cur == "ld" and tag == "script"):
            txt = " ".join("".join(self._buf).split())
            if tag == "title":
                self.title = txt
            elif tag in self.h:
                if txt:
                    self.h[tag].append(txt)
            elif self._cur == "ld":
                self.ld.append("".join(self._buf))
            self._cur = None

    def handle_data(self, data):
        if self._cur:
            self._buf.append(data)
        if self._a is not None:
            self._a[2].append(data)
        if not self._skip:
            self.text.append(data)


def norm(url):
    url, _ = urldefrag(url)
    p = urlparse(url)
    path = p.path or "/"
    return p._replace(path=path, fragment="").geturl()


def parse_page(url, res):
    p = PageParser(res["final_url"])
    try:
        p.feed(res["body"])
    except Exception:
        pass
    text = " ".join(" ".join(p.text).split())
    ld_types = []
    for raw in p.ld:
        ld_types += re.findall(r'"@type"\s*:\s*"([^"]+)"', raw)
    host = urlparse(url).netloc
    internal, external = [], []
    for href, rel, anchor in p.links:
        if href.startswith(("mailto:", "tel:", "javascript:", "#", "viber:", "tg:", "whatsapp:")):
            continue
        full = norm(urljoin(res["final_url"], href))
        if urlparse(full).scheme not in ("http", "https"):
            continue
        item = dict(url=full, anchor=anchor, nofollow="nofollow" in rel)
        (internal if urlparse(full).netloc == host else external).append(item)
    return dict(
        url=url, final_url=res["final_url"], status=res["status"], ms=res["ms"], size=res["size"],
        redirects=res["redirects"], error=res["error"],
        content_type=res["headers"].get("Content-Type", ""),
        title=p.title, description=p.meta.get("description", ""), robots_meta=p.meta.get("robots", ""),
        canonical=p.canonical, lang=p.lang, hreflang=p.hreflang,
        h1=p.h["h1"], h2=p.h["h2"], h3=p.h["h3"],
        og={k: v for k, v in p.meta.items() if k.startswith("og:")},
        viewport=p.meta.get("viewport", ""), schema_types=ld_types,
        words=len(re.findall(r"\w+", text)), text_sample=text[:400],
        imgs_total=len(p.imgs), imgs_no_alt=sum(1 for s, a in p.imgs if s and (a is None or not a.strip())),
        internal_links=internal, external_links=external,
    )


def crawl(start_url, max_pages=300, workers=8, log=print, seeds=()):
    start = norm(start_url)
    host = urlparse(start).netloc
    seeds = [u for u in dict.fromkeys(seeds) if urlparse(u).netloc == host and u != start]
    seen, pages, queue = {start, *seeds}, {}, [start, *seeds]
    while queue and len(pages) < max_pages:
        batch, queue = queue[: workers * 2], queue[workers * 2:]
        with ThreadPoolExecutor(workers) as ex:
            results = list(ex.map(lambda u: (u, fetch(u)), batch))
        for u, res in results:
            ctype = res["headers"].get("Content-Type", "")
            if res["status"] and ctype and "html" not in ctype.lower() and res["status"] < 400:
                pages[u] = dict(url=u, final_url=res["final_url"], status=res["status"], ms=res["ms"], size=res["size"],
                                redirects=res["redirects"], error=None, content_type=ctype, non_html=True,
                                internal_links=[], external_links=[], h1=[], h2=[], h3=[], title="", description="",
                                robots_meta="", canonical=None, lang=None, hreflang=[], og={}, viewport="",
                                schema_types=[], words=0, text_sample="", imgs_total=0, imgs_no_alt=0)
                continue
            pg = parse_page(u, res)
            pages[u] = pg
            log(f"  [{pg['status'] or 'ERR'}] {u}")
            for l in pg["internal_links"]:
                t = l["url"]
                if t not in seen and not re.search(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|rar|docx?|xlsx?|mp4|css|js|ico)(\?|$)", t, re.I):
                    seen.add(t)
                    queue.append(t)
            # финальный URL после редиректа тоже внутренний
            fu = norm(res["final_url"])
            if urlparse(fu).netloc == host and fu not in seen:
                seen.add(fu)
                queue.append(fu)
    return pages


def site_files(start_url):
    """robots.txt и sitemap.xml."""
    p = urlparse(start_url)
    root = f"{p.scheme}://{p.netloc}"
    robots = fetch(root + "/robots.txt")
    sm_urls = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots["body"]) if robots["status"] == 200 else []
    sm_list = sm_urls or [root + "/sitemap.xml"]
    urls, sm_status = [], {}
    for sm in sm_list:
        r = fetch(sm)
        sm_status[sm] = r["status"]
        if r["status"] == 200:
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r["body"])
            for loc in locs:
                if loc.endswith(".xml"):  # индекс сайтмапов
                    rr = fetch(loc)
                    urls += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", rr["body"]) if rr["status"] == 200 else []
                else:
                    urls.append(loc)
    return dict(robots_status=robots["status"], robots_text=robots["body"][:3000] if robots["status"] == 200 else "",
                sitemaps=sm_status, sitemap_urls=[norm(u) for u in urls],
                https=p.scheme == "https")
