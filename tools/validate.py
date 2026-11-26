"""Check the recipe data.

Serves the repo on a local port, opens tools/validate.html in headless
Chrome or Edge (so the check uses the app's own js/derive.js), and prints
the report. Exits with 1 if there are problems.

    python tools/validate.py
"""

import functools
import html
import http.server
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BROWSERS = [
    shutil.which("chrome"), shutil.which("msedge"), shutil.which("google-chrome"), shutil.which("chromium"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_browser():
    for b in BROWSERS:
        if b and os.path.exists(b):
            return b
    sys.exit("Couldn't find Chrome or Edge. Instead, serve the repo and open /tools/validate.html.")


def main():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/tools/validate.html"
    try:
        dom = subprocess.run(
            [find_browser(), "--headless=new", "--disable-gpu", "--virtual-time-budget=10000",
             "--dump-dom", url],
            capture_output=True, text=True, encoding="utf-8", timeout=90,
        ).stdout
    finally:
        server.shutdown()
    match = re.search(r'<pre id="out">(.*?)</pre>', dom, re.S)
    report = html.unescape(match.group(1)) if match else "Couldn't read the report.\nPROBLEMS: 1"
    print(report)
    ok = re.search(r"PROBLEMS: 0\b", report)

    # Coeliac / nut safety of the recipe WORDS (tools/safety_scan.py).
    sys.path.insert(0, str(ROOT / "tools"))
    import safety_scan
    problems = safety_scan.scan()
    print("\nSafety scan of recipe text (gluten words in gluten-free recipes, nut words in nut-free ones):")
    for rid, where, word, ctx in problems[:50]:
        print(f"  {rid} | {where} | {word} | {ctx}")
    if len(problems) > 50:
        print(f"  … and {len(problems) - 50} more (run python tools/safety_scan.py)")
    print(f"SAFETY PROBLEMS: {len(problems)}")
    sys.exit(0 if ok and not problems else 1)


if __name__ == "__main__":
    main()
