import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import subprocess
import sys

# -----------------------------
# Install Playwright Chromium
# -----------------------------
subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])

# -----------------------------
# Streamlit page setup
# -----------------------------
st.set_page_config(page_title="SKU Price Checker", layout="wide")
st.title("Australian Multi-Vendor SKU Price Checker")

# -----------------------------
# Input SKU
# -----------------------------
sku_input = st.text_input("Enter SKU / Model:")

# -----------------------------
# Session state for history
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = []

if "results" not in st.session_state:
    st.session_state.results = []

# -----------------------------
# Vendors configuration
# CSS selectors may need updating if site changes
# -----------------------------
vendors = {
    "JB Hi-Fi": {"url": "https://www.jbhifi.com.au/search/?q={}", "selector": "span.product-price__value"},
    "Officeworks": {"url": "https://www.officeworks.com.au/shop/search?searchTerm={}", "selector": "span.oo-price"},
    "The Good Guys": {"url": "https://www.thegoodguys.com.au/search?q={}", "selector": "span.product-price"},
    "Harvey Norman": {"url": "https://www.harveynorman.com.au/catalogsearch/result/?q={}", "selector": "span.price"},
    "Bing Lee": {"url": "https://www.binglee.com.au/search?q={}", "selector": "span.price"},
    "Amazon AU": {"url": "https://www.amazon.com.au/s?k={}", "selector": "span.a-price-whole"},
}

# -----------------------------
# Fetch prices function
# -----------------------------
def fetch_prices(sku):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = browser.new_page()
        for name, info in vendors.items():
            search_url = info["url"].format(sku)
            try:
                page.goto(search_url, timeout=60000)  # 60s timeout
                price_el = page.query_selector(info["selector"])
                price = price_el.inner_text().strip() if price_el else "Not Found"
            except:
                price = "Not Found"
            results.append({
                "Retailer": name,
                "Price": price,
                "Search Link": f"[Click Here]()
