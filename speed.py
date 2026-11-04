"""Скорость страниц: локальный Lighthouse (npm-пакет, ставится через npx, без ключей и облаков)."""
import json
import os
import shutil
import subprocess
import tempfile

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def lighthouse(url, strategy="mobile", timeout=240):
    chrome = next((p for p in CHROME_PATHS if os.path.exists(p)), None)
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not chrome or not npx:
        return dict(url=url, error="Нужны Node.js (npx) и Google Chrome")
    out = os.path.join(tempfile.mkdtemp(), "lh.json")
    cmd = [npx, "--yes", "lighthouse@12", url, "--output=json", f"--output-path={out}", "--quiet",
           "--only-categories=performance,seo,accessibility,best-practices",
           f"--chrome-flags=--headless=new --no-sandbox", "--max-wait-for-load=45000"]
    if strategy == "desktop":
        cmd += ["--preset=desktop"]
    env = dict(os.environ, CHROME_PATH=chrome)
    try:
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":  # убиваем всё дерево процессов (npx -> node -> chrome)
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
            else:
                proc.kill()
            return dict(url=url, error="Lighthouse завис (timeout)")
        d = json.load(open(out, encoding="utf-8"))
    except Exception as e:
        return dict(url=url, error=f"Lighthouse не отработал: {str(e)[:150]}")
    a, c = d["audits"], d["categories"]

    def v(k):
        return a.get(k, {}).get("displayValue", "—")

    return dict(url=url, strategy=strategy, error=None,
                scores={k: round((c[k]["score"] or 0) * 100) for k in c},
                lcp=v("largest-contentful-paint"), cls=v("cumulative-layout-shift"), tbt=v("total-blocking-time"),
                fcp=v("first-contentful-paint"), speed_index=v("speed-index"), page_weight=v("total-byte-weight"),
                opportunities=[dict(title=x["title"], saving=x.get("displayValue", ""))
                               for x in a.values() if x.get("details", {}).get("type") == "opportunity"
                               and x.get("score") is not None and x["score"] < 0.9][:6])
