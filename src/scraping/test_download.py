import sys
import pathlib
import requests

def main():
    # Define paths using pathlib relative to the script's location
    current_dir = pathlib.Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    urls_file = project_root / "urls.txt"
    output_html_file = project_root / "data" / "raw" / "sample_page.html"

    # Ensure output directory exists
    output_html_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Reading URLs from: {urls_file}")
    if not urls_file.exists():
        print(f"Error: {urls_file} does not exist.")
        sys.exit(1)

    # Read URLs and find the first non-empty one
    with open(urls_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print("Error: urls.txt has no non-empty URLs.")
        sys.exit(1)

    target_url = urls[0]
    print(f"Target URL: {target_url}")

    # Set up transparent academic user-agent
    headers = {
        "User-Agent": "Academic Research Bot/1.0 (Contact: student-researcher@example.edu; Sri Lanka Skills Demand Study)"
    }

    print("Sending GET request...")
    try:
        # Send request with a 20-second timeout
        response = requests.get(target_url, headers=headers, timeout=20)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        sys.exit(1)

    # Print results
    print("\n--- Download Results ---")
    print(f"URL: {target_url}")
    print(f"HTTP Status Code: {response.status_code}")
    print(f"Response Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
    print(f"HTML Character Count: {len(response.text)}")
    print("\n--- HTML Preview (First 500 characters) ---")
    print(response.text[:500])
    print("-------------------------------------------\n")

    # Save to data/raw/sample_page.html
    with open(output_html_file, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Saved complete response to: {output_html_file}")

    # Explain status codes clearly
    if response.status_code == 200:
        print("Status 200: Request succeeded. The server returned the page.")
    elif response.status_code == 403:
        print("Status 403 (Forbidden): The server understood the request but refuses to authorize it. "
              "This usually means the website is blocking requests from automated tools, scraper-like user agents, "
              "or IP addresses. We must not bypass this block.")
    elif response.status_code == 404:
        print("Status 404 (Not Found): The server cannot find the requested URL. The link might be broken or expired.")
    elif response.status_code == 429:
        print("Status 429 (Too Many Requests): The server is rate-limiting us. We have sent too many requests "
              "in a short time. We must respect this and stop or slow down significantly.")
    else:
        print(f"Status {response.status_code}: Received unexpected status code.")

if __name__ == "__main__":
    main()