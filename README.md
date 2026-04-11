# Job Description Scraper

Fetches a job posting URL and returns clean plain text.

---

## Files

- `scraper.py` — core scraping library
- `test_scraper.py` — Pytest unit tests (mocked)

---

## Install

```bash
pip install playwright requests trafilatura curl-cffi cloudscraper
playwright install chromium
```

`curl-cffi` and `cloudscraper` are required for Indeed and LinkdIn. `trafilatura` is used for readability extraction. `pytest` is required for running the tests. All others are required in general.

---

## How it works

`scrape_job_description(url: str) -> str` is the single public function. It routes by domain, fetches the page, then runs up to three extraction strategies in order, returning the first result that exceeds 200 chars.

### Fetch routing

| Domain | Method | Reason |
|---|---|---|
|`linkdein.com` |`curl_cffi` -> `cloudscraper` -> `requests`  | Uses TLS impersonation to bypass bot detection at the HTTP layer. URL is normalized to /jobs/view/{id}.|
| `indeed.com` | `curl_cffi` -> `cloudscraper` -> `requests` | Cloudflare blocks headless browsers; TLS impersonation works at HTTP layer |
| Everything else | Playwright headless Chromium (`networkidle`) | Handles JS-rendered SPAs, lazy-loaded content |

### Extraction strategies (tried in order)

1. **For HTTP-fetches sites (LinkdeIn, Indeed)** 
    1. `Trafilatura` - Applied directly to the static HTML response.
    2. `Site CSS selector` - If Trafilatura fails, HTML is injected into a headless page to query known selectors
    3. `Heuristics JS` - In-browser noise stripping to find the largest text block.
2. **For Browser-fetched sites (Playwright)**
    1. `Site CSS Selector` - Known high-precision selectors queried on the live post-JS DOM.
    2. `Trafilatura` - Readability-based extraction on the fully rendered HTML.
    3. `Heurustic JS` - Injected JavaScript strips noise tags and returns the best semantic container.

### Stealth measures (Playwright contexts)

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
from Agent.scraper import scrape_job_description, ScraperError

try:
    text = scrape_job_description("https://www.linkedin.com/jobs/view/...")
    print(text)
except ScraperError as e:
    print(f"Failed: {e}")
```


## Testing

```bash
# run all test with pytest
pytest Agent/test_scraper.py -v
pytest --cov=Agent.scraper --cov-report=term-missing Agent/test_scraper.py

# single URL
python3 -c "from Agent.scraper import scrape_job_description; text = scrape_job_description('https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4389538828'); print(text[:1000])"
```

The test suite mocks all external network requests (requests, curl_cffi) and browser interactions (Playwright) to ensure logic is validated without hitting real servers.

**note:** In Jupyter, the sync wrapper raises inside a running event loop. Should have to use an async version (not implemented)

---

## Errors & Concerns 

All failures raise `ScraperError` with a descriptive message. Common causes:
- **Timeout** — site has aggressive bot detection (add it to the Indeed-style HTTP path if headless keeps failing)
- **HTTP 403/404** — posting removed or access denied
- **All strategies failed** — page is heavily JS-gated or requires authentication

Possible future errors:
- Maybe proxy rotation if a website blocks scrapers by IP address (BrightData, ScraperAPI, Zyte)
- Specific CSS selectors might stop working when website changes HTML - maybe log url that fails every stragey
- LinkdIn might change the endpoint for "guest API" (EVEN THOUGH WE DONT CURRENTLY USE IT)

Concerns:
- Parsing will be handled by who? - maybe LLM would be better 
- scrape_job_description(url) kinda slow, latency of ~3-10 seconds - maybe asynchrounrous processing
- scraping almost everything - maybe only Job Description, Requirements, and some other stuff

LinkdIN:
- We're using a public guest API to extract LinkdIn JD. It works, but it can lead to IP ban (its not legal). We could use Playwritgh but we would have the user to authenticate first https://dev.to/victorlg98/tutorial-web-scraping-linkedin-jobs-with-playwright-2h7l
- Use same approach as INdeed (curl_cffi -> cloudscraper -> requests). IT WORKS, but heavier.