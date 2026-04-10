from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote
from bs4 import BeautifulSoup
import time
import ollama
import json
import re as _re
from concurrent.futures import ThreadPoolExecutor, as_completed

# https://www.sainsburys.co.uk/gol-ui/SearchResults/

# https://home.bargains/search?q=

# https://groceries.morrisons.com/search?q=

FORCE_HEURISTIC_FALLBACK = False
FORCE_LLM_HEURISTIC_BYPASS = False

#DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_MODEL = "gemma4:e4b"
FALLBACK_MODEL = "phi3:3.8b"

# Tags that are pure noise — remove entirely including their children
_STRIP_TAGS = [
    "script", "style", "svg", "noscript", "img", "picture", "source",
    "header", "footer", "nav", "aside", "iframe", "video", "audio",
    "form", "input", "button", "meta", "link", "head",
]

# Attributes worth keeping — everything else is stripped
_KEEP_ATTRS = {"href", "class", "data-testid", "data-test", "data-retailer-anchor", "id"}

# Price patterns
_PRICE_RE = _re.compile(
    r"(?:£)\s*\d+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?\s*p\b",
    _re.IGNORECASE,
)

def get_sainsburys_results(search_query):
    print(f"\n{'='*60}")
    print(f"[Sainsbury's] Starting search for: {search_query!r}")
    print(f"{'='*60}")
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36"
    )
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
 
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
 
    encoded_query = quote(search_query)
 
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.setBlockedURLs", {
        "urls": [
            "*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif", "*.svg",
            "*.woff", "*.woff2", "*.ttf", "*.otf",
            "*google-analytics.com/*", "*googletagmanager.com/*",
            "*doubleclick.net/*", "*facebook.net/*", "*hotjar.com/*",
        ]
    })
 
    search_url = f"https://www.sainsburys.co.uk/gol-ui/SearchResults/{encoded_query}"
    print(f"[Sainsbury's] Navigating to: {search_url}")
    driver.get(search_url)
    print(f"[Sainsbury's] Page loaded. Title: {driver.title!r}  |  HTML size: {len(driver.page_source)} chars")

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.pt__link")))

    if FORCE_HEURISTIC_FALLBACK:
        print("[Sainsbury's] FORCE_HEURISTIC_FALLBACK enabled — skipping CSS extraction.")
        results = fallback_llm_search(driver.page_source, site='sainsburys')
        driver.quit()
        return results

    try:
        wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "article[data-testid^='product-tile-']")
            )
        )
        time.sleep(1)
    except:
        print("[Sainsbury's] Product grid not found — invoking LLM fallback.")
        results = fallback_llm_search(driver.page_source, site='sainsburys')
        driver.quit()
        return results
 
    results = []
    try:
        products = driver.find_elements(By.CSS_SELECTOR, "article[data-testid^='product-tile-']")
 
        for p in products:
            try:
                name_el = p.find_element(By.CSS_SELECTOR, "h2[data-testid='product-tile-description'] a")
                name = name_el.text.strip()
                href = name_el.get_attribute("href") or ""
            except:
                name = "N/A"
                href = ""
 
            try:
                price = p.find_element(
                    By.CSS_SELECTOR, "span[data-testid='pt-retail-price']"
                ).text.strip()
            except:
                price = "N/A"
 
            results.append([name, price, href])
 
    except:
        print("[Sainsbury's] Extraction failed — invoking LLM fallback.")
        print(driver.page_source[:3000])
        results = fallback_llm_search(driver.page_source, site='sainsburys')
 
    driver.quit()
    return results

def get_homebargains_results(search_query):
    print(f"\n{'='*60}")
    print(f"[Home Bargains] Starting search for: {search_query!r}")
    print(f"{'='*60}")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    search_url = f"https://home.bargains/search?q={quote(search_query)}"
    print(f"[Home Bargains] Navigating to: {search_url}")
    driver.get(search_url)
    print(f"[Home Bargains] Page loaded. Title: {driver.title!r}  |  HTML size: {len(driver.page_source)} chars")

    if FORCE_HEURISTIC_FALLBACK:
        print("[Home Bargains] FORCE_HEURISTIC_FALLBACK enabled — skipping CSS extraction.")
        results = fallback_llm_search(driver.page_source, site='homebargains')
        driver.quit()
        return results

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.ais-Hits-item")))
    except:
        print("[Home Bargains] Results list not found — invoking LLM fallback.")
        results = fallback_llm_search(driver.page_source, site='homebargains')
        driver.quit()
        return results

    items = []
    try:
        product_cards = driver.find_elements(By.CSS_SELECTOR, "li")

        for card in product_cards:
            try:
                name_el = card.find_element(By.CSS_SELECTOR, ".item-name a")
                name = name_el.text.strip()
            except:
                try:
                    name = card.find_element(By.CSS_SELECTOR, ".title").text.strip()
                except:
                    name = None

            try:
                raw_price = card.find_element(By.CSS_SELECTOR, ".item-price").text.strip()
            except:
                try:
                    raw_price = card.find_element(By.CSS_SELECTOR, ".price").text.strip()
                except:
                    raw_price = None

            # Handle double prices like "£3.99, £2.49" — take the last (sale) price
            if raw_price:
                prices = [p.strip() for p in raw_price.split(",") if p.strip()]
                price = prices[-1] if prices else raw_price
            else:
                price = None

            try:
                raw_href = card.find_element(By.CSS_SELECTOR, "a").get_attribute("href") or ""
                href = ("https://home.bargains" + raw_href) if raw_href.startswith("/") else raw_href
            except:
                href = ""

            if name and price:
                items.append([name, price, href])

    except:
        print("[Home Bargains] Extraction failed — invoking LLM fallback.")
        items = fallback_llm_search(driver.page_source, site='homebargains')

    driver.quit()
    return items

def get_morrisons_results(search_query):
    print(f"\n{'='*60}")
    print(f"[Morrisons] Starting search for: {search_query!r}")
    print(f"{'='*60}")

    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    search_url = f"https://groceries.morrisons.com/search?q={quote(search_query)}"
    print(f"[Morrisons] Navigating to: {search_url}")
    driver.get(search_url)
    print(f"[Morrisons] Page loaded. Title: {driver.title!r}  |  HTML size: {len(driver.page_source)} chars")

    if FORCE_HEURISTIC_FALLBACK:
        print("[Morrisons] FORCE_HEURISTIC_FALLBACK enabled — skipping CSS extraction.")
        results = fallback_llm_search(driver.page_source, site='morrisons')
        driver.quit()
        return results

    try:
        wait.until(EC.presence_of_element_located((By.ID, "product-page")))
    except:
        print("[Morrisons] Product page not found — invoking LLM fallback.")
        results = fallback_llm_search(driver.page_source, site='morrisons')
        driver.quit()
        return results

    items = []
    time.sleep(1)

    try:
        product_cards = driver.find_elements(By.CSS_SELECTOR, "div[data-retailer-anchor^='fop']")

        # If no fop cards found, try Angular .item-name/.item-price structure
        if not product_cards:
            product_cards = driver.find_elements(By.CSS_SELECTOR, "li")

        for card in product_cards:
            try:
                name = card.find_element(By.CSS_SELECTOR, "h3[data-test='fop-title']").text.strip()
            except:
                try:
                    name = card.find_element(By.CSS_SELECTOR, ".item-name a").text.strip()
                except:
                    name = None

            try:
                price = card.find_element(By.CSS_SELECTOR, "span[data-test='fop-price']").text.strip()
            except:
                try:
                    price = card.find_element(By.CSS_SELECTOR, ".item-price").text.strip()
                except:
                    price = None

            try:
                raw_href = card.find_element(By.CSS_SELECTOR, "a[href]").get_attribute("href") or ""
                href = ("https://groceries.morrisons.com" + raw_href) if raw_href.startswith("/") else raw_href
            except:
                href = ""

            if name and price:
                items.append([name, price, href])

    except:
        print("[Morrisons] Extraction failed — invoking LLM fallback.")
        items = fallback_llm_search(driver.page_source, site='morrisons')

    driver.quit()
    return items

def clean_html(html: str) -> str:

    import time
    t0 = time.time()
    print(f"[clean_html] Raw HTML size: {len(html):,} chars — parsing...")

    soup = BeautifulSoup(html, "html.parser")   # faster than lxml for huge pages
    print(f"[clean_html] Parsed in {time.time()-t0:.1f}s — stripping noise tags...")

    # Remove noise tags
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()
    print(f"[clean_html] Noise tags removed in {time.time()-t0:.1f}s — stripping attrs...")

    # Strip attributes in one pass
    for tag in soup.find_all(True):
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in _KEEP_ATTRS}
    print(f"[clean_html] Attrs stripped in {time.time()-t0:.1f}s — serialising...")

    # Serialise and collapse whitespace
    cleaned = str(soup)
    cleaned = _re.sub(r"\n\s*\n+", "\n", cleaned)
    cleaned = _re.sub(r"[ \t]{2,}", " ", cleaned)

    print(f"[clean_html] Done in {time.time()-t0:.1f}s — "
          f"size: {len(cleaned):,} chars ({100*len(cleaned)/max(len(html),1):.1f}% of original)")
    return cleaned

def html_to_product_dicts(soup: "BeautifulSoup", site: str = "unknown") -> list[dict]:

    import time
    t0 = time.time()
    print(f"[html_to_product_dicts] Site={site!r} — trying known selectors...")

    results = []

    if site == "sainsburys":
        BASE = "https://www.sainsburys.co.uk"

        cards = soup.select("article[data-testid]")
        product_cards = [c for c in cards if c.get("data-testid","").startswith("product-tile-")]
        print(f"[html_to_product_dicts] Sainsbury's: {len(cards)} article[data-testid] tags, "
              f"{len(product_cards)} product-tile cards")

        # Debug: show a sample of data-testid values found so we can see what's there
        all_testids = [t.get("data-testid","") for t in soup.find_all(attrs={"data-testid": True})]
        tile_ids = [x for x in all_testids if "product" in x.lower() or "tile" in x.lower()]
        print(f"[html_to_product_dicts] Sample data-testid values with 'product'/'tile': {tile_ids[:10]}")

        for card in product_cards:
            name_el = card.select_one('[data-testid="product-tile-description"] a')
            price_el = (
                card.select_one('[data-testid="contextual-price-text"]')
                or card.select_one('[data-testid="pt-retail-price"]')
                or card.select_one(".pt__cost--price")
            )
            name  = name_el.get_text(strip=True) if name_el else ""
            price = price_el.get_text(strip=True) if price_el else ""
            href  = name_el.get("href", "") if name_el else ""
            if href and not href.startswith("http"):
                href = BASE + href
            if name:
                results.append({"name": name, "price": price, "href": href})

    elif site == "homebargains":
        BASE = "https://home.bargains"
        cards = soup.select("li.ais-Hits-item")
        print(f"[html_to_product_dicts] Home Bargains: {len(cards)} li.ais-Hits-item cards")
        # Also check for Angular item-name structure
        alt_cards = soup.select("li")
        item_name_cards = [c for c in alt_cards if c.select_one(".item-name")]
        print(f"[html_to_product_dicts] Home Bargains: {len(item_name_cards)} li with .item-name")

        # Try ais-Hits-item first, then .item-name structure
        search_cards = cards if cards else item_name_cards
        for card in search_cards:
            name_el  = (card.select_one(".item-name a")
                        or card.select_one(".title")
                        or card.select_one("a[href]"))
            price_el = card.select_one(".item-price") or card.select_one(".price")
            a_el     = card.select_one("a[href]")
            if not (name_el and price_el):
                continue
            name = name_el.get_text(strip=True)
            raw_price = price_el.get_text(strip=True)
            prices = [p.strip() for p in raw_price.split(",") if p.strip()]
            price = prices[-1] if prices else raw_price
            raw_href = a_el.get("href", "") if a_el else ""
            href = (BASE + raw_href) if raw_href.startswith("/") else raw_href
            if name and price:
                results.append({"name": name, "price": price, "href": href})

    elif site == "morrisons":
        BASE = "https://groceries.morrisons.com"
        fop_cards = soup.select("div[data-retailer-anchor]")
        product_fops = [c for c in fop_cards if c.get("data-retailer-anchor","").startswith("fop")]
        print(f"[html_to_product_dicts] Morrisons: {len(fop_cards)} div[data-retailer-anchor], "
              f"{len(product_fops)} fop cards")

        # Debug: show sample retailer-anchor values
        anchors = [c.get("data-retailer-anchor","") for c in fop_cards[:10]]
        print(f"[html_to_product_dicts] Sample data-retailer-anchor values: {anchors}")

        for card in product_fops:
            name_el  = card.select_one("h3[data-test='fop-title']")
            price_el = card.select_one("span[data-test='fop-price']")
            a_el     = card.select_one("a[href]")
            name  = name_el.get_text(strip=True) if name_el else ""
            price = price_el.get_text(strip=True) if price_el else ""
            raw_href = a_el.get("href", "") if a_el else ""
            href = (BASE + raw_href) if raw_href.startswith("/") else raw_href
            if name and price:
                results.append({"name": name, "price": price, "href": href})

        if not results:
            # Angular .item-name/.item-price fallback
            item_cards = [li for li in soup.select("li") if li.select_one(".item-name")]
            print(f"[html_to_product_dicts] Morrisons Angular fallback: {len(item_cards)} .item-name cards")
            for card in item_cards:
                name_el  = card.select_one(".item-name a")
                price_el = card.select_one(".item-price")
                a_el     = card.select_one("a[href]")
                if not (name_el and price_el):
                    continue
                name  = name_el.get_text(strip=True)
                price = price_el.get_text(strip=True)
                raw_href = a_el.get("href", "") if a_el else ""
                href = (BASE + raw_href) if raw_href.startswith("/") else raw_href
                if name and price:
                    results.append({"name": name, "price": price, "href": href})

    if results:
        print(f"[html_to_product_dicts] Known selectors found {len(results)} products in {time.time()-t0:.1f}s")
        return results

    print(f"[html_to_product_dicts] No results from known selectors — trying generic scan...")

    # Non-product patterns to skip
    _NON_PRODUCT_TEXT = _re.compile(
        r"^(skip to|choose now|shop now|shop the|see all|view all|sign in|log in|"
        r"home delivery|my account|basket|checkout|back to top|meal deal|"
        r"terms|privacy|cookie|newsletter|subscribe|follow us|save |was )",
        _re.IGNORECASE,
    )
    _NON_PRODUCT_HREF = _re.compile(
        r"(^#|#main|#footer|#search|/offers?/?$|/features/|utm_|"
        r"/account|/basket|/checkout|/sign-?in|/help)",
        _re.IGNORECASE,
    )

    seen: dict[tuple, dict] = {}
    for a in soup.find_all("a", href=True):
        href = a.get("href", "") or ""
        if _NON_PRODUCT_HREF.search(href):
            continue
        text = a.get_text(" ", strip=True)
        if not text or len(text) < 5 or len(text) > 120:
            continue
        if _NON_PRODUCT_TEXT.match(text):
            continue
        parent = a.parent
        search_text = parent.get_text(" ", strip=True)[:300] if parent else text
        price_match = _PRICE_RE.search(search_text)
        if not price_match:
            continue
        price_str = price_match.group(0).strip()
        name_str = text.replace(price_str, "").strip()[:120] or text[:120]
        if len(name_str) < 5:
            continue
        key = (name_str[:60], price_str)
        if key not in seen:
            seen[key] = {"name": name_str, "price": price_str, "href": href}

    results = list(seen.values())
    print(f"[html_to_product_dicts] Generic scan found {len(results)} candidates in {time.time()-t0:.1f}s")
    return results

