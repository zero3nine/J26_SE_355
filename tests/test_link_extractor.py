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


    def test_extract_topjobs_listing_links(self):
        topjobs_url = "https://topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ&jst=OPEN"
        topjobs_html = """
        <html>
            <body>
                <table id="table">
                    <tr id="tr0" onclick="createAlert('0','0000000375','0001562037','0000000492','JQwQx3XuT0SbaCBX1M6Kq9AM')">
                        <td>1</td><td>0001562037</td>
                        <td><h1>Jobfactory</h1><h2>AI-First SaaS Operations & Delivery Lead</h2></td>
                    </tr>
                    <tr id="tr1" onclick="createAlert('1','0000000375','0001562026','0000000492','JQwQx3XuT0SbaCBX1M6Kq9AM')">
                        <td>2</td><td>0001562026</td>
                        <td><h1>Jobfactory</h1><h2>QA Intern</h2></td>
                    </tr>
                </table>
                <a href="/site_map.jsp;jsessionid=12345">Site Map</a>
                <a href="/testimonials.jsp">Testimonials</a>
            </body>
        </html>
        """
        links = self.extractor.extract_job_links(topjobs_url, topjobs_html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://topjobs.lk/employer/JobAdvertismentServlet?rid=0&ac=0000000375&jc=0001562037&ec=0000000492&pg=applicant/vacancybyfunctionalarea.jsp", links)
        self.assertIn("https://topjobs.lk/employer/JobAdvertismentServlet?rid=1&ac=0000000375&jc=0001562026&ec=0000000492&pg=applicant/vacancybyfunctionalarea.jsp", links)
        self.assertNotIn("https://topjobs.lk/site_map.jsp;jsessionid=12345", links)


    def test_category_navigation_and_filters_excluded(self):
        """Regression test: Ensure category slugs, sub-types, and filter labels are excluded from job candidates."""
        listing_url = "https://itpro.lk/jobs/software-engineering/"
        html = """
        <html>
            <body>
                <!-- Category navigation links - MUST BE EXCLUDED -->
                <a href="/jobs/devops-cloud/">DevOps & Cloud</a>
                <a href="/jobs/ai-and-data/">AI & Data</a>
                <a href="/jobs/management-business/">Management & Business</a>
                <a href="/jobs/software-engineering/fulltime/">Full Time</a>
                <a href="/jobs/software-engineering/internship/">Internship</a>

                <!-- Real job postings - MUST BE EXTRACTED -->
                <a href="/job/15538/software-engineer-intern-at-sans-technologies/">Software Engineer Intern</a>
                <a href="/job/15536/senior-software-engineer-java-at-hatchyard/">Senior Software Engineer - Java</a>
            </body>
        </html>
        """
        links = self.extractor.extract_job_links(listing_url, html)
        self.assertEqual(len(links), 2)
        self.assertIn("https://itpro.lk/job/15538/software-engineer-intern-at-sans-technologies/", links)
        self.assertIn("https://itpro.lk/job/15536/senior-software-engineer-java-at-hatchyard/", links)
        self.assertNotIn("https://itpro.lk/jobs/devops-cloud/", links)
        self.assertNotIn("https://itpro.lk/jobs/ai-and-data/", links)
        self.assertNotIn("https://itpro.lk/jobs/software-engineering/fulltime/", links)


if __name__ == "__main__":
    unittest.main()
