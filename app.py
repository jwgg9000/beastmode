import os
import time
import json
import re
import random
import pandas as pd
import streamlit as st
# 💡 New libraries for static scraping
import requests
from bs4 import BeautifulSoup 

# --- Configuration ---
st.set_page_config(page_title="SKU Price Checker", layout="wide")
st.title("📄 Static HTML SKU Price Checker")

VENDORS = {
    "JB Hi-Fi": "https://www.jbhifi.com.au/search?q=",
    "Officeworks": "https://www.officeworks.com.au/shop/officeworks/search?q=",
    "The Good Guys": "https://www.thegoodguys.com.au/search?q=",
    "Harvey Norman": "https://www.harveynorman.com.au/catalogsearch/result/?q=",
    "Bing Lee": "https://www.binglee.com.au/search?q=",  # link only
    "Google Shopping": "https://www.google.com/search?tbm=shop&q=",  # link only
    "PriceSpy": "https://www.pricespy.com.au/search?search=",  # link only
}

# Common headers to help avoid basic blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
}

# --- Price Extraction Functions (Minimal Change) ---

# Basic price regex (Remains the same)
def extract_price_from_text(text: str):
    match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
    return match.group(0) if match else None

# Try to parse JSON-LD price objects (Adapted for BeautifulSoup)
def parse_json_ld_for_price(soup):
    scripts = soup.find_all('script', type='application/ld+json')
    for s in scripts:
        try:
            # Use .string instead of inner_text() for BeautifulSoup
            data = json.loads(s.string) 
            items = data if isinstance(data, list) else [data]
            for it in items:
                offers = it.get("offers") or it.get("priceSpecification")
                if isinstance(offers, dict):
                    price = offers.get("price") or it.get("price") # Check top level price too
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

# List of common selectors (Remains the same)
COMMON_PRICE_SELECTORS = [
    '[itemprop="price"]', '.price', '.product-price', '.price--now',
    '.price__value', '.price-sales', '.price-amount', '.priceValue',
    '[data-testid="price"]', '.product__price', '.sale-price', '.productPrice',
]

# --- CORE FETCH FUNCTION (NEW) ---

def fetch_price_static(url: str, vendor: str, proxy: str = None):
    """Use requests to fetch static HTML and BeautifulSoup to extract a price."""
    try:
        # Configure proxy for requests if provided
        proxies = {"http": proxy, "https": proxy} if proxy else None
        
        # 💡 Use a session for better connection handling
        with requests.Session() as session:
            session.headers.update(HEADERS)
            
            # Polite random delay before navigation
            time.sleep(random.uniform(0.5, 1.2))
            
            # Make the GET request
            response = session.get(url, proxies=proxies, timeout=15)
            response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
            
            # Parse the content
            soup = BeautifulSoup(response.content, 'html.parser')

            # 1) Try JSON-LD structured data
            price = parse_json_ld_for_price(soup)
            if price:
                return {"Vendor": vendor, "Product": "Static HTML (JSON-LD)", "Price": price, "Link": f"[Open {vendor}]({url})"}

            # 2) Try common selectors
            for sel in COMMON_PRICE_SELECTORS:
                # Using CSS selector syntax
                el = soup.select_one(sel) 
                if el:
                    # Get the text, including from children
                    txt = el.get_text(strip=True) 
                    ptxt = extract_price_from_text(txt)
                    if ptxt:
                        return {"Vendor": vendor, "Product": f"Static HTML ({sel})", "Price": ptxt, "Link": f"[Open {vendor}]({url})"}
            
            # 3) Fallback: search entire HTML content
            content = response.text
            ptxt = extract_price_from_text(content)
            
            return {"Vendor": vendor, "Product": "Static HTML (Fallback)", "Price": ptxt if ptxt else "Click link", "Link": f"[Open {vendor}]({url})"}

    except requests.exceptions.HTTPError as e:
        # Handle 4xx or 5xx errors
        return {"Vendor": vendor, "Product": "Error (HTTP)", "Price": f"Status {e.response.status_code}", "Link": f"[Open {vendor}]({url})"}
    except requests.exceptions.RequestException as e:
        # Handle connection, timeout, or general request errors
        return {"Vendor": vendor, "Product": "Error (Connection)", "Price": str(e), "Link": f"[Open {vendor}]({url})"}
    except Exception as e:
        # Handle other unexpected errors
        return {"Vendor": vendor, "Product": "Error (General)", "Price": str(e), "Link": f"[Open {vendor}]({url})"}

