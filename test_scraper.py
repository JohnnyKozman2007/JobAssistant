"""
# Test a single URL:
    python test_scraper.py "https://www.indeed.com/viewjob?jk=abc123"

# Test multiple URLs:
    python test_scraper.py "https://..." "https://..." "https://..."

# Or edit the URLS list below and run with no arguments:
    python test_scraper.py
"""

import sys
import logging
from scraper import scrape_job_description, ScraperError

# Configure logging (shows which strategy fired) 
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# Hardcoded URLs - in case of running without args
URLS = [
    "https://www.indeed.com/q-Junior-Data-Scientist-jobs.html?vjk=b65e7472df9f9c50",
    "https://job-boards.greenhouse.io/anthropic/jobs/5097186008",
    "https://workday.wd5.myworkdayjobs.com/en-US/Workday/job/Machine-Learning-Engineer_JR-0105123-1?source=Careers_Website_mlai",
    "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4389538828",
]


# Helpers 
def run(url: str) -> None:
    print(f"\n{'=*' * 86}")
    print(f"URL: {url}")
    print('=*' * 86)
    try:
        text = scrape_job_description(url)
        print(f"{len(text):,} chars extracted\n")
        print(text[:1000])
        if len(text) > 1000:
            print(f"\n... [{len(text) - 1000:,} more chars]")
    except ScraperError as e:
        print(f"ScraperError: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


# Entry point 
if __name__ == "__main__":
    urls = sys.argv[1:] or URLS
    if not urls:
        print("No URLs provided. Pass them as arguments or edit the URLS list in the script.")
        sys.exit(1)

    for url in urls:
        run(url)