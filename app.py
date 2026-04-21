"""Desktop application entry point for LJ Discounts.

The scraper still writes the same static HTML report. This module wraps that
report in a native desktop window so Windows users can run it like an app
instead of launching a terminal and browser.
"""
from __future__ import annotations

import contextlib
import io
import sys
import threading
import traceback

from run import DEFAULT_DB, DEFAULT_HTML_OUT, main as run_scraper

APP_TITLE = "LJ Discounts"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 780


class DiscountsApp:
    def __init__(self) -> None:
        self.html_path = DEFAULT_HTML_OUT
        self.db_path = DEFAULT_DB
        self.window = None
        self._lock = threading.Lock()
        self._is_refreshing = False

    def start(self) -> None:
        import webview

        self.window = webview.create_window(
            APP_TITLE,
            html=self._status_html("Starting LJ Discounts", "Preparing the app window..."),
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=(820, 560),
            js_api=self,
        )
        webview.start(self.refresh)

    def refresh(self) -> dict[str, str | bool]:
        with self._lock:
            if self._is_refreshing:
                return {"ok": False, "message": "Refresh already running"}
            self._is_refreshing = True

        thread = threading.Thread(target=self._refresh_worker, daemon=True)
        thread.start()
        return {"ok": True, "message": "Refreshing"}

    def _refresh_worker(self) -> None:
        self._show_status("Refreshing discounts", "Scraping Mercator Rudnik and rebuilding the report...")
        stdout = io.StringIO()
        stderr = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = run_scraper([
                    "--html",
                    str(self.html_path),
                    "--db",
                    str(self.db_path),
                    "--no-open",
                ])
            if code:
                self._show_error("The scraper exited with an error.", stderr.getvalue() or stdout.getvalue())
            else:
                self._load_report()
        except Exception:
            self._show_error("The scraper crashed.", traceback.format_exc())
        finally:
            with self._lock:
                self._is_refreshing = False

    def _load_report(self) -> None:
        if self.window:
            self.window.load_url(self.html_path.resolve().as_uri())

    def _show_status(self, title: str, message: str) -> None:
        if self.window:
            self.window.load_html(self._status_html(title, message))

    def _show_error(self, title: str, details: str) -> None:
        if self.window:
            self.window.load_html(self._error_html(title, details))

    def _status_html(self, title: str, message: str) -> str:
        return _shell_html(
            f"""
            <main class="panel">
              <div class="mark">LJ</div>
              <h1>{_esc(title)}</h1>
              <p>{_esc(message)}</p>
              <div class="loader" aria-hidden="true"></div>
            </main>
            """,
        )

    def _error_html(self, title: str, details: str) -> str:
        return _shell_html(
            f"""
            <main class="panel error">
              <div class="mark">!</div>
              <h1>{_esc(title)}</h1>
              <p>Check your internet connection, then try refreshing.</p>
              <button onclick="window.pywebview.api.refresh()">Refresh</button>
              <details>
                <summary>Details</summary>
                <pre>{_esc(details[-4000:] or "No details available.")}</pre>
              </details>
            </main>
            """,
        )


def _shell_html(content: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{APP_TITLE}</title>
<style>
:root{{
  --bg:#0c0f14;
  --surface:#151a22;
  --surface2:#1e2631;
  --border:rgba(255,255,255,.1);
  --text:#eef2f7;
  --text2:#a7b1c2;
  --accent:#41d77d;
  --danger:#ff7a59;
}}
*{{box-sizing:border-box}}
body{{
  margin:0;
  min-height:100vh;
  display:grid;
  place-items:center;
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  background:var(--bg);
  color:var(--text);
}}
.panel{{
  width:min(520px,calc(100vw - 40px));
  padding:32px;
  border:1px solid var(--border);
  border-radius:8px;
  background:var(--surface);
  box-shadow:0 20px 70px rgba(0,0,0,.35);
}}
.mark{{
  width:52px;
  height:52px;
  display:grid;
  place-items:center;
  margin-bottom:22px;
  border-radius:8px;
  background:var(--accent);
  color:#06110a;
  font-weight:900;
}}
h1{{
  margin:0 0 10px;
  font-size:25px;
  line-height:1.15;
}}
p{{
  margin:0;
  color:var(--text2);
  line-height:1.5;
}}
.loader{{
  width:100%;
  height:7px;
  margin-top:26px;
  border-radius:999px;
  overflow:hidden;
  background:var(--surface2);
}}
.loader::before{{
  content:"";
  display:block;
  width:42%;
  height:100%;
  border-radius:inherit;
  background:var(--accent);
  animation:slide 1s ease-in-out infinite alternate;
}}
button{{
  margin-top:22px;
  min-height:38px;
  padding:0 18px;
  border:0;
  border-radius:6px;
  background:var(--accent);
  color:#06110a;
  font-weight:800;
  cursor:pointer;
}}
details{{
  margin-top:22px;
  color:var(--text2);
}}
summary{{cursor:pointer}}
pre{{
  overflow:auto;
  max-height:220px;
  padding:14px;
  border-radius:6px;
  background:#090b0f;
  white-space:pre-wrap;
  color:#d8dee9;
}}
.error .mark{{
  background:var(--danger);
  color:#190603;
}}
@keyframes slide{{
  from{{transform:translateX(-8%)}}
  to{{transform:translateX(150%)}}
}}
</style>
</head>
<body>{content}</body>
</html>"""


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main() -> int:
    try:
        DiscountsApp().start()
        return 0
    except ModuleNotFoundError as exc:
        if exc.name == "webview":
            print(
                "Missing desktop app dependency. Install it with: "
                "python -m pip install -r requirements-windows.txt",
                file=sys.stderr,
            )
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