# --- Utility Function ---

def parse_price(p):
    # ... (Implementation remains the same)
    try:
        if not p or p in ("Click link", None) or not isinstance(p, str):
            return None
        # Use regex to strip $ and commas, finding the number
        num = re.search(r"\d[\d,]*(\.\d{1,2})?", str(p))
        if not num:
            return None
        return float(num.group(0).replace(",", ""))
    except Exception:
        return None

# --- Streamlit UI Logic (Adapted from previous refactor) ---

# Initialize session state for results if not present
if "results" not in st.session_state:
    st.session_state["results"] = []

sku = st.text_input("Enter SKU and press Enter:")

st.sidebar.markdown("### Settings")
# Removed "Run browser visible (headful)" as it's no longer relevant
proxy_input = st.sidebar.text_input("Optional proxy (http://user:pass@host:port)", value=os.environ.get("PLAYWRIGHT_PROXY", ""))
# Removed os.environ.get("PLAYWRIGHT_PROXY", "") as it's confusing, but kept the value for now

# 💡 Use a button to explicitly trigger the long-running process
if st.button("Check Prices"):
    if not sku or not sku.strip():
        st.warning("Please enter an SKU to search.")
    else:
        results = []
        with st.spinner(f"Searching for SKU **{sku}** across {len(VENDORS)} vendors..."):
            for vendor_name, base_url in VENDORS.items():
                search_url = base_url + sku

                # Link-only vendors
                if vendor_name in ["Bing Lee", "Google Shopping", "PriceSpy"]:
                    results.append({
                        "Vendor": vendor_name,
                        "Product": "Search results (Link Only)",
                        "Price": "Click link",
                        "Link": f"[Open {vendor_name}]({search_url})"
                    })
                    continue

                # Fetch with static requests
                res = fetch_price_static(
                    search_url, 
                    vendor_name, 
                    proxy=proxy_input or None, 
                )
                results.append(res)
                # small delay between vendor requests
                time.sleep(random.uniform(0.8, 1.6))
        
        # Store results in session state
        st.session_state["results"] = results
        st.success("Search complete! Results are below.")

# --- Display Results from Session State ---

if st.session_state["results"]:
    df = pd.DataFrame(st.session_state["results"])
    df["NumericPrice"] = df["Price"].apply(parse_price)

    st.markdown("---")

    st.markdown("### 📊 Results Table")
    
    st.dataframe(
        df[["Vendor", "Product", "Price", "Link", "NumericPrice"]], 
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="Open 🔗")
        },
        height=300
    )

    # Highlight lowest price
    if df["NumericPrice"].notnull().any():
        min_price = df["NumericPrice"].min()
        best_rows = df[df["NumericPrice"] == min_price]
        
        best_rows_list = [
            f"**{row['Vendor']}**" for _, row in best_rows.iterrows()
        ]
        vendors_str = " and ".join(best_rows_list)

        st.success(f"🎉 **Lowest price found:** ${min_price:.2f} at {vendors_str}")
    else:
        st.info("No numeric prices detected. This could be due to anti-bot measures or prices being loaded by JavaScript.")

    st.markdown("---")

    st.markdown("### 🔗 Quick Links (Raw Markdown Output)")
    for _, row in df.iterrows():
        st.markdown(f"- **{row['Vendor']}** | **{row['Price']}** | {row['Link']}", unsafe_allow_html=True)