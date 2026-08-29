"""
Unit tests for the multi-site cleaning pipeline.
"""

import unittest
import pandas as pd
from src.cleaning.clean_jobs import clean_raw_dataframe


class TestCleaningPipeline(unittest.TestCase):

    def test_cleaning_extended_schema(self):
        # A mix of old and new schema columns to verify backward compatibility
        raw_data = {
            "job_id": ["site_1", "site_2"],
            "source_job_id": ["1", "2"],
            "job_title_raw": ["  Software Engineer  ", "Graphic Designer"],
            "company_raw": ["WSO2 &amp; Co", "Creative Studio"],
            "country_raw": ["Sri Lanka", "lk"],
            "location_raw": ["Colombo 03", "Kandy"],
            "job_description_raw": ["<p>Development role description</p>", "Creative role"],
            "posted_date_raw": ["2026-08-25", "2026-08-25"],
            "closing_date_raw": ["2026-09-25", "2026-09-25"],
            "description_type": ["html_text", "html_text"],
            "source_hostname": ["wso2.com", "creatives.lk"],
            "extraction_status": ["success", "success"],
        }
        df_raw = pd.DataFrame(raw_data)

        # Execute cleaning
        df_internal, df_team, stats = clean_raw_dataframe(df_raw)

        # 1. Verify WSO2 was cleaned and kept
        self.assertEqual(len(df_internal), 2)
        wso2_row = df_internal[df_internal["source_platform"] == "wso2.com"].iloc[0]
        self.assertEqual(wso2_row["job_title_raw"], "Software Engineer")
        self.assertEqual(wso2_row["company_raw"], "WSO2 & Co")  # HTML unescaped
        self.assertEqual(wso2_row["country"], "Sri Lanka")
        self.assertEqual(wso2_row["job_description_clean"], "Development role description")

        # 2. Verify team schema has exactly 10 standard columns
        self.assertEqual(len(df_team.columns), 10)
        self.assertTrue("company" in df_team.columns)
        self.assertTrue("job_description" in df_team.columns)
        self.assertTrue("posted_date" in df_team.columns)

        # 3. Verify deduplication stats are reported
        self.assertEqual(stats["total_raw_records"], 2)

    def test_cleaning_empty_dataframe(self):
        df_raw = pd.DataFrame()
        df_internal, df_team, stats = clean_raw_dataframe(df_raw)
        
        # Verify empty returns
        self.assertTrue(df_internal.empty)
        self.assertTrue(df_team.empty)
        self.assertEqual(stats, {})
        
        # Verify schema is populated correctly
        expected_cols = [
            "job_id", "source_job_id", "job_title_raw", "company_raw", "country", "location_raw",
            "job_description_raw", "job_description_clean", "listing_posted_date_raw", "closing_date_raw",
            "functional_area", "description_type", "advert_image_urls", "ocr_text_raw", "ocr_status",
            "ocr_confidence", "source_platform", "source_url", "canonical_url", "collection_batch_id",
            "scraped_at", "extraction_status", "exclusion_reason",
            "fetch_method", "rendering_used", "failure_reason", "date_conversion_method",
            "date_parse_status", "date_parse_warning", "field_provenance", "classification_status",
            "classification_explanation", "classification_override", "manual_review_reason"
        ]
        self.assertEqual(list(df_internal.columns), expected_cols)


if __name__ == "__main__":
    unittest.main()
