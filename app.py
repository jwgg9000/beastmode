import os
import time
import json
import re
import random
import pandas as pd
import streamlit as st
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="SKU Price Checker", layout="wide")
st.title("Headless Browser SKU Price Checker")

# Vendors (HP Store removed)
VENDORS = {
    "JB Hi-Fi": "https://www.jbhifi.com.au/search?q=",
    "Officeworks": "https://www.officeworks.com.au/shop/officeworks/search?q=",
    "The Good Guys": "https://www.thegoodguys.com.au/search?q=",
    "Harvey Norman": "https://www.harveynorman.com.au/catalogsearch/result/?q=",
    "Bing Lee": "https://www.binglee.com.au/search?q=",  # link only
    "Google Shopping": "https://www.google.com/search?tbm=shop&q=",  # link only
    "PriceSpy": "https://www.pricespy.com.au/search?search=",  # link only
}

# Basic price regex
def extract_price_from_text(text: str):
    match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
    return match.group(0) if match else None

# Try to parse JSON-LD price objects
def parse_json_ld_for_price(page):
    scripts = page.query_selector_all('script[type="application/ld+json"]')
    for s in scripts:
        try:
            data = json.loads(s.inner_text())
            # data can be a list or dict
            items = data if isinstance(data, list) else [data]
            for it in items:
                # common schema.org patterns
                offers = it.get("offers") or it.get("priceSpecification")
                if isinstance(offers, dict):
                    price = offers.get("price") or offers.get("priceCurrency")
                    if price:
                        return f"${price}"
                if isinstance(offers, list):
                    for o in offers:
                        price = o.get("price")
                        if price:
                            return f"${price}"
        except Exception:
            continue
    return None

# Try a list of common selectors for price
COMMON_PRICE_SELECTORS = [
    '[itemprop="price"]',
    '.price',
    '.product-price',
    '.price--now',
    '.price__value',
    '.price-sales',
    '.price-amount',
    '.priceValue',
    '[data-testid="price"]',
    '.product__price',
    '.sale-price',
    '.productPrice',
]

def fetch_price_browser(url: str, vendor: str, proxy: str = None, headless: bool = True):
    """Use Playwright to render the page and extract a price."""
    try:
        with sync_playwright() as p:
            launch_args = {"headless": headless}
            browser = p.chromium.launch(**launch_args)

            # Optional proxy support via environment variable PLAYWRIGHT_PROXY (format: http://user:pass@host:port)
            context_args = {
                "locale": "en-AU",
                "viewport": {"width": 1280, "height": 800},
                "user_agent": os.environ.get(
                    "PLAYWRIGHT_USER_AGENT",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                ),
                "extra_http_headers": {"Accept-Language": "en-AU,en;q=0.9"},
            }
            if proxy:
                context_args["proxy"] = {"server": proxy}

            context = browser.new_context(**context_args)

            # Make pages look less like automation
            context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-AU','en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                """
            )

            page = context.new_page()
            # polite random delay before navigation
            time.sleep(random.uniform(0.5, 1.2))
            page.goto(url, timeout=60000)
            # Wait for network to settle and a short extra delay
            page.wait_for_load_state("networkidle", timeout=60000)
            time.sleep(random.uniform(0.3, 0.9))

            # 1) Try JSON-LD structured data
            price = parse_json_ld_for_price(page)
            if price:
                browser.close()
                return {"Vendor": vendor, "Product": "Rendered page", "Price": price, "Link": f"[Open {vendor}]({url})"}

            # 2) Try common selectors
            for sel in COMMON_PRICE_SELECTORS:
                try:
                    el = page.query_selector(sel)
                    if el:
                        txt = el.inner_text().strip()
                        ptxt = extract_price_from_text(txt)
                        if ptxt:
                            browser.close()
                            return {"Vendor": vendor, "Product": "Rendered page", "Price": ptxt, "Link": f"[Open {vendor}]({url})"}
                except Exception:
                    continue

            # 3) Fallback: search page HTML
            content = page.content()
            ptxt = extract_price_from_text(content)
            browser.close()
            return {"Vendor": vendor, "Product": "Rendered page", "Price": ptxt if ptxt else "Click link", "Link": f"[Open {vendor}]({url})"}

    except Exception as e:
        return {"Vendor": vendor, "Product": "Error", "Price": str(e), "Link": f"[Open {vendor}]({url})"}

# Streamlit UI
sku = st.text_input("Enter SKU and press Enter:")

st.sidebar.markdown("### Settings")
use_headful = st.sidebar.checkbox("Run browser visible (headful)", value=False)
proxy_input = st.sidebar.text_input("Optional proxy (http://user:pass@host:port)", value=os.environ.get("PLAYWRIGHT_PROXY", ""))

if sku and sku.strip():
    results = []
    for vendor_name, base_url in VENDORS.items():
        search_url = base_url + sku

        # Link-only vendors
        if vendor_name in ["Bing Lee", "Google Shopping", "PriceSpy"]:
            results.append({
                "Vendor": vendor_name,
                "Product": "Search results",
                "Price": "Click link",
                "Link": f"[Open {vendor_name}]({search_url})"
            })
            continue

        # Fetch with Playwright
        res = fetch_price_browser(search_url, vendor_name, proxy=proxy_input or None, headless=not use_headful)
        results.append(res)
        # small delay between vendor requests to reduce blocking
        time.sleep(random.uniform(0.8, 1.6))

    df = pd.DataFrame(results)

    # Parse numeric price for comparison
    def parse_price(p):
        try:
            if not p or p in ("Click link", None):
                return None
            # strip $ and commas
            num = re.search(r"\d[\d,]*(\.\d{1,2})?", str(p))
            if not num:
                return None
            return float(num.group(0).replace(",", ""))
        except Exception:
            return None

    df["NumericPrice"] = df["Price"].apply(parse_price)

    st.markdown("### Results table")
    # Show full table; links are markdown strings
    st.dataframe(df[["Vendor", "Product", "Price", "Link", "NumericPrice"]])

    # Highlight lowest price
    if df["NumericPrice"].notnull().any():
        min_price = df["NumericPrice"].min()
        best_rows = df[df["NumericPrice"] == min_price]
        best_vendor = best_rows.iloc[0]["Vendor"]
        st.success(f"Lowest price: ${min_price:.2f} at {best_vendor}")
    else:
        st.info("No numeric prices detected. Click vendor links to view pages.")

    # Also print a simple markdown list with clickable links
    st.markdown("### Quick links")
    for _, row in df.iterrows():
        st.markdown(f"- **{row['Vendor']}** | **{row['Price']}** | {row['Link']}", unsafe_allow_html=True)

