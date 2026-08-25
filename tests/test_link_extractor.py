import unittest
from src.scraping.link_extractor import LinkExtractor


class TestLinkExtractor(unittest.TestCase):
    """Unit tests for LinkExtractor heuristics and validations."""

    def setUp(self):
        self.extractor = LinkExtractor()
        self.base_url = "https://itpro.lk/jobs/"
        
        self.mock_html = """
        <html>
            <body>
                <!-- Valid Job Link by URL Path -->
                <a href="/jobs/python-developer-colombo/">Python Developer</a>
                
                <!-- Valid Job Link by Query Param -->
                <a href="https://itpro.lk/job-details?id=99281">QA Engineer</a>
                
                <!-- Valid Job Link by Text Heuristic -->
                <a href="/career/position-301">Associate DevOps Specialist</a>
                
                <!-- External Link - Should be skipped -->
                <a href="https://evil.com/jobs/designer">Graphic Designer at Evil Corp</a>
                
                <!-- Non-HTTP Scheme - Should be skipped -->
                <a href="javascript:void(0)">Click here</a>
                
                <!-- Static Asset - Should be skipped -->
                <a href="/jobs/brochure.pdf">Job Advert PDF Flyer</a>
                
                <!-- System Route - Should be skipped -->
                <a href="/jobs/login">Login to view jobs</a>
                
                <!-- Short/Navigation text - Should be skipped -->
                <a href="/jobs/next-page">Next</a>
                <a href="/about-us">About Us</a>
            </body>
        </html>
        """

    def test_extract_job_links(self):
        links = self.extractor.extract_job_links(self.base_url, self.mock_html)
        
        # Check that we extracted the 3 valid links
        self.assertIn("https://itpro.lk/jobs/python-developer-colombo/", links)
        self.assertIn("https://itpro.lk/job-details?id=99281", links)
        self.assertIn("https://itpro.lk/career/position-301", links)
        
        # Check that we did NOT extract invalid or skipped links
        self.assertNotIn("https://evil.com/jobs/designer", links)
        self.assertNotIn("https://itpro.lk/jobs/brochure.pdf", links)
        self.assertNotIn("https://itpro.lk/jobs/login", links)
        self.assertNotIn("https://itpro.lk/jobs/next-page", links)
        self.assertNotIn("https://itpro.lk/about-us", links)
        
        # Ensure length is exactly 3
        self.assertEqual(len(links), 3)


if __name__ == "__main__":
    unittest.main()
