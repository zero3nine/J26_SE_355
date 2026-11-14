"""Explicit browser QA: .venv/Scripts/python tests/browser_public_dashboard.py.

Requires installed Playwright Chromium; not part of offline unittest discovery.
Uses a temporary synthetic snapshot and its own local server.
"""
from __future__ import annotations

import csv
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from public_dashboard.publication import publish, synthetic_records


class DashboardBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.output = ROOT / "tmp/dashboard-qa"
        cls.output.mkdir(parents=True, exist_ok=True)
        database = Path(cls.temp.name) / "public.sqlite3"
        publish(synthetic_records(), database, {"title": "Browser demo", "provenance": "Synthetic seed 355", "is_synthetic": True})
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.url = f"http://127.0.0.1:{port}"
        cls.server = subprocess.Popen([sys.executable, "-m", "public_dashboard.app", "--port", str(port), "--database", str(database)],
                                      cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        def stop_server():
            cls.server.terminate()
            try:
                cls.server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.server.kill(); cls.server.wait()
        cls.addClassCleanup(stop_server)
        for _ in range(60):
            try:
                with urllib.request.urlopen(cls.url+"/healthz", timeout=1):
                    break
            except OSError:
                time.sleep(.2)
        else:
            raise RuntimeError("Test server did not start.")
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1100}, color_scheme="light")
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.url, wait_until="networkidle")
        self.ready()

    def ready(self):
        self.page.wait_for_selector('#analysis[aria-busy="false"] .kpi-value')

    def view(self, name):
        self.page.locator(f'#navigation [data-view="{name}"]').click()

    def change(self, selector, value):
        with self.page.expect_response(lambda r: "/api/analysis?" in r.url):
            self.page.locator(selector).select_option(value)
        self.ready()

    def test_desktop_and_all_views(self):
        self.assertEqual(self.page.locator(".kpi-value").first.inner_text(), "1,512")
        self.page.screenshot(path=str(self.output / "overview-desktop.png"), full_page=True)
        for view in ("careers", "trends", "markets", "connections", "methods"):
            self.view(view)
            self.assertFalse(self.page.evaluate("document.documentElement.scrollWidth > innerWidth"))
            self.page.screenshot(path=str(self.output / f"{view}-desktop.png"), full_page=True)
        self.assertEqual(self.errors, [])

    def test_market_role_search_and_skill_drilldown(self):
        self.change("#country", "Singapore")
        self.assertEqual(self.page.locator(".kpi-value").first.inner_text(), "1,152")
        self.change("#role", "Data & AI")
        self.assertLess(int(self.page.locator(".kpi-value").first.inner_text().replace(",", "")), 1152)
        self.view("careers")
        self.page.locator("#skill-search").fill("Python")
        self.assertEqual(self.page.locator("#skill-table tbody tr").count(), 1)
        self.page.locator("#skill-sort").select_option("name")
        with self.page.expect_response(lambda r: "/api/analysis?" in r.url):
            self.page.locator("#skill-table [data-skill='Python']").click()
        self.ready()
        self.assertIn("skill=Python", self.page.url)
        self.view("trends")
        self.assertIn("How Python demand is changing", self.page.locator("#analysis").inner_text())
        self.assertEqual(self.errors, [])

    def test_empty_selection_and_reset(self):
        self.change("#country", "Singapore")
        self.page.locator("#advanced summary").click()
        self.change("#source", "Topjobs")
        self.assertIn("A little too specific?", self.page.locator("#analysis").inner_text())
        self.assertTrue(self.page.locator("#download").is_disabled())
        with self.page.expect_response(lambda r: "/api/analysis?" in r.url):
            self.page.locator("[data-reset]").click()
        self.ready()
        self.assertEqual(self.page.locator(".kpi-value").first.inner_text(), "1,512")

    def test_scoped_download_and_shared_url(self):
        self.change("#country", "Malaysia")
        self.view("markets")
        self.assertEqual(self.page.locator(".bar-row").count(), 4)
        with self.page.expect_download() as info:
            self.page.locator("#download").click()
        data = info.value.path().read_text(encoding="utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(data)))
        self.assertEqual(len(rows), 4)
        self.assertIn('"country": "Malaysia"', rows[0]["scope"])
        self.assertEqual(rows[0]["synthetic"], "True")
        self.page.reload(wait_until="networkidle"); self.ready()
        self.assertEqual(self.page.locator("#country").input_value(), "Malaysia")
        self.assertTrue(self.page.locator('#navigation [data-view="markets"]').get_attribute("aria-current"))

    def test_forecast_and_sparse_period_controls(self):
        self.view("trends")
        self.assertEqual(self.page.locator(".forecast-point").count(), 3)
        self.page.locator("#advanced summary").click()
        with self.page.expect_response(lambda r: "/api/analysis?" in r.url):
            self.page.locator("#min_jobs").fill("10000")
            self.page.locator("#min_jobs").press("Tab")
        self.ready()
        self.assertIn("Not enough jobs per month", self.page.locator("#analysis").inner_text())
        self.assertEqual(self.page.locator(".forecast-point").count(), 0)

    def test_mobile_navigation_readability_and_overflow(self):
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.assertFalse(self.page.evaluate("document.documentElement.scrollWidth > innerWidth"))
        self.page.screenshot(path=str(self.output / "overview-mobile.png"), full_page=True)
        self.assertFalse(self.page.locator("#sidebar").is_visible())
        self.page.locator("#menu-toggle").click()
        self.assertTrue(self.page.locator("#sidebar").is_visible())
        self.view("connections")
        self.assertEqual(self.page.locator("#menu-toggle").get_attribute("aria-expanded"), "false")
        self.assertFalse(self.page.evaluate("document.documentElement.scrollWidth > innerWidth"))
        self.page.screenshot(path=str(self.output / "connections-mobile.png"), full_page=True)
        self.assertEqual(self.errors, [])

    def test_theme_toggle_preserves_analysis_and_remembers_choice(self):
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'light')
        self.change('#country', 'Malaysia')
        self.view('trends')
        before_url = self.page.url
        before_analysis = self.page.locator('#analysis').inner_text()
        requests = []
        self.page.on('request', lambda request: requests.append(request.url))
        toggle = self.page.get_by_role('button', name='Dark mode', exact=True)
        toggle.focus()
        toggle.press('Space')
        self.assertEqual(toggle.get_attribute('aria-pressed'), 'true')
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'dark')
        self.assertEqual(self.page.url, before_url)
        self.assertEqual(self.page.locator('#analysis').inner_text(), before_analysis)
        self.assertFalse(any('/api/' in url for url in requests))
        self.page.reload(wait_until='networkidle'); self.ready()
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'dark')
        self.assertEqual(self.page.locator('#country').input_value(), 'Malaysia')
        with self.page.expect_download() as info:
            self.page.locator('#download').click()
        rows = list(csv.DictReader(io.StringIO(info.value.path().read_text(encoding='utf-8-sig'))))
        self.assertIn('"country": "Malaysia"', rows[0]['scope'])
        self.page.get_by_role('button', name='Dark mode', exact=True).click()
        self.page.reload(wait_until='networkidle'); self.ready()
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'light')
        self.assertEqual(self.errors, [])

    def test_theme_follows_system_until_explicit_choice(self):
        self.page.emulate_media(color_scheme='dark')
        self.page.reload(wait_until='networkidle'); self.ready()
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'dark')
        self.page.emulate_media(color_scheme='light')
        self.page.wait_for_function("() => document.documentElement.dataset.theme === 'light'")
        self.page.get_by_role('button', name='Dark mode', exact=True).click()
        self.page.emulate_media(color_scheme='dark')
        self.page.emulate_media(color_scheme='light')
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'dark')
        self.page.reload(wait_until='networkidle'); self.ready()
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'dark')

    def test_theme_handles_invalid_and_unavailable_storage(self):
        self.page.evaluate("localStorage.setItem('skillscope-theme', 'invalid-theme')")
        self.page.emulate_media(color_scheme='dark')
        self.page.reload(wait_until='networkidle'); self.ready()
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'dark')
        self.page.add_init_script("""
            Storage.prototype.getItem = () => { throw new DOMException('Blocked', 'SecurityError'); };
            Storage.prototype.setItem = () => { throw new DOMException('Blocked', 'SecurityError'); };
        """)
        self.page.reload(wait_until='networkidle'); self.ready()
        self.page.get_by_role('button', name='Dark mode', exact=True).click()
        self.assertEqual(self.page.locator('html').get_attribute('data-theme'), 'light')
        self.view('careers')
        self.assertTrue(self.page.locator('#skill-table').is_visible())
        self.assertEqual(self.errors, [])

    def test_both_themes_all_views_contrast_and_mobile(self):
        for theme in ('light', 'dark'):
            if theme == 'dark':
                self.page.get_by_role('button', name='Dark mode', exact=True).click()
            for view in ('overview', 'careers', 'trends', 'markets', 'connections', 'methods'):
                self.view(view)
                self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                # Check text against its actual nearest opaque surface, not token names.
                failures = self.page.evaluate("""() => {
                    const rgb = value => value.match(/[\\d.]+/g).map(Number);
                    const luminance = c => c.slice(0, 3).map(v => {
                        v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
                    }).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
                    const failures = [];
                    for (const el of document.querySelectorAll(
                        '.page-heading p, .kpi-label, .kpi-note, .card-heading p, .card-footnote, ' +
                        '.nav-button, .button, .notice, .pill, .tag, td, th, .explanation, ' +
                        '.mini-card p, .provenance, .chart-label, .chart-legend, .focus-strip p')) {
                        if (!el.getClientRects().length) continue;
                        const style = getComputedStyle(el);
                        let parent = el;
                        while (parent && rgb(getComputedStyle(parent).backgroundColor)[3] === 0)
                            parent = parent.parentElement;
                        const background = getComputedStyle(parent || document.documentElement).backgroundColor;
                        const foreground = el.matches('.chart-label') ? style.fill : style.color;
                        const a = luminance(rgb(foreground)), b = luminance(rgb(background));
                        const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
                        if (ratio < 4.5) failures.push([el.className.baseVal ?? el.className, foreground, background, ratio]);
                    }
                    return failures;
                }""")
                self.assertEqual(failures, [], (theme, view, failures))
            self.view('overview')
            self.page.screenshot(path=str(self.output / f'overview-{theme}-desktop.png'), full_page=True)
            self.page.set_viewport_size({'width': 390, 'height': 844})
            self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))
            toggle = self.page.get_by_role('button', name='Dark mode', exact=True)
            self.assertTrue(toggle.is_visible())
            self.assertGreaterEqual(toggle.bounding_box()['height'], 44)
            self.page.locator('#menu-toggle').click()
            self.view('connections')
            self.assertFalse(self.page.locator('#sidebar').is_visible())
            self.page.screenshot(path=str(self.output / f'connections-{theme}-mobile.png'), full_page=True)
            self.page.set_viewport_size({'width': 1440, 'height': 1100})
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main()
