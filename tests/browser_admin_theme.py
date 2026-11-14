"""Explicit admin appearance QA using an isolated project and synthetic records.

Run: .venv/Scripts/python tests/browser_admin_theme.py
Requires installed Playwright Chromium. Never collects live data or opens the
working project's master database. Screenshots: tmp/dashboard-qa/admin/.
"""
import csv
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AdminThemeBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        project = Path(cls.temp.name)
        for directory in ("src", "config", "pages", "tools", "public_dashboard", ".streamlit"):
            shutil.copytree(ROOT / directory, project / directory,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("app.py", "app_shared.py", "theme.py"):
            shutil.copy2(ROOT / name, project / name)
        cls.output = ROOT / "tmp/dashboard-qa/admin"
        cls.output.mkdir(parents=True, exist_ok=True)
        # Seed only this temporary server's session and review CSV.
        fixture = [
            {"job_id": "synthetic-1", "job_title_raw": "Synthetic Python Engineer", "company_raw": "Demo One",
             "source_url": "https://example.com/job/1", "source_platform": "Synthetic",
             "job_description_raw": "Synthetic Python and SQL engineering position for UI verification.",
             "extraction_status": "manual_review", "classification_status": "ambiguous", "source_hostname": "example.com"},
            {"job_id": "synthetic-2", "job_title_raw": "Synthetic Data Analyst", "company_raw": "Demo Two",
             "source_url": "https://example.com/job/2", "source_platform": "Synthetic",
             "job_description_raw": "Synthetic analytical position for UI verification.",
             "extraction_status": "success", "classification_status": "it", "source_hostname": "example.com"},
        ]
        shared = project / "app_shared.py"
        source = shared.read_text(encoding="utf-8")
        source = source.replace("\ninit_session_state()\n", "\ninit_session_state()\n"
                                + "if not st.session_state.get('_theme_qa_seeded'):\n"
                                + f"    st.session_state.raw_df = pd.DataFrame({fixture!r})\n"
                                + "    st.session_state._theme_qa_seeded = True\n", 1)
        shared.write_text(source, encoding="utf-8")
        processed = project / "data/processed"
        processed.mkdir(parents=True)
        with (processed / "jobs_clean_internal.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fixture[0].keys())
            writer.writeheader()
            writer.writerows(fixture)
        # Include populated shared components that otherwise require collection.
        (project / "pages/99_Theme_QA.py").write_text('''import streamlit as st
from app_shared import render_page_shell
from theme import *
render_page_shell()
st.subheader("Synthetic component preview")
st.markdown(render_kpis(4, 2, 1, 1), unsafe_allow_html=True)
st.markdown(render_pipeline_funnel({"total_raw_records": 4, "final_internal_records": 3, "final_team_records": 2}), unsafe_allow_html=True)
st.markdown(render_terminal(["Fetching synthetic record", "Completed successfully", "Error: synthetic failure"]), unsafe_allow_html=True)
st.markdown(render_validation_checklist([{"status":"PASS", "name":"Synthetic check", "details":"Offline preview"}]), unsafe_allow_html=True)
st.markdown(render_custom_table(["Status"], [[make_status_pill("Ready", "success")], [make_status_pill("Review", "warning")], [make_status_pill("Failed", "error")]]), unsafe_allow_html=True)
''', encoding="utf-8")
        subprocess.run([sys.executable, "-c", """from src.database.connection import initialize_database
from src.database.repository import import_jobs_dataframe, record_extraction_run, store_extracted_skills
import pandas as pd
initialize_database()
rows = []
for index, country in enumerate(('Sri Lanka', 'India', 'Singapore', 'Malaysia')):
    for month in range(1, 7):
        rows.append(dict(job_id=f'synthetic-{index}-{month}', source_url=f'https://example.com/{index}/{month}',
                         job_title_raw='Synthetic Software Engineer', company='Synthetic Employer', country=country,
                         location=country, job_description='Synthetic Python and SQL engineering role for appearance checks.',
                         requirements='Python SQL', posting_date=f'2026-{month:02d}-15', classification_status='it',
                         source_platform='Synthetic', skills=['Python', 'SQL']))
frame = pd.DataFrame(rows)
result = import_jobs_dataframe(frame, source_name='Synthetic UI fixture')
assert result['inserted_jobs'] == 24, result
run = record_extraction_run('both', notes='Synthetic UI fixture')
for method in ('lexical', 'semantic'):
    assert store_extracted_skills(frame, run, method, 'skills') > 0
"""],
                       cwd=project, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.url = f"http://127.0.0.1:{port}"
        cls.log = (cls.output / "server.log").open("w", encoding="utf-8")
        cls.addClassCleanup(cls.log.close)
        cls.server = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py",
                                       "--server.headless", "true", "--server.address", "127.0.0.1",
                                       "--server.port", str(port), "--browser.gatherUsageStats", "false"],
                                      cwd=project, stdout=cls.log, stderr=cls.log,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        def stop_server():
            cls.server.terminate()
            try:
                cls.server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.server.kill()
                cls.server.wait()
        cls.addClassCleanup(stop_server)
        for _ in range(100):
            try:
                with urllib.request.urlopen(cls.url + "/_stcore/health", timeout=1):
                    break
            except OSError:
                time.sleep(.2)
        else:
            raise RuntimeError("Temporary admin server did not start")
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width":1440, "height":1050}, color_scheme="light")
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.url)
        self.ready()

    def ready(self):
        self.page.wait_for_selector('[data-testid="stMain"] h1', timeout=60000)
        self.page.wait_for_function("getComputedStyle(document.documentElement).getPropertyValue('--admin-paper').trim() === '#f7f9fc'")
        self.page.wait_for_timeout(300)
        self.page.locator('[data-testid="stStatusWidget"]').filter(has_text="Running").wait_for(state="hidden", timeout=60000)
        self.assertEqual(self.page.locator('[data-testid="stException"]').count(), 0)

    def navigate(self, text):
        self.page.locator('[data-testid="stSidebarNav"]').get_by_role("link", name=text, exact=True).click()
        self.ready()

    def assert_layout(self):
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
        self.assertEqual(self.errors, [])
        self.assertEqual(self.page.locator('[data-testid="stException"]').count(), 0)

    def test_all_modules(self):
        links = self.page.locator('[data-testid="stSidebarNav"] a').all_text_contents()
        self.assertEqual(len(links), 17)  # Home, 15 modules, temporary component preview.
        for label in links:
            with self.subTest(module=label):
                self.navigate(label.strip())
                self.assert_layout()
                if label.strip() == "Regional Analysis":
                    self.page.get_by_text("Focal Market (Sri Lanka)", exact=True).wait_for()
                self.page.screenshot(path=str(self.output / (label.strip().replace(" ", "-") + "-desktop.png")), full_page=True)

    def test_search_and_collection_mode(self):
        self.navigate("Raw Data")
        rows = self.page.locator(".console-table tbody tr")
        self.assertEqual(rows.count(), 2)
        search = self.page.get_by_role("textbox", name="Search by title / company:")
        search.fill("Python")
        search.press("Enter")
        self.page.wait_for_timeout(900)
        self.assertEqual(rows.count(), 1)
        self.assertIn("Python", rows.inner_text())
        search.fill("")
        search.press("Enter")
        self.page.wait_for_timeout(900)
        self.assertEqual(rows.count(), 2)
        with self.page.expect_download() as download:
            self.page.locator('[data-testid="stDownloadButton"] button').click()
        with Path(download.value.path()).open(encoding="utf-8", newline="") as file:
            self.assertEqual(len(list(csv.DictReader(file))), 2)
        self.navigate("Collect Data")
        self.page.get_by_text("Historical Data Import", exact=True).click()
        self.page.get_by_role("heading", name="Import historical job advertisements").wait_for()
        self.assert_layout()
        self.page.screenshot(path=str(self.output / "import-desktop.png"), full_page=True)

    def test_all_modules_mobile(self):
        destinations = self.page.locator('[data-testid="stSidebarNav"] a').evaluate_all("links => links.map(link => ({text:link.textContent, href:link.href}))")
        self.page.set_viewport_size({"width":390,"height":844})
        for destination in destinations:
            with self.subTest(module=destination["text"]):
                self.page.goto(destination["href"])
                self.ready()
                self.assert_layout()
                name = destination["text"].strip().replace(" ", "-")
                self.page.screenshot(path=str(self.output / (name + "-mobile.png")), full_page=True)

    def test_component_contrast(self):
        self.navigate("Theme QA")
        samples = self.page.locator(".header-tagline, .kpi-label, .kpi-value, .kpi-trend span, .status-pill, .terminal-line, .info-banner-content").evaluate_all("""elements => elements.map(el => {
            let parent = el, background = 'rgb(247, 249, 252)';
            while(parent) {
                const candidate = getComputedStyle(parent).backgroundColor;
                if(candidate !== 'rgba(0, 0, 0, 0)' && candidate !== 'transparent') { background = candidate; break; }
                parent = parent.parentElement;
            }
            return {text: el.textContent, ink: getComputedStyle(el).color, background};
        })""")
        def luminance(css):
            import re
            rgb = [float(x) / 255 for x in re.findall(r"[\d.]+", css)[:3]]
            values = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
            return sum(c * weight for c, weight in zip(values, (.2126, .7152, .0722)))
        self.assertGreaterEqual(len(samples), 15)
        for sample in samples:
            light, dark = sorted((luminance(sample["ink"]), luminance(sample["background"])), reverse=True)
            self.assertGreaterEqual((light + .05) / (dark + .05), 4.5, sample)

    def test_mobile_and_focus(self):
        self.navigate("Theme QA")
        self.page.set_viewport_size({"width":390,"height":844})
        self.page.wait_for_timeout(800)
        self.assert_layout()
        self.page.screenshot(path=str(self.output / "components-mobile.png"), full_page=True)
        # Confirm keyboard focus remains visible without triggering any action.
        self.page.keyboard.press("Tab")
        self.page.wait_for_timeout(100)
        self.assertTrue(self.page.evaluate("document.activeElement.matches(':focus-visible')"))
        self.assertGreaterEqual(self.page.evaluate("parseFloat(getComputedStyle(document.activeElement).outlineWidth)"), 2)


if __name__ == "__main__":
    unittest.main()
