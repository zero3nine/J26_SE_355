# 💼 Multi-Site Job-Advertisement Scraping & Cleaning Tool

Welcome! This tool is an academic research prototype designed to collect, clean, and validate job advertisement data from the web. 

It is designed to be **highly user-friendly**: you can paste **any job portal search page or direct job details URL**, and the tool will automatically extract the individual listings, crawl them safely, filter out non-IT postings (like sales or graphic designers), and save everything as a clean, structured CSV table.

---

## 🚀 Quick Start Guide (For Absolute Beginners)

Follow these simple steps to set up and run the application on your computer.

### Step 1: Open Terminal (On Mac)
1. Press `Cmd + Space` on your keyboard to open Spotlight Search.
2. Type **Terminal** and press `Enter`.
3. Paste the following command into Terminal and press `Enter` to navigate to the project folder:
   ```bash
   cd "/Users/gavidurushela/Client Project/Research"
   ```

### Step 2: Activate the Virtual Environment
Activate the pre-configured Python environment to make sure all dependencies are isolated:
```bash
source .venv/bin/activate
```
*(Your terminal prompt should now show `(.venv)` at the beginning of the line).*

### Step 3: Install Required Packages
Run this command to install all necessary Python software libraries:
```bash
pip install -r requirements.txt
```

### Step 4: Launch the Dashboard!
Start the interactive graphical interface:
```bash
python3 -m streamlit run app.py
```
After a few seconds, the application will automatically open in your web browser at:
👉 **`http://localhost:8501`**

---

## 🖥️ How to Use the Streamlit Dashboard (Step-by-Step)

The dashboard is structured into **5 easy-to-use tabs**. Here is how to navigate them:

### 1️⃣ Tab 1: Collect Data (Input & Scrape)
* **What it does**: This is where you enter the website link you want to scrape.
* **How to use it**:
  1. Go to any job website (like `https://itpro.lk/jobs/` or `https://www.topjobs.lk`).
  2. Copy the URL from your browser's address bar. You can copy a **listing index/search page** (e.g. `https://itpro.lk/jobs/quality-assurance/`) or a **direct job vacancy detail page**.
  3. Paste the URL into the large text box in the dashboard (you can paste multiple links, one per line).
  4. *(Optional)* Check **Save submitted URLs to urls.txt** if you want to remember these URLs for later.
  5. Click **Scrape submitted URLs**.
  6. **Watch it work**: A progress bar will show the progress. If you pasted a listing page, it will automatically discover all the vacancy postings on that page, download them safely, and queue them up to scrape.

> [!NOTE]
> **Polite Crawling**: The tool enforces a strict **2-second delay** between requests. This ensures we do not overload the servers of the target website.

---

### 2️⃣ Tab 2: Raw Data (Inspect and Review)
* **What it does**: Displays the raw, unmodified data extracted directly from the web pages.
* **How to use it**:
  * You can search for positions, companies, or filter by specific crawlers using the drop-down selectors.
  * Select a job from the inspector drop-down to see a preview of the job posting's full HTML details.
  * Click **Download raw CSV** to save this raw, unprocessed dataset to your computer.

---

### 3️⃣ Tab 3: Clean Data (Filter & Export)
* **What it does**: Cleans up messy text, standardizes dates, normalizes locations, and **automatically filters out non-IT jobs** (like generic sales, creative designers, operators, or administration roles).
* **How to use it**:
  1. Click the **Clean data** button.
  2. The screen will instantly display statistics comparing raw items vs. cleaned items, including how many non-IT or short postings were excluded.
  3. Inspect the clean 10-column table. Ambiguous jobs (such as managers or general interns) are flagged for manual review instead of being deleted.
  4. Click **Download clean CSV** to save the final cleaned research dataset (e.g. `jobs_clean.csv`) to your computer.

---

### 4️⃣ Tab 4: Quality Report (Data Auditing)
* **What it does**: Audits the collected dataset for quality checks.
* **How to use it**:
  * It verifies if there are missing columns, duplicate IDs, future publication dates, or empty descriptions.
  * You can click **Download Quality Report** to export this health audit as a markdown document.

---

### 5️⃣ Tab 5: Failure Logs (Troubleshooting)
* **What it does**: Keeps a detailed record of why any URL failed to scrape.
* **How to use it**:
  * If a link was rejected because of SSRF security protection, server errors, or because it did not match the IT inclusion keywords, it will be logged here with a detailed explanation.
  * You can download this log as a CSV for review.

---

## 🛠️ Command-Line Interface (For Advanced Users)

If you prefer using the command-line terminal instead of the web browser dashboard, you can run these scripts directly from the repository root:

* **Verify Connection & Download Test**:
  ```bash
  python3 src/scraping/test_download.py
  ```
* **Clean Data CLI**:
  ```bash
  python3 src/cleaning/clean_jobs.py
  ```
* **Validate Quality CLI**:
  ```bash
  python3 src/cleaning/validate_jobs.py
  ```

---

## 🧪 Running the Verification Test Suite

We maintain a complete test suite to ensure the security, extraction, and cleaning modules work correctly. To run the automated tests, open Terminal and execute:

### Run all tests together:
```bash
python3 -m unittest discover -s tests -p "test_*.py" && python3 -m unittest src/test_app.py
```

---

## 🔒 Security & Ethical Crawling Guidelines

> [!WARNING]
> **SSRF Protection & Safety**:
> The tool contains advanced security features to block Server-Side Request Forgery (SSRF). Any attempt to input URLs pointing to local servers (`localhost`, `127.0.0.1`, `169.254.169.254`, etc.) or non-standard ports (other than 80 or 443) will be automatically blocked.

> [!IMPORTANT]
> **Ethical Crawling**:
> Ensure you check the Terms of Use of the target website before executing large crawls. The tool respects a polite 2-second rate-limiting delay and uses an transparent **Academic User-Agent** to identify itself to website administrators.
