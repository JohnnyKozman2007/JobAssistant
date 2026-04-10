'''
scraper.py Scraper to extract Job Description and relevent INFO from the given URL 
'''

from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from typing import Generator, Optional
from urllib.parse import urlparse, parse_qs

import requests
from playwright.sync_api import (
    sync_playwright,
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

logger = logging.getLogger(__name__)

# custom exception for scraper errors
class ScraperError(Exception):
    """Raised when the scraper cannot produce a usable job description."""

# =====================================================================================
#  CONSTANTS
# =====================================================================================
_REQUESTS_TIMEOUT   = 15      # seconds — used for LinkedIn API + Indeed HTTP calls
_NAVIGATION_TIMEOUT = 30_000  # ms — Playwright page.goto timeout
_SELECTOR_TIMEOUT   = 5_000   # ms — Playwright locator timeout per selector
_MIN_CONTENT_LEN    = 200     # chars — extraction is considered failed below this

# TLS impersonation profiles for curl_cffi, tried in order.
# Rotating profiles helps when Cloudflare flags a specific fingerprint.
_CURL_CFFI_PROFILES = ["chrome124", "chrome120", "chrome116", "chrome110"]

# user-agent string to mimic a real browser and avoid being blocked by websites
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# regex pattern to identify and exclude common non-content elements from the page
_NOISE_PATTERN = (
    r"nav|navigation|header|footer|sidebar|cookie|banner|"
    r"modal|ads?|advertisement|popup|promo|social|share|"
    r"breadcrumb|related|recommend|notification|alert|menu|"
    r"toolbar|search|sign-?in|log-?in"
)

# HTML tags that never hold job-description copy.
_NOISE_TAGS: list[str] = [
    "nav", "header", "footer", "aside",
    "script", "style", "noscript",
    "form", "iframe", "svg", "figure",
    "button", "input", "select", "textarea",
]


# Site-specific CSS selectors ordered by decreasing specificity.
_SITE_SELECTORS: dict[str, list[str]] = {
    "greenhouse.io": [
        "#content",
        "#app_body",
        "[class*='description']",
        "[class*='job-post']",
    ],
    "lever.co": [
        ".posting-description",
        ".section-wrapper",
        "[class*='description']",
    ],
    "indeed.com": [
        "#jobDescriptionText",
        ".jobsearch-jobDescriptionText",
        "[class*='jobDescription']",
    ],
    "linkedin.com": [
        ".description__text",
        ".show-more-less-html__markup",
        ".jobs-description-content__text",
        "[class*='description']",
    ],
    "workday.com": [
        "[data-automation-id='job-posting-details']",
        "[class*='job-posting']",
    ],
    "myworkdayjobs.com": [
        "[data-automation-id='job-posting-details']",
        "[class*='job-posting']",
    ],
    "smartrecruiters.com": [
        ".job-sections",
        "#job-description",
        "[class*='description']",
    ],
    "ashbyhq.com": [
        "#posting-description",
        "[class*='posting-description']",
        "[class*='description']",
    ],
    "icims.com": [
        "#job-content",
        ".iCIMS_JobContent",
        "[class*='iCIMS']",
    ],
}

# =====================================================================================
#  HELPERS
# =====================================================================================

# extract domain name withouth www
def _domain(url: str) -> str:
    """Host without 'www.' prefix (e.g. 'www.indeed.com' → 'indeed.com')."""
    host = urlparse(url).netloc.lower()
    return re.sub(r"^www\.", "", host)

# check wheter url is valid fot http or https
def _validate_url(url: str) -> None:
    """Raise ScraperError early for obviously invalid input."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScraperError(
            f"Invalid URL scheme '{parsed.scheme}' — only http/https are supported."
        )
    if not parsed.netloc:
        raise ScraperError(f"Invalid URL (no host): {url}")

# normalize html text to plain text
def _clean_text(raw: str) -> str:
    """Collapse whitespace and remove leftover HTML artefacts."""
    text = re.sub(r"[ \t]+",   " ",    raw)
    text = re.sub(r" *\n *",   "\n",   text)
    text = re.sub(r"\n{3,}",   "\n\n", text)
    return text.strip()


# =====================================================================================
#  Browser context manager
# =====================================================================================

# even if scrape crashes, browser will be closed due to the context manager's finally block
@contextmanager
def _browser_page() -> Generator[Page, None, None]:
    """
    Launch a stealth Playwright Chromium browser, yield a ready Page,
    then tear everything down cleanly — even on exception.

    Stealth measures applied:
      • navigator.webdriver overridden to undefined
      • Realistic viewport, locale, and timezone
      • AutomationControlled Blink feature disabled
    """
    with sync_playwright() as pw:
        browser: Browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context: BrowserContext = browser.new_context(
            user_agent=_USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
            viewport={"width": 1280, "height": 900},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        # Mask the automation flag before any page script runs.
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page: Page = context.new_page()
        page.set_default_timeout(_NAVIGATION_TIMEOUT)
        try:
            yield page
        finally:
            context.close()
            browser.close()


# =====================================================================================
#  FETCH - site-specific 
# =====================================================================================

# ──────────────────────────── LinkedIn ──────────────────────────── 
def _extract_linkedin_job_id(url: str) -> Optional[str]:
    """
    Parse the numeric LinkedIn job ID from common URL formats:
      • /jobs/view/4115507396
      • /jobs/…/?currentJobId=4377015836
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "currentJobId" in params:
        return params["currentJobId"][0]
    match = re.search(r"/jobs/view/(\d+)", parsed.path)
    if match:
        return match.group(1)
    match = re.search(r"/(\d{7,})(?:/|$)", parsed.path)
    if match:
        return match.group(1)
    return None

# get the JD by calling the LinkedIn guest API 
def _fetch_linkedin(url: str) -> str:
    """
    Fetch via LinkedIn's public guest API — no auth, no browser overhead.

    Endpoint: /jobs-guest/jobs/api/jobPosting/{id}
    returns a partial HTML snippet containing the full job description.
    keep requests here since endpoint is a plain HTTP call that requires no JavaScript execution.
    """
    job_id = _extract_linkedin_job_id(url)
    if not job_id:
        raise ScraperError(
            f"Could not extract LinkedIn job ID from: {url}\n"
            "Supported formats: /jobs/view/{{id}}  or  ?currentJobId={{id}}"
        )

    api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    logger.info("LinkedIn guest API: %s", api_url) # log for LInk API url

    session = requests.Session()
    # set header to mimit real browser, otherwise LinkedIn returns 403 error.  
    session.headers.update({
        "User-Agent": _USER_AGENT,
        "Accept":     "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try: # try request call
        resp = session.get(api_url, timeout=_REQUESTS_TIMEOUT, allow_redirects=True)
        # "handle" errors
        if resp.status_code == 404:
            raise ScraperError(
                f"LinkedIn job {job_id} not found (404) — it may have expired."
            )
        if resp.status_code == 429:
            raise ScraperError(
                "LinkedIn guest API rate-limited. Wait a few minutes and retry."
            )
        resp.raise_for_status()
        return resp.text
    except ScraperError:
        raise
    except requests.exceptions.RequestException as exc:
        raise ScraperError(f"LinkedIn guest API network error: {exc}") from exc


def _fetch_linkedin_http(url: str) -> str:
    """
    Fetch a LinkedIn job page without a browser, using TLS fingerprint impersonation to bypass LinkedIn's bot detection at the HTTP layer.

    URL normalisation:
      Any user-pasted LinkedIn URL is rewritten to the " /jobs/view/{id} " form, which serves the full job description as static HTML — no JS rendering or login required.

    Strategy order:
      1. curl_cffi — TLS fingerprint impersonation (fast, preferred)
      2. cloudscraper — JS challenge solver (heavier, reliable fallback)
      3. plain requests — last resort, may return login wall

    Raises ScraperError if all three are blocked or unavailable.
    """
    job_id = _extract_linkedin_job_id(url)
    if job_id:
        # no login required for public job postings.
        target = f"https://www.linkedin.com/jobs/view/{job_id}"
        logger.info("LinkedIn: normalised URL: %s", target)
    else:
        target = url
        logger.info("LinkedIn: using original URL (could not extract job ID)")

    errors: list[str] = []

    # Attempt 1: curl_cffi (multiple TLS profiles)
    try:
        from curl_cffi import requests as cffi_requests 

        for profile in _CURL_CFFI_PROFILES:
            try:
                resp = cffi_requests.get(
                    target,
                    impersonate=profile,
                    timeout=_REQUESTS_TIMEOUT,
                    allow_redirects=True,
                )
                if resp.status_code == 200 and len(resp.text) > 1000:
                    logger.info("LinkedIn: curl_cffi succeeded (profile=%s)", profile)
                    return resp.text
                logger.debug("LinkedIn: curl_cffi %s -> HTTP %d", profile, resp.status_code)
            except Exception as exc:
                logger.debug("LinkedIn: curl_cffi %s error: %s", profile, exc)

        errors.append("curl_cffi: all profiles blocked")
    except ImportError:
        errors.append("curl_cffi not installed — pip install curl-cffi")

    # Attempt 2: cloudscraper (JS challenge solver)
    try:
        import cloudscraper  # type: ignore[import]

        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        resp = scraper.get(target, timeout=_REQUESTS_TIMEOUT)
        if resp.status_code == 200 and len(resp.text) > 1000:
            logger.info("LinkedIn: cloudscraper succeeded")
            return resp.text
        errors.append(f"cloudscraper: HTTP {resp.status_code}")
    except ImportError:
        errors.append("cloudscraper not installed — pip install cloudscraper")
    except Exception as exc:
        errors.append(f"cloudscraper error: {exc}")

    # Attempt 3: plain requests (may return login wall, but cheap to try)
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        resp = session.get(target, timeout=_REQUESTS_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200 and len(resp.text) > 1000:
            logger.info("LinkedIn: plain requests succeeded")
            return resp.text
        errors.append(f"requests: HTTP {resp.status_code}")
    except Exception as exc:
        errors.append(f"requests error: {exc}")

    raise ScraperError(
        f"LinkedIn blocked all fetch attempts for {target}.\n"
        f"  Errors: {' | '.join(errors)}\n"
        "  Fix: pip install curl-cffi cloudscraper"
    )


# ──────────────────────────── Indeed ────────────────────────────

def _extract_indeed_job_key(url: str) -> Optional[str]:
    """
    Extract the Indeed job key from common URL formats:
      • /viewjob?jk=abc123
      • /q-...-jobs.html?vjk=abc123   (search result URL)
      • /rc/clk?jk=abc123
    """
    params = parse_qs(urlparse(url).query)
    for param in ("jk", "vjk"):
        if param in params:
            return params[param][0]
    return None


def _fetch_indeed(url: str) -> str:
    """
    Fetch an Indeed job page without a browser, bypassing Cloudflare via TLS fingerprint impersonation.

    Indeed serves a JS challenge to headless browsers that never resolves (networkidle never fires), so Playwright is useless here regardless of
    timeout. Trying stay at the HTTP layer and spoof the TLS fingerprint so Cloudflare never triggers the challenge at all.

    URL normalisation:
    Search-result URLs (/q-*?vjk=...) are rewritten to /viewjob?jk=...which always bakes the full JD into #jobDescriptionText server-side.

    Strategy order:
      1. curl_cffi  — TLS fingerprint impersonation (fast, no JS engine)
      2. cloudscraper — JS challenge solver (heavier, reliable fallback)
      3. plain requests — last resort, usually 403 but cheap to try

    Raises ScraperError if all three are blocked or unavailable.
    """
    job_key = _extract_indeed_job_key(url)
    if job_key:
        target = f"https://www.indeed.com/viewjob?jk={job_key}"
        logger.info("Indeed: normalised URL -> %s", target)
    else:
        target = url
        logger.info("Indeed: using original URL (no jk/vjk param found)")

    errors: list[str] = []

    # Attempt 1: curl_cffi (multiple TLS profiles) 
    try:
        from curl_cffi import requests as cffi_requests  # type: ignore[import]

        for profile in _CURL_CFFI_PROFILES:
            try:
                resp = cffi_requests.get(
                    target,
                    impersonate=profile,
                    timeout=_REQUESTS_TIMEOUT,
                    allow_redirects=True,
                )
                if resp.status_code == 200 and len(resp.text) > 1000:
                    logger.info("Indeed: curl_cffi succeeded (profile=%s)", profile)
                    return resp.text
                logger.debug("Indeed: curl_cffi %s -> HTTP %d", profile, resp.status_code)
            except Exception as exc:
                logger.debug("Indeed: curl_cffi %s error: %s", profile, exc)

        errors.append("curl_cffi: all profiles blocked")
    except ImportError:
        errors.append("curl_cffi not installed — pip install curl-cffi")

    #  Attempt 2: cloudscraper (JS challenge solver) 
    try:
        import cloudscraper  

        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        resp = scraper.get(target, timeout=_REQUESTS_TIMEOUT)
        if resp.status_code == 200 and len(resp.text) > 1000:
            logger.info("Indeed: cloudscraper succeeded")
            return resp.text
        errors.append(f"cloudscraper: HTTP {resp.status_code}")
    except ImportError:
        errors.append("cloudscraper not installed — pip install cloudscraper")
    except Exception as exc:
        errors.append(f"cloudscraper error: {exc}")

    # Attempt 3: plain requests (usually 403, butlets try)
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        resp = session.get(target, timeout=_REQUESTS_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200 and len(resp.text) > 1000:
            logger.info("Indeed: plain requests succeeded")
            return resp.text
        errors.append(f"requests: HTTP {resp.status_code}")
    except Exception as exc:
        errors.append(f"requests error: {exc}")

    raise ScraperError(
        f"Indeed blocked all fetch attempts for {target}.\n"
        f"  Errors: {' | '.join(errors)}\n"
        "  Fix: pip install curl-cffi cloudscraper"
    )


#──────────────────────────── Playwright navigation (all other sites) ──────────────────────────── 

# load webpage in Playwright and wait for the page to load
def _navigate(page: Page, url: str) -> None:
    """
    Navigate `page` to `url`, waiting for the network to get idle (JS-rendered content) including SPA, lazy-loaded 
    Raises ScraperError on HTTP errors or navigation failures.
    """
    try:
        logger.info("Playwright navigating to: %s", url) #log
        response = page.goto(url, wait_until="networkidle", timeout=_NAVIGATION_TIMEOUT) # go to page 

    # "hanlding" errors
    except PlaywrightTimeoutError:
        raise ScraperError(f"Page load timed out for {url}")
    except Exception as exc:
        raise ScraperError(f"Playwright navigation error for {url}: {exc}") from exc

    if response is None:
        raise ScraperError(f"Playwright received no response from {url}")

    status = response.status
    if status == 404:
        raise ScraperError(f"Job posting not found (HTTP 404): {url}")
    if status == 403:
        raise ScraperError(
            f"Access denied (HTTP 403) for {url}. "
            "The site may require authentication or has strong bot detection."
        )
    if status >= 400:
        raise ScraperError(f"HTTP {status} fetching {url}")

# =====================================================================================
#  Extraction STRATEGIES
# =====================================================================================

# STRATEGIE 1 - get JD by site-specific CSS selectors using Playwright's live DOM locator API
def _strategy_site_selector(page: Page, domain: str) -> Optional[str]:
    """
    Strategy 1: Try CSS selectors known to contain the JD on X platform.

    Playwright's locator API queries the *live* DOM after JS has run, so it works on SPAs (Workday, Ashby, etc.) that would have returned empty containers under the old BeautifulSoup approach.
    """
    # browse for site in constant and select selectors
    for site_key, selectors in _SITE_SELECTORS.items():
        if site_key not in domain: # ensure to run selecotr in matches domain only
            continue
        # try each selector until one works, if none work return None and move to next strategy
        for sel in selectors: 
            try:
                locator = page.locator(sel) # find element that matches selector
                if locator.count() == 0:
                    continue
                text = _clean_text(locator.first.inner_text(timeout=_SELECTOR_TIMEOUT)) # extract texto 
                if len(text) >= _MIN_CONTENT_LEN: # check if extracted text is long enough to be a valid JD
                    logger.info(
                        "Extraction: site selector '%s' matched (%d chars)", sel, len(text)
                    )
                    return text
            # error handling
            except PlaywrightTimeoutError:
                logger.debug("Selector '%s' timed out", sel)
            except Exception as exc:
                logger.debug("Selector '%s' error: %s", sel, exc)
    return None


# STRATEGIE 2 - try using trafilatura lib
def _strategy_trafilatura(html: str) -> Optional[str]:
    """
    Strategy 2: readability-based content extraction via trafilatura.

    Receives the *fully rendered* HTML from page.content() so it sees the same DOM that the browser user would see, not a static HTTP response.
    """
    try:
        import trafilatura 

        # extract main content
        result = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )
        if result and len(result) >= _MIN_CONTENT_LEN: # check if extracted text is long enough to be a valid JD
            logger.info("Extraction: trafilatura succeeded (%d chars)", len(result))
            return _clean_text(result)
    # error handlinggg
    except ImportError:
        logger.debug("trafilatura not installed — skipping")
    except Exception as exc:
        logger.debug("trafilatura failed: %s", exc)
    return None

# STRATEGIES 3 - 'heuristic' approach; runs custom JavaScript on the page to find the largest text block that doesn't match common noise patterns (nav, header, footer, etc.) 
_HEURISTIC_JS = """
() => {
    const noiseTags    = %s;
    const noisePattern = /(%s)/i;

    // Remove structural boilerplate elements.
    noiseTags.forEach(tag =>
        document.querySelectorAll(tag).forEach(el => el.remove())
    );

    // Remove elements whose class or id matches the noise pattern.
    document.querySelectorAll('*').forEach(el => {
        const cls = typeof el.className === 'string' ? el.className : '';
        const id  = el.id || '';
        if (noisePattern.test(cls) || noisePattern.test(id)) {
            el.remove();
        }
    });

    // Pick the best semantic container — same priority order as the old BS4 code.
    const container = (
        document.querySelector('main')    ||
        document.querySelector('article') ||
        document.querySelector(
            '[id*="job"],[id*="posting"],[id*="description"],[id*="content"]'
        ) ||
        document.querySelector(
            '[class*="job"],[class*="posting"],[class*="description"],[class*="content"]'
        ) ||
        document.body
    );

    return container ? container.innerText : '';
}
""" % (
    # Inject Python values as JS literals.
    str(_NOISE_TAGS).replace("'", '"'),   # Python list > JS array
    _NOISE_PATTERN,
)

# inject and run the above JS in the browser to extract the JD text
def _strategy_heuristic(page: Page) -> Optional[str]:
    """
    Strategy 3: run _HEURISTIC_JS inside the browser to strip noise elementsand return innerText of the best semantic container.

    It runs in-browser it sees the rendered DOM and handles dynamically injected content automatically.
    """
    try:
        raw: str = page.evaluate(_HEURISTIC_JS) # run js (as if were in browser console)
        # clean whitespace, check length, return if good
        if raw:
            text = _clean_text(raw)
            if len(text) >= _MIN_CONTENT_LEN:
                logger.info("Extraction: heuristic succeeded (%d chars)", len(text))
                return text
    except Exception as exc:
        logger.debug("Heuristic JS eval failed: %s", exc)
    return None


# =====================================================================================
#  API - the actual function we call to get JD text
# =====================================================================================

def scrape_job_description(url: str) -> str:
    """
    Fetch a job posting URL and return clean plain-text content.
    -------
    Fetch routing:
    1. Linkedin: requests to the public guest API (no browser overhead)
    2. others: Playwright headless Chromium (JS rendering, bot bypass)
    -------
    Extraction order:
    1. Site-specific CSS selector  (Playwright locator — works on live DOM)
    2. Trafilatura readability engine (fed fully-rendered page.content())
    3. Heuristic JS noise-stripping  (page.evaluate on the live DOM)
    -------
    Parameters:
    1. url : str   HTTP/HTTPS URL of a job posting page.
    -------
    Returns:
    1. str   Clean plain text (≥ 200 chars).
    -------
    Raises:
    1. ScraperError on invalid URL, blocked access, or failed extraction.
    """
    # validate url, get domain and log
    _validate_url(url)
    logger.info("Scraping: %s", url)
    domain = _domain(url)

    # ────────────── LinkedIn: HTTP fetch (curl_cffi -> cloudscraper -> requests) ──────────────
    # Fetches /jobs/view/{id} directly at the HTTP layer — no browser, no login required.
    # LinkedIn's job detail pages are server-rendered, so TLS impersonation via curl_cffi
    # is enough to bypass bot detection without triggering a login wall.
    if "linkedin.com" in domain:
        html = _fetch_linkedin_http(url)

        text = _strategy_trafilatura(html)
        if text:
            return text

        # Parse the static HTML with a throw-away Playwright page (no navigation)
        # so site-selector and heuristic strategies can still run on the DOM.
        with _browser_page() as page:
            page.set_content(html, wait_until="domcontentloaded")
            text = _strategy_site_selector(page, domain)
            if not text:
                text = _strategy_heuristic(page)
        if text:
            return text

        raise ScraperError(f"All extraction strategies failed for LinkedIn job: {url}")

    # ────────────── LinkedIn: guest API (DISABLED — kept for reference) ──────────────
    # The guest API reliably returns the full JD but is an unofficial endpoint.
    # Hitting it at scale risks IP bans. Re-enable if the HTTP fetch above proves
    # unreliable and the legal risk is acceptable for your use case.
    #
    # if "linkedin.com" in domain:
    #     html = _fetch_linkedin(url)
    #
    #     text = _strategy_trafilatura(html)
    #     if text:
    #         return text
    #
    #     with _browser_page() as page:
    #         page.set_content(html, wait_until="domcontentloaded")
    #         text = _strategy_site_selector(page, domain)
    #         if not text:
    #             text = _strategy_heuristic(page)
    #     if text:
    #         return text
    #
    #     raise ScraperError(f"All extraction strategies failed for LinkedIn job: {url}")

    # ────────────── Indeed: HTTP-only, no browser (Cloudflare blocks headless) ──────────────
    if "indeed.com" in domain:
        html = _fetch_indeed(url)  # curl_cffi > cloudscraper > requests

        text = _strategy_trafilatura(html)
        if text:
            return text

        # Parse the static HTML with a throw-away Playwright page (no navigation) so site-selector and heuristic strategies can still run.
        with _browser_page() as page:
            page.set_content(html, wait_until="domcontentloaded")
            text = _strategy_site_selector(page, domain)
            if not text:
                text = _strategy_heuristic(page)
        if text:
            return text

        raise ScraperError(f"All extraction strategies failed for Indeed job: {url}")

    # ────────────── Others: full Playwright browser ───────────────────────────────
    with _browser_page() as page:
        _navigate(page, url) # go to page

        # Strategy 1 — CSS selector 
        text = _strategy_site_selector(page, domain)
        if text:
            return text

        # Strategy 2 — trafilatura 
        html = page.content()
        text = _strategy_trafilatura(html)
        if text:
            return text

        # Strategy 3 — in-browser js
        text = _strategy_heuristic(page)
        if text:
            return text

    raise ScraperError(
        f"All extraction strategies failed for {url}. "
        "The page may have an AGGRESIVVE bot detection or the posting was removed."
    )