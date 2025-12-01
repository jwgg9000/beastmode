import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# Page setup
st.set_page_config(page_title="SKU Price Checker", layout="wide")
st.title("Hybrid SKU Price Checker")

# Vendor search URLs
VENDORS = {
    "JB Hi-Fi": "https://www.jbhifi.com.au/search?query=",
    "Officeworks": "https://www.officeworks.com.au/shop/officeworks/search?q=",
    "The Good Guys": "https://www.thegoodguys.com.au/search?q=",
    "Harvey Norman": "https://www.harveynorman.com.au/catalogsearch/result/?q=",
    "Bing Lee": "https://www.binglee.com.au/catalogsearch/result/?q=",
}

# Extract price from text
def extract_price_from_text(text):
    match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
    return match.group(0) if match else None

# Fetch price safely with timeout
def fetch_price_safe(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=2)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        price = extract_price_from_text(text)
        return price if price else "Click link"
    except:
        return "Click link"

# Input
sku = st.text_input("Enter SKU:")

# Search button
if st.button("Search"):
    if not sku.strip():
        st.warning("Please enter a SKU before searching.")
    else:
        results = []
        for vendor_name, base_url in VENDORS.items():
            search_url = base_url + sku
            price = fetch_price_safe(search_url)
            results.append({
                "Vendor": vendor_name,
                "Price": price,
                "Link": f"[Open {vendor_name}]({search_url})"
            })

        df = pd.DataFrame(results)
        st.markdown("### Results")
        st.dataframe(df, use_container_width=True)
