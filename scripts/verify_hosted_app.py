#!/usr/bin/env python3
"""Static consistency checks for the mirrored hosted Micro Helper source."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "hosted-app"

def read(path: str) -> str:
    file = ROOT / path
    if not file.is_file():
        raise SystemExit(f"Missing hosted source file: {path}")
    return file.read_text(encoding="utf-8")

def main() -> None:
    package = json.loads(read("package.json"))
    manifest = json.loads(read("public/manifest.webmanifest"))
    tests = json.loads(read("tests/tests.json"))
    cron = json.loads(read("cron.json"))
    backend = read("backend/index.ts")
    html = read("index.html")
    read("src/main.ts")
    read("src/styles.css")
    read("public/sw.js")
    read("public/icon.svg")

    assert package["name"], "package.json must have a package name"
    assert manifest["lang"] == "cs-CZ", "PWA must declare Czech locale"
    assert manifest["start_url"] == "/" and manifest["scope"] == "/"
    assert '<link rel="manifest" href="/manifest.webmanifest"' in html
    assert "https://html.duckduckgo.com/html/?q=" in backend, "Search must use a fixed upstream URL"
    assert "new URL(data.url" not in backend, "Backend must not fetch arbitrary client-provided URLs"

    routes = re.findall(r'"(?:GET|POST|PUT|PATCH|DELETE) /api/[^"]+"\s*:\s*\[([^\]]{0,240})', backend)
    if not routes:
        raise SystemExit("No API routes found in hosted backend")
    unprotected = [route for route in routes if "requireAuth()" not in route]
    if unprotected:
        raise SystemExit(f"Found API route without requireAuth(): {len(unprotected)}")

    sanity = [item for item in tests if item.get("sanity") is True]
    if len(sanity) != 1:
        raise SystemExit("Exactly one hosted QA scenario must be marked sanity=true")
    for item in tests:
        if not item.get("name") or not item.get("description") or not item.get("covers") or not item.get("steps") or not item.get("expected"):
            raise SystemExit("Each QA scenario needs name, description, covers, steps and expected")

    if not any(item.get("handler") == "dailyReviewHandler" for item in cron):
        raise SystemExit("Daily review cron handler is missing")

    scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.DOTALL)
    if not scripts:
        raise SystemExit("No inline browser scripts found")
    with tempfile.TemporaryDirectory(prefix="micro-helper-") as tmp:
        for index, script in enumerate(scripts):
            path = Path(tmp) / f"inline-{index}.js"
            path.write_text(script, encoding="utf-8")
            subprocess.run(["node", "--check", str(path)], check=True)

    print(f"Hosted source checks passed: {len(tests)} QA scenarios, {len(routes)} authenticated API routes, {len(scripts)} inline scripts.")

if __name__ == "__main__":
    main()