def toon_encode(data: list[dict], delimiter: str = ",") -> str:
    """
    Encode a list of uniform dicts as a TOON tabular array.

    Example output for 2 products:
        [2,]{name,price,href}:
          Whole Milk 2L,£1.20,https://...
          Skimmed Milk 1L,£0.95,https://...

    Falls back to compact JSON if the list is empty or non-uniform.
    """
    if not data or not isinstance(data[0], dict):
        return json.dumps(data, ensure_ascii=False)

    keys = list(data[0].keys())
    # Check all rows share the same keys (uniform = tabular encoding)
    if not all(set(row.keys()) == set(keys) for row in data):
        return json.dumps(data, ensure_ascii=False)

    def _cell(v: object) -> str:
        s = "" if v is None else str(v)
        # Quote if value contains delimiter, newline, or leading/trailing space
        if delimiter in s or "\n" in s or s != s.strip():
            s = f'"{s}"'
        return s

    header = f"[{len(data)},]{{{delimiter.join(keys)}}}:"
    rows = [f"  {delimiter.join(_cell(row.get(k, '')) for k in keys)}" for row in data]
    return "\n".join([header] + rows)

def encode_for_llm(raw_html: str, site: str = "unknown") -> tuple[str, str, list[dict]]:
    """
    Pipeline:
      1. Parse once, strip noise tags (keeps all attrs intact)
      2. Unless FORCE_LLM_HEURISTIC_BYPASS, run heuristic with full attrs
      3. If heuristic finds products → return directly (no LLM)
      4. Otherwise strip attrs, send cleaned HTML to LLM
    """
    import time
    t0 = time.time()

    print(f"[encode_for_llm] Starting pipeline — site={site!r}, input={len(raw_html):,} chars...")
    soup = BeautifulSoup(raw_html, "html.parser")

    # Strip noise tags only — keep ALL attributes so selectors work
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()
    print(f"[encode_for_llm] Noise tags removed in {time.time()-t0:.1f}s")

    # Run heuristic while attrs are intact (unless bypassed for LLM testing)
    if not FORCE_LLM_HEURISTIC_BYPASS:
        products = html_to_product_dicts(soup, site=site)
        if products:
            toon = toon_encode(products)
            print(f"[encode_for_llm] Heuristic found {len(products)} products — "
                  f"returning directly ({len(toon):,} chars TOON, {time.time()-t0:.1f}s total)")
            return toon, "toon", products
    else:
        print(f"[encode_for_llm] FORCE_LLM_HEURISTIC_BYPASS — skipping heuristic, going straight to LLM")

    # Strip attrs now for the LLM payload
    for tag in soup.find_all(True):
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in _KEEP_ATTRS}

    cleaned = str(soup)
    cleaned = _re.sub(r"\n\s*\n+", "\n", cleaned)
    cleaned = _re.sub(r"[ \t]{2,}", " ", cleaned)
    print(f"[encode_for_llm] Sending cleaned HTML to LLM ({len(cleaned):,} chars, {time.time()-t0:.1f}s)")
    return cleaned, "html", []

