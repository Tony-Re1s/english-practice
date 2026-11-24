"""Visita os apps do Streamlit e acorda os que estiverem dormindo (roda no GitHub Actions)."""

import os
import sys

from playwright.sync_api import sync_playwright

URLS = [u.strip() for u in os.environ.get("APP_URLS", "").split(",") if u.strip()]
WAKE_TEXTS = ["Yes, get this app back up", "get this app back up"]


def visit(page, url: str) -> str:
    page.goto(url, wait_until="domcontentloaded", timeout=90_000)
    page.wait_for_timeout(8_000)
    for txt in WAKE_TEXTS:
        btn = page.get_by_role("button", name=txt)
        if btn.count():
            btn.first.click()
            page.wait_for_timeout(60_000)  # tempo para o app subir de novo
            return "estava dormindo → acordado"
    return "já estava acordado"


def main() -> int:
    if not URLS:
        print("Nenhuma URL em APP_URLS")
        return 1
    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for url in URLS:
            try:
                print(f"{url}: {visit(page, url)}")
            except Exception as e:
                failures += 1
                print(f"{url}: ERRO {e}")
        browser.close()
    return 1 if failures == len(URLS) else 0


if __name__ == "__main__":
    sys.exit(main())
