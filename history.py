"""Недельные снимки метрик: data/history/<сайт>/<дата>.json"""
import glob
import json
import os
import time
from collections import Counter


def snapshot(slug, data_dir, pages, issues, health, broken, speed, uptime, traffic, date=None):
    ok = [p for p in pages.values() if p["status"] == 200 and not p.get("non_html")]
    by = Counter(i["code"] for i in issues)
    sev = Counter(i["severity"] for i in issues)
    perf = [s["scores"]["performance"] for s in (speed or []) if not s.get("error")]
    snap = dict(
        date=date or time.strftime("%Y-%m-%d"),
        health=health, pages=len(pages), indexable=len(ok),
        errors=sev["error"], warnings=sev["warning"], notices=sev["notice"],
        broken=len(broken), avg_ms=round(sum(p["ms"] for p in ok) / len(ok)) if ok else None,
        slow=by["slow_response"], no_h1=by["no_h1"], no_description=by["no_description"],
        dup_title=by["dup_title"], noindex=by["noindex"], no_og=by["no_og"], img_alt=by["img_alt"],
        uptime_pct=uptime["uptime_pct"] if uptime else None,
        perf=round(sum(perf) / len(perf)) if perf else None,
        visitors=traffic["visitors"] if traffic else None, pageviews=traffic["pageviews"] if traffic else None,
        by_code=dict(by),
    )
    d = os.path.join(data_dir, "history", slug)
    os.makedirs(d, exist_ok=True)
    json.dump(snap, open(os.path.join(d, snap["date"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
    return snap


def load(slug, data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "history", slug, "*.json")))
    return [json.load(open(f, encoding="utf-8")) for f in files]
