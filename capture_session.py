"""
Captura sessão autenticada do Superset (incluindo SSO Azure) via Playwright.

Uso:
    uv run python capture_session.py
    # ou: python capture_session.py

Abre um Chromium visível. Faça login normalmente (incluindo Azure/MFA).
Quando a página principal do Superset carregar, o script salva os cookies em
.superset_session.json e fecha o navegador.

Pré-requisito (uma vez):
    pip install playwright
    playwright install chromium
"""

import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

load_dotenv()

BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://localhost:8088").rstrip("/")
STATE_PATH = os.path.join(os.path.dirname(__file__), ".superset_session.json")
LOGIN_TIMEOUT_MS = 5 * 60 * 1000  # 5 min para concluir SSO/MFA


def main() -> int:
    login_url = f"{BASE_URL}/login/"
    host = urlparse(BASE_URL).netloc

    print(f"Abrindo {login_url} — faça login (Azure/SSO inclusive).")
    print("Aguardando você chegar em /superset/welcome/ ...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(login_url)

        try:
            page.wait_for_url("**/superset/welcome/**", timeout=LOGIN_TIMEOUT_MS)
        except PWTimeout:
            print("Timeout aguardando redirecionamento pós-login.", file=sys.stderr)
            browser.close()
            return 1

        # Garante que o cookie 'session' está presente para o host alvo
        cookies = context.cookies()
        has_session = any(
            c.get("name") == "session" and host in (c.get("domain") or "")
            for c in cookies
        )
        if not has_session:
            print("Aviso: cookie 'session' não encontrado. A sessão pode não funcionar.",
                  file=sys.stderr)

        context.storage_state(path=STATE_PATH)
        browser.close()

    os.chmod(STATE_PATH, 0o600)
    print(f"Sessão salva em {STATE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
