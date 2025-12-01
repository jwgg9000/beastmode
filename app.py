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
    "Google Shopping": "https://www.google.com/search?tbm=shop&q=",
}

# Regex-based price extractor
def extract_price_from_text(text: str):
    match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
    return match.group(0) if match else None

# Special parser for Google Shopping
def fetch_google_price(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Find any text that looks like a price
        candidates = soup.find_all(text=re.compile(r"\$\s?\d[\d,]*(\.\d{1,2})?"))
        if candidates:
            return candidates[0].strip()

        return "Click link"
    except Exception as e:
        return f"Error: {e}"

# General fetcher
def fetch_price_safe(url: str, vendor: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        if vendor == "Google Shopping":
            return fetch_google_price(url)

        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        price = extract_price_from_text(text)
        return price if price else "Click link"
    except Exception as e:
        return f"Error: {e}"

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
            price = fetch_price_safe(search_url, vendor_name)
            results.append({
                "Vendor": vendor_name,
                "Price": price,
                "Link": f"[Open {vendor_name}]({search_url})"
            })

        df = pd.DataFrame(results)

        # Try to highlight lowest price
        def parse_price(p):
            try:
                return float(p.replace("$", "").replace(",", ""))
            except:
                return None

        df["NumericPrice"] = df["Price"].apply(parse_price)
        min_price = df["NumericPrice"].min()

        st.markdown("### Results")
        st.dataframe(df.drop(columns=["NumericPrice"]), use_container_width=True)

        if min_price is not None:
            best_vendor = df.loc[df["NumericPrice"] == min_price, "Vendor"].values[0]
            st.success(f"Lowest price: ${min_price:.2f} at {best_vendor}")