def fallback_llm_search(raw_html: str, model: str = DEFAULT_MODEL, site: str = "unknown") -> list[list[str]]:
    """
    Full pipeline: raw HTML → heuristic extraction → (LLM only if heuristic fails)

    If html_to_product_dicts finds products via known selectors, returns them
    directly without any LLM call. LLM is only invoked as a last resort when
    the heuristic finds nothing (e.g. site has been redesigned).
    """
    payload, fmt, heuristic_products = encode_for_llm(raw_html, site=site)
    
    # Short-circuit: heuristic succeeded — no LLM needed
    if heuristic_products:
        print(f"[fallback] Heuristic returned {len(heuristic_products)} products — skipping LLM.")
        results = [[p["name"], p["price"], p["href"]] for p in heuristic_products]
        print("[fallback] Final results:")
        for i, r in enumerate(results):
            print(f"  [{i+1}] name={r[0]!r}  price={r[1]!r}  href={r[2]!r}")
        return results

    # Heuristic found nothing — send cleaned HTML to LLM
    print(f"[fallback] Heuristic empty — invoking LLM on {len(payload):,} char payload...")

    if fmt == "toon":
        format_description = (
            "TOON tabular format (a compact encoding of uniform objects).\n"
            "The header line [N,]{col1,col2,...}: lists the columns.\n"
            "Each subsequent line is one product's values, comma-separated."
        )
    else:
        format_description = "cleaned HTML"

    prompt = f"""You are a data extractor. Below is a retail search results page encoded as {format_description}

Extract every product and return ONLY a JSON array.
Each element must be an object with exactly these three keys:
  "name"  – product title as plain text
  "price" – price as plain text (e.g. "£1.50")
  "href"  – URL or path to the product page (empty string if not found)

Rules:
- Return ONLY the JSON array. No markdown fences, no explanation.
- Use empty string for any field you cannot find.
- Do not invent data.

Examples:

HTML:
<a href="/product/1">Cherry Tomatoes</a>
<span>£2.50</span>

Output:
[
 {"name":"Cherry Tomatoes","price":"£2.50","href":"/product/1"}
]

HTML:
<a tabindex="0" class="_text_cn5lb_1 _text--m_cn5lb_23 _link-standalone_v2p9r_8" data-synthetics="bop-link" data-test="fop-product-link" aria-hidden="false" href="/products/morrisons-salad-tomatoes/108389100" data-discover="true"><h3 class="_text_cn5lb_1 _text--m_cn5lb_23" data-test="fop-title">Morrisons Salad Tomatoes</h3></a>
<span class="salt-vc">Price</span>
<span class="_display_xy0eg_1 sc-1fkdssq-1 eDGgtR" data-test="fop-price">£0.99</span>

Output:
[
 {"name":"Morrisons Salad Tomatoes","price":"£0.99","href":"/products/morrisons-salad-tomatoes/108389100"}
]

DATA:
{payload}
"""
 
    def call_model(m: str) -> list[list[str]]:
        import traceback
        print(f"\n[LLM] Sending prompt to {m}...")
        print(f"[LLM] Format: {fmt.upper()}  |  Payload: {len(payload):,} chars  |  Prompt: {len(prompt):,} chars")
        print("-" * 60)

        # Single non-streaming call — simpler and avoids chunk assembly bugs
        response = ollama.chat(
            model=m,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        raw = response["message"]["content"].strip()

        print(f"[LLM] Raw response from {m} ({len(raw):,} chars):")
        print("=" * 60)
        print(raw[:2000])  # cap console spam but always show start
        if len(raw) > 2000:
            print(f"... [{len(raw)-2000:,} more chars]")
        print("=" * 60)

        if not raw:
            raise ValueError("LLM returned an empty response")

        # Strip accidental markdown fences — handle ```json ... ``` or ``` ... ```
        clean = raw
        if clean.startswith("```"):
            print("[LLM] Stripping markdown fences...")
            clean = _re.sub(r"^```[a-zA-Z]*\n?", "", clean)
            clean = _re.sub(r"\n?```$", "", clean).strip()
            print(f"[LLM] After fence strip: {clean[:200]}")

        # Extract the JSON array even if the model prepended/appended prose
        bracket_start = clean.find("[")
        bracket_end   = clean.rfind("]")
        if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
            if bracket_start > 0 or bracket_end < len(clean) - 1:
                print(f"[LLM] Extracting JSON array from pos {bracket_start}:{bracket_end+1}")
            clean = clean[bracket_start : bracket_end + 1]

        print("[LLM] Parsing JSON...")
        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError as e:
            print(f"[LLM] JSON parse error: {e}")
            print(f"[LLM] Offending text around error:\n{clean[max(0,e.pos-100):e.pos+100]}")
            raise

        print(f"[LLM] JSON parsed OK — {len(parsed)} items found.")
        results = [
            [item.get("name", ""), item.get("price", ""), item.get("href", "")]
            for item in parsed
            if isinstance(item, dict)
        ]
        print("[LLM] Extracted results:")
        for i, r in enumerate(results):
            print(f"  [{i+1}] name={r[0]!r}  price={r[1]!r}  href={r[2]!r}")
        return results

    # Try primary model, then fallback model
    for attempt_model in [model, FALLBACK_MODEL]:
        try:
            print(f"\n[LLM fallback] Trying model: {attempt_model}")
            results = call_model(attempt_model)
            if results:
                print(f"[LLM fallback] ✓ Successfully extracted {len(results)} products via {attempt_model}.")
                return results
            else:
                print(f"[LLM fallback] {attempt_model} returned no results — trying next model.")
        except Exception as e:
            import traceback
            print(f"[LLM fallback] ✗ {attempt_model} failed: {e}")
            traceback.print_exc()

    print("[LLM fallback] All models failed. Returning empty list.")
    return []

def search_all(query, on_result=None):
    """
    Run all three crawlers concurrently.

    on_result: optional callback(store_name, results) fired as each store
               finishes — use this so your display page can render results
               immediately instead of waiting for all three to complete.
    """
    crawlers = {
        "sainsburys":   lambda: get_sainsburys_results(query),
        "homebargains": lambda: get_homebargains_results(query),
        "morrisons":    lambda: get_morrisons_results(query),
    }
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn): name for name, fn in crawlers.items()}
        for future in as_completed(futures):   # fires as each store finishes, not all at once
            name = futures[future]
            try:
                store_results = future.result()
            except Exception as e:
                import traceback
                print(f"[search_all] {name} failed: {e}")
                traceback.print_exc()
                store_results = []
            results[name] = store_results
            print(f"[search_all] ✓ {name} done — {len(store_results)} products")
            if on_result is not None:
                on_result(name, store_results)  # display page gets this store NOW
    return results