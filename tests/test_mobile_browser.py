"""Real Chromium mobile-browser smoke tests for the installable web app.

Run with: python -m playwright install chromium && pytest tests/test_mobile_browser.py
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def launch_chromium(playwright):
    try:
        return playwright.chromium.launch()
    except Exception as exc:
        if "Executable doesn't exist" in str(exc):
            pytest.skip("Chromium is not installed; the dedicated mobile workflow installs it.")
        raise


@pytest.fixture(scope="module")
def app_url(tmp_path_factory):
    temp = tmp_path_factory.mktemp("micro-helper-browser")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["MICRO_HELPER_DB"] = str(temp / "browser.sqlite3")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "micro_helper.api:app",
         "--app-dir", str(ROOT / "src"), "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            if process.poll() is not None:
                raise RuntimeError("Micro Helper server exited before becoming ready")
            try:
                import urllib.request
                urllib.request.urlopen(url + "/health", timeout=0.5).read()
                break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError("Micro Helper server did not become ready")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_mobile_layout_and_core_controls(app_url):
    with sync_playwright() as p:
        browser = launch_chromium(p)
        page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(app_url, wait_until="networkidle")
        assert response and response.status == 200
        assert page.locator("h1").inner_text() == "Mykla · Micro Helper"
        assert page.locator("#chat").is_visible()
        assert page.locator("#memoryForm").is_visible()
        assert page.locator("#exportBackup").is_visible()
        assert page.locator("body").evaluate("(el) => el.scrollWidth") <= 390
        page.wait_for_function(
            "() => navigator.serviceWorker && navigator.serviceWorker.getRegistration('/').then(Boolean)"
        )
        manifest = page.request.get(app_url + "/static/manifest.webmanifest")
        worker = page.request.get(app_url + "/service-worker.js")
        assert manifest.status == 200
        assert worker.status == 200
        assert "service-worker-allowed" in worker.headers
        assert not errors
        browser.close()


def test_chat_interaction_with_mocked_local_model(app_url):
    with sync_playwright() as p:
        browser = launch_chromium(p)
        page = browser.new_page(viewport={"width": 412, "height": 915}, device_scale_factor=1, is_mobile=True, has_touch=True)
        page.route("**/v1/chat", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body='{"reply":"Testovací odpověď Mykly"}',
        ))
        page.goto(app_url, wait_until="networkidle")
        page.locator("#prompt").fill("Otestuj chat")
        page.locator("#chat button.primary").click()
        page.get_by_text("Testovací odpověď Mykly").wait_for(state="visible", timeout=5000)
        assert page.get_by_text("Testovací odpověď Mykly").is_visible()
        browser.close()
