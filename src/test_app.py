import unittest
import urllib.parse
import pandas as pd
import sys
import pathlib

# Add current dir to system path to import backend
current_dir = pathlib.Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent))

from src.security.url_validator import validate_url
from src.cleaning.clean_jobs import clean_raw_dataframe
from src.scraping.scrape_jobs import get_canonical_url, create_job_id, evaluate_it_job_status

class TestScraperPipeline(unittest.TestCase):
    
    # 1. URL parsing & hostname validations
    def test_hostname_validation(self):
        # Valid hostnames
        is_ok1, _ = validate_url("https://www.topjobs.lk/employer/JobAdvertismentServlet?rid=0&ac=0000000375&jc=0001540527")
        is_ok2, _ = validate_url("https://topjobs.lk/employer/JobAdvertismentServlet?rid=0&ac=0000000375")
        self.assertTrue(is_ok1)
        self.assertTrue(is_ok2)
        
    def test_deceptive_domains_rejection(self):
        # Deceptive lookalike domains or fake domains
        is_ok1, reason1 = validate_url("https://topjobs.lk.example.com/malicious")
        is_ok2, reason2 = validate_url("https://fake-topjobs.lk/malicious")
        is_ok3, reason3 = validate_url("https://www.topjobs.lk.evil.org/malicious")
        
        self.assertFalse(is_ok1)
        self.assertFalse(is_ok2)
        self.assertFalse(is_ok3)
        self.assertTrue("DNS resolution failed" in reason1 or "Unauthorized hostname" in reason1 or "blocked" in reason1)
        self.assertTrue("DNS resolution failed" in reason2 or "Unauthorized hostname" in reason2 or "blocked" in reason2)
        self.assertTrue("DNS resolution failed" in reason3 or "Unauthorized hostname" in reason3 or "blocked" in reason3)

    # 2. SSRF Protection: loopback, localhost, and private IPs
    def test_localhost_and_private_ip_rejection(self):
        # We check localhost (which resolves to 127.0.0.1 or local network)
        is_ok, reason = validate_url("http://localhost:8501")
        self.assertFalse(is_ok)
        
        # Test lookups to local IPs via hostname
        is_ok_ip, reason_ip = validate_url("http://127.0.0.1/malicious")
        self.assertFalse(is_ok_ip)
        
        is_ok_ip2, reason_ip2 = validate_url("http://192.168.1.1/malicious")
        self.assertFalse(is_ok_ip2)

    # 3. Canonical URL extraction and Job ID creation
    def test_canonical_url_and_job_id(self):
        url1 = "https://www.topjobs.lk/employer/JobAdvertismentServlet?rid=0&ac=0000000375&jc=0001540527&ec=0000000492&pg=applicant/vacancybyfunctionalarea.jsp"
        url2 = "https://www.topjobs.lk/employer/JobAdvertismentServlet?ac=0000000375&ec=0000000492&jc=0001540527&pg=applicant/vacancybyfunctionalarea.jsp&rid=0"
        
        canon1 = get_canonical_url(url1)
        canon2 = get_canonical_url(url2)
        self.assertEqual(canon1, canon2)
        
        # Job ID generation
        job_id = create_job_id("topjobs.lk", "0001540527", url1)
        self.assertEqual(job_id, "topjobs.lk_0001540527")

    # 4. IT Inclusion & Exclusion categorization checks
    def test_it_job_inclusion_exclusion(self):
        # Included Software Role
        is_it1, is_ambig1, _ = evaluate_it_job_status("Associate Software Engineer")
        self.assertTrue(is_it1)
        self.assertFalse(is_ambig1)
        
        # Excluded Graphic Designer
        is_it2, _, reason2 = evaluate_it_job_status("Senior Graphic Designer")
        self.assertFalse(is_it2)
        self.assertIn("Non-IT role", reason2)
        
        # Excluded Operator
        is_it3, _, reason3 = evaluate_it_job_status("Printing Machine Operator")
        self.assertFalse(is_it3)
        self.assertIn("Non-IT role", reason3)
        
        # Ambiguous Role (Flagged)
        is_it4, is_ambig4, reason4 = evaluate_it_job_status("Project Manager")
        self.assertTrue(is_it4)
        self.assertTrue(is_ambig4)
        self.assertIn("ambiguous", reason4)

    # 5. Cleaning without modifying raw data
    def test_cleaning_does_not_modify_raw_data(self):
        raw_row = {
            "job_id": "topjobs.lk_1",
            "source_job_id": "1",
            "job_title_raw": "Software Engineer",
            "company_raw": "Test Company",
            "country": "lk",
            "location_raw": "Colombo, Sri Lanka",
            "job_description_raw": "<p>Software job requirement details</p>",
            "listing_posted_date_raw": "Mon Aug 24 2026",
            "closing_date_raw": "Mon Sep 07 2026",
            "functional_area": "SDQ",
            "description_type": "html_text",
            "advert_image_urls": "[]",
            "ocr_text_raw": "",
            "ocr_status": "not_required",
            "ocr_confidence": "-1.0",
            "source_platform": "topjobs.lk",
            "source_url": "https://www.topjobs.lk/1",
            "canonical_url": "https://www.topjobs.lk/1",
            "collection_batch_id": "batch_1",
            "scraped_at": "2026-08-24T18:00:00Z",
            "extraction_status": "success",
            "exclusion_reason": ""
        }
        df_raw = pd.DataFrame([raw_row])
        
        # Keep an exact copy of original raw values
        raw_description_before = df_raw.loc[0, "job_description_raw"]
        
        df_internal, df_team, stats = clean_raw_dataframe(df_raw)
        
        # Verify original raw DataFrame remains unmodified
        self.assertEqual(df_raw.loc[0, "job_description_raw"], raw_description_before)
        
        # Verify internal dataframe cleaned the HTML tag
        self.assertNotIn("<p>", df_internal.loc[0, "job_description_clean"])
        self.assertEqual(df_internal.loc[0, "country"], "Sri Lanka")
        self.assertEqual(stats["total_raw_records"], 1)

if __name__ == "__main__":
    unittest.main()
