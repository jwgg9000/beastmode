import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import subprocess

# Ensure Playwright browsers are installed on Cloud
subprocess.run(["playwright", "install", "chromium"])

st.set_page_config(page_title="SKU Price Dashboard", layout="wide")
st.title("Multi-Vendor SKU Price Checker")

# Input SKU
sku_input = st.text_input("Enter SKU / Model:")

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []

if "results" not in st.session_state:
    st.session_state.results = []

# Vendor configuration with URL + CSS selector for first product price
vendors = {
    "JB Hi-Fi": {"url": "https://www.jbhifi.com.au/search/?q={}", "selector": "span.product-price__value"},
    "Officeworks": {"url": "https://www.officeworks.com.au/shop/search?searchTerm={}", "selector": "span.oo-price"},
    "The Good Guys": {"url": "https://www.thegoodguys.com.au/search?q={}", "selector": "span.product-price"},
    "Harvey Norman": {"url": "https://www.harveynorman.com.au/catalogsearch/result/?q={}", "selector": "span.price"},
    "Bing Lee": {"url": "https://www.binglee.com.au/search?q={}", "selector": "span.price"},
    "Amazon AU": {"url": "https://www.amazon.com.au/s?k={}", "selector": "span.a-price-whole"},
    "Kogan": {"url": "https://www.kogan.com/au/shop/?q={}", "selector": "span.price"},
    "Catch": {"url": "https://www.catch.com.au/search?query={}", "selector": "span.price"},
}

def fetch_prices(sku):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for name, info in vendors.items():
            search_url = info["url"].format(sku)
            try:
                page.goto(search_url, timeout=30000)
                price_el = page.query_selector(info["selector"])
                price = price_el.inner_text().strip() if price_el else "Not Found"
            except:
                price = "Not Found"
            results.append({
                "Retailer": name,
                "Price": price,
                "Search Link": f"[Click Here]({search_url})"
            })
        browser.close()
    return results

# Process SKU
if sku_input:
    st.info(f"Searching for SKU: {sku_input} across vendors...")
    prices = fetch_prices(sku_input)
    st.session_state.history.append(sku_input)
    st.session_state.results = prices

# Display results
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)

    # Highlight lowest price (ignores "Not Found")
    def highlight_lowest(row):
        try:
            # Convert price strings to floats, remove non-numeric chars
            numeric_prices = [float(''.join(c for c in str(p) if (c.isdigit() or c == "."))) 
                              if p != "Not Found" else float('inf') for p in row["Price"]]
            min_price = min(numeric_prices)
            return ["background-color: lightgreen" if 
                    (p != "Not Found" and float(''.join(c for c in str(p) if (c.isdigit() or c == "."))) == min_price) 
                    else "" for p in [row["Price"]]]
        except:
            return [""]*len(row)

    st.subheader("Price Comparison Table")
    st.table(df)

st.subheader("Recent SKUs")
for sku in reversed(st.session_state.history[-10:]):
    st.write(sku)
