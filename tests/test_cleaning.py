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
            "job_id": ["site_1", "site_2", "site_3"],
            "source_job_id": ["1", "2", "3"],
            "job_title_raw": ["  Software Engineer  ", "Graphic Designer", "Remote QA Engineer"],
            "company_raw": ["WSO2 &amp; Co", "Creative Studio", "Tech Corp"],
            "country_raw": ["Sri Lanka", "lk", "Sri Lanka"],
            "location_raw": ["Colombo 03", "Kandy", ""],
            "job_description_raw": [
                "<p>Development role description involving software development, application design, testing, debugging, database integration, and collaboration with the engineering team.</p>",
                "<p>Creative role involving graphic design, visual content creation, branding, digital media production, collaboration with clients, and preparation of marketing materials.</p>",
                "<p>Quality assurance and automation testing role requiring solid Python background. This is a very long description to ensure it exceeds the 100 characters threshold required by the cleaning pipeline.</p>"
            ],
            "posted_date_raw": ["2026-08-25", "2026-08-25", "2026-08-25"],
            "closing_date_raw": ["2026-09-25", "2026-09-25", "2026-09-25"],
            "requirements_raw": ["<ul><li>Bachelor's degree</li><li>Python experience</li></ul>","<ul><li>Portfolio required</li></ul>", "<ul><li>QA experience</li></ul>"],
            "description_type": ["html_text", "html_text", "html_text"],
            "source_hostname": ["wso2.com", "creatives.lk", "techcorp.com"],
            "extraction_status": ["success", "success", "success"],
        }
        df_raw = pd.DataFrame(raw_data)

        # Execute cleaning
        df_internal, df_team, stats = clean_raw_dataframe(df_raw)

        # 1. Verify WSO2 was cleaned and kept
        self.assertEqual(len(df_internal), 3)
        wso2_row = df_internal[df_internal["source_platform"] == "wso2.com"].iloc[0]
        self.assertEqual(wso2_row["job_title_raw"], "Software Engineer")
        self.assertEqual(wso2_row["company_raw"], "WSO2 & Co")  # HTML unescaped
        self.assertEqual(wso2_row["country"], "Sri Lanka")
        self.assertEqual(wso2_row["job_description_clean"], "Development role description involving software development, application design, testing, debugging, database integration, and collaboration with the engineering team.")

        # Verify empty location is cleaned to "Remote Work"
        remote_row = df_internal[df_internal["source_platform"] == "techcorp.com"].iloc[0]
        self.assertEqual(remote_row["location_raw"], "Remote Work")

        # 2. Verify team schema has exactly 10 standard columns
        self.assertEqual(len(df_team.columns), 10)
        self.assertTrue("company" in df_team.columns)
        self.assertTrue("job_description" in df_team.columns)
        self.assertTrue("posted_date" in df_team.columns)
        self.assertTrue("location_raw" in df_team.columns)
        
        # Verify "Remote Work" location is in the team dataset
        remote_team_row = df_team[df_team["company"] == "Tech Corp"].iloc[0]
        self.assertEqual(remote_team_row["location_raw"], "Remote Work")

        # 3. Verify deduplication stats are reported
        self.assertEqual(stats["total_raw_records"], 3)

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
