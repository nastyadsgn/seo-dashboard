"""Шифрует дашборды проектов паролями из секретов и раскладывает в site/ для GitHub Pages.
arkadiyikura.ru лежит в корне (старый адрес), остальные — в site/<домен>/.
Проект без пароля в секрете не публикуется."""
import glob
import json
import os
import subprocess
import shutil
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT_HOST = "arkadiyikura.ru"
OPTS = ["--short", "--template-title", "SEO-дашборд", "--template-instructions", "Введите пароль для доступа к дашборду",
        "--template-placeholder", "Пароль", "--template-button", "Войти", "--template-error", "Неверный пароль",
        "--template-remember", "Запомнить на этом устройстве", "--template-color-primary", "#1f5fd6",
        "--template-color-secondary", "#e8f0ff"]


def main():
    out = os.path.join(ROOT, "site")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    published = []
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    for f in sorted(glob.glob(os.path.join(ROOT, "projects", "*.json"))):
        cfg = json.load(open(f, encoding="utf-8"))
        host = urlparse(cfg["url"]).netloc
        if not cfg.get("enabled", True):
            continue
        src = os.path.join(ROOT, "docs", host, "index.html")
        secret = cfg.get("password_secret") or ("DASH_PASSWORD" if host == ROOT_HOST else "DASH_PASSWORD_" + host.split(".")[0].upper().replace("-", "_"))
        pwd = os.environ.get(secret)
        if not os.path.exists(src):
            print(f"{host}: нет собранного дашборда, пропуск")
            continue
        if not pwd:
            print(f"{host}: не задан секрет {secret}, не публикую")
            continue
        dest = out if host == ROOT_HOST else os.path.join(out, host)
        os.makedirs(dest, exist_ok=True)
        subprocess.run([npx, "--yes", "staticrypt@3", src, "-p", pwd, "-d", dest] + OPTS, check=True)
        published.append(host)
    print("Опубликовано:", ", ".join(published) or "ничего")


if __name__ == "__main__":
    main()
