import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="SKU Price Checker", layout="wide")
st.title("Hybrid SKU Price Checker")

# Vendor search URLs
VENDORS = {
    "JB Hi-Fi": "https://www.jbhifi.com.au/search?query=",
    "Officeworks": "https://www.officeworks.com.au/shop/officeworks/search?q=",
    "The Good Guys": "https://www.thegoodguys.com.au/search?q=",
    "Harvey Norman": "https://www.harveynorman.com.au/catalogsearch/result/?q=",
    "HP Store": "https://www.hp.com/au-en/shop/search?q=",
    "Bing Lee": "https://www.binglee.com.au/search?q=",  # link only
    "Google Shopping": "https://www.google.com/search?tbm=shop&q=",  # link only
}

# Optional direct SKU mapping
SKU_DIRECT = {
    "714P3A": {
        "JB Hi-Fi": "https://www.jbhifi.com.au/products/hp-envy-6531e-all-in-one-printer-instant-ink-enabled",
        "The Good Guys": "https://www.thegoodguys.com.au/hp-envy-6531e-aio-printer-instant-ink-enabled-714p3a",
        "HP Store": "https://www.hp.com/au-en/shop/hp-envy-6531e-all-in-one-printer-714p3a.html"
    }
}

# Regex-based price extractor
def extract_price_from_text(text: str):
    match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
    return match.group(0) if match else None

# Safe scraper
def fetch_price_safe(url: str, vendor: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        price = extract_price_from_text(text)
        return {
            "Vendor": vendor,
            "Product": "Search results",
            "Price": price if price else "Click link",
            "Link": f"[Open {vendor}]({url})"
        }
    except Exception as e:
        return {
            "Vendor": vendor,
            "Product": "Error",
            "Price": str(e),
            "Link": f"[Open {vendor}]({url})"
        }

# Input
sku = st.text_input("Enter SKU:")

if st.button("Search"):
    if not sku.strip():
        st.warning("Please enter a SKU before searching.")
    else:
        results = []
        for vendor_name, base_url in VENDORS.items():
            # Use direct mapping if available
            if sku in SKU_DIRECT and vendor_name in SKU_DIRECT[sku]:
                search_url = SKU_DIRECT[sku][vendor_name]
            else:
                search_url = base_url + sku

            # Blocked vendors → link only
            if vendor_name in ["Bing Lee", "Google Shopping"]:
                results.append({
                    "Vendor": vendor_name,
                    "Product": "Search results",
                    "Price": "Click link",
                    "Link": f"[Open {vendor_name}]({search_url})"
                })
            else:
                results.append(fetch_price_safe(search_url, vendor_name))

        df = pd.DataFrame(results)

        st.markdown("### Results")
        for _, row in df.iterrows():
            st.markdown(
                f"- **{row['Vendor']}** | {row['Product']} | **{row['Price']}** | {row['Link']}",
                unsafe_allow_html=True
            )

        # Highlight lowest price if numeric
        def parse_price(p):
            try:
                return float(p.replace("$", "").replace(",", ""))
            except:
                return None

        df["NumericPrice"] = df["Price"].apply(parse_price)
        min_price = df["NumericPrice"].min()
        if min_price is not None:
            best_vendor = df.loc[df["NumericPrice"] == min_price, "Vendor"].values[0]
            st.success(f"Lowest price: ${min_price:.2f} at {best_vendor}")



