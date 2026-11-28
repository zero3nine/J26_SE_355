"""Check the original CLI entry point without collecting from the network."""

import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

from src.scraping import scrape_jobs


class TestLegacyCollectionCLI(unittest.TestCase):
    def test_pipeline_delegates_to_bounded_collection_service(self):
        service = ModuleType("src.scraping.service")
        service.run_collection_pipeline = Mock(return_value=([], "batch"))
        urls = ["https://example.com/jobs"]
        progress = Mock()

        with patch.dict("sys.modules", {service.__name__: service}):
            result = scrape_jobs.run_scraping_pipeline(
                urls, progress_callback=progress, enable_ocr=True, batch_id="batch"
            )

        self.assertEqual(result, ([], "batch"))
        service.run_collection_pipeline.assert_called_once_with(
            urls,
            max_requests=120,
            max_time_seconds=300,
            use_browser_fallback=False,
            use_ocr=True,
            progress_callback=progress,
            batch_id="batch",
            crawl_all_pages=True,
        )

    def test_cli_deduplicates_input_and_bounds_test_mode(self):
        first = "https://example.com/jobs"
        second = "https://example.com/job/123"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "urls.txt").write_text(
                f"# Source URLs\n\n{first}\n{first}\n{second}\n", encoding="utf-8"
            )
            cli_file = root / "src" / "scraping" / "scrape_jobs.py"
            with patch.object(scrape_jobs, "__file__", str(cli_file)), \
                 patch("sys.argv", ["scrape_jobs.py", "--test-limit", "1"]), \
                 patch.object(scrape_jobs, "run_scraping_pipeline") as pipeline:
                scrape_jobs.main()

        args = pipeline.call_args
        self.assertEqual(args.args[0], [first])
        self.assertEqual(args.kwargs["max_requests"], 1)
        self.assertFalse(args.kwargs.get("enable_ocr", False))
