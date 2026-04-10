# Job Description Scraper

Fetches a job posting URL and returns clean plain text.

---

## Files

- `scraper.py` — core scraping library
- `test_scraper.py` — CLI test script

---

## Install

```bash
pip install playwright requests trafilatura curl-cffi cloudscraper
playwright install chromium
```

`curl-cffi` and `cloudscraper` are required for Indeed. `trafilatura` is required for LinkedIn. All others are required in general.

---

## How it works

`scrape_job_description(url: str) -> str` is the single public function. It routes by domain, fetches the page, then runs up to three extraction strategies in order, returning the first result that exceeds 200 chars.

**Fetch routing**

| Domain | Method | Reason |
|---|---|---|
| `linkedin.com` | `requests` -> LinkedIn guest API (`/jobs-guest/jobs/api/jobPosting/{id}`) | Clean REST endpoint, no JS needed |
|`linkdein.com` option 2 |`curl_cffi` -> `cloudscraper` -> `requests`  | guest API theorically can lead to IP ban depending on volume of request|
| `indeed.com` | `curl_cffi` -> `cloudscraper` -> `requests` | Cloudflare blocks headless browsers; TLS impersonation works at HTTP layer |
| Everything else | Playwright headless Chromium (`networkidle`) | Handles JS-rendered SPAs, lazy-loaded content |

**Extraction strategies** (tried in order)

1. **Site CSS selector** — known high-precision selectors per platform (defined in `_SITE_SELECTORS`), queried on the live post-JS DOM via Playwright's locator API.
2. **Trafilatura** — readability-based extraction on the fully rendered HTML.
3. **Heuristic JS** — injected JavaScript strips noise tags and class/id patterns, then returns `innerText` of the best semantic container (`main`, `article`, or job-related id/class).

**Stealth measures** (Playwright contexts)

- `navigator.webdriver` overridden to `undefined`
- `AutomationControlled` Blink feature disabled
- Realistic viewport (1280×900), locale (`en-US`), timezone (`America/New_York`)

---

## Tested platforms

Greenhouse, Indeed, LinkedIn, Workday, 

---

## Usage

**In a script or production code:**

```python
from scraper import scrape_job_description, ScraperError

try:
    text = scrape_job_description("https://www.linkedin.com/jobs/view/...")
    print(text)
except ScraperError as e:
    print(f"Failed: {e}")
```


**CLI test script:**

```bash
# single URL
python test_scraper.py "https://www.indeed.com/viewjob?jk=abc123"

# multiple URLs
python test_scraper.py "https://..." "https://..."

# or edit the URLS list inside the script and run with no arguments
python test_scraper.py
```

Prints status, char count, and a 1000-char preview per URL. `INFO` logs show which fetch path and extraction strategy fired.

**note:** In Jupyter, the sync wrapper raises inside a running event loop. Should have to use an async version (not implemented)

---

## Errors & Concerns 

All failures raise `ScraperError` with a descriptive message. Common causes:
- **Timeout** — site has aggressive bot detection (add it to the Indeed-style HTTP path if headless keeps failing)
- **HTTP 403/404** — posting removed or access denied
- **All strategies failed** — page is heavily JS-gated or requires authentication

Possible future errors:
- LinkdIn might change the endpoint for "guest API" 
- Maybe proxy rotation if a website blocks scrapers by IP address (BrightData, ScraperAPI, Zyte)
- Specific CSS selectors might stop working when website changes HTML - maybe log url that fails every stragey

Concerns:
- Parsing will be handled by who? - maybe LLM would be better 
- scrape_job_description(url) kinda slow, latency of ~3-10 seconds - maybe asynchrounrous processing
- scraping almost everything - maybe only Job Description, Requirements, and some other stuff

LinkdIN:
- We're using a public guest API to extract LinkdIn JD. It works, but it can lead to IP ban (its not legal). We could use Playwritgh but we would have the user to authenticate first https://dev.to/victorlg98/tutorial-web-scraping-linkedin-jobs-with-playwright-2h7l
- Use same approach as INdeed (curl_cffi -> cloudscraper -> requests). IT WORKS, but heavier.