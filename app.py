import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="SKU Price Checker", layout="wide")
st.title("Hybrid SKU Price Checker")

# Vendor search URLs (curated + Google Shopping)
VENDORS = {
    "JB Hi-Fi": "https://www.jbhifi.com.au/search?query=",
    "Officeworks": "https://www.officeworks.com.au/shop/officeworks/search?q=",
    "The Good Guys": "https://www.thegoodguys.com.au/search?q=",
    "Harvey Norman": "https://www.harveynorman.com.au/catalogsearch/result/?q=",
    "Bing Lee": "https://www.binglee.com.au/search?q=",
    "HP Store": "https://www.hp.com/au-en/shop/search?q=",
    "Google Shopping": "https://www.google.com/search?tbm=shop&q=",
}

# Regex-based price extractor
def extract_price_from_text(text: str):
    match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
    return match.group(0) if match else None

# Parse Google Shopping for multiple results
def fetch_google_results(url: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        results = []
        for item in soup.select("div.sh-dgr__content"):
            title = item.get_text(" ", strip=True)
            price = extract_price_from_text(title)
            if price:
                results.append({
                    "Vendor": "Google Shopping",
                    "Product": title,
                    "Price": price,
                    "Link": f"[Open Google Shopping]({url})"
                })
        return results if results else [{
            "Vendor": "Google Shopping",
            "Product": "No structured results",
            "Price": "Click link",
            "Link": f"[Open Google Shopping]({url})"
        }]
    except Exception as e:
        return [{
            "Vendor": "Google Shopping",
            "Product": "Error",
            "Price": str(e),
            "Link": f"[Open Google Shopping]({url})"
        }]

# Fallback fetcher for other vendors
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
            search_url = base_url + sku
            if vendor_name == "Google Shopping":
                results.extend(fetch_google_results(search_url))
            else:
                results.append(fetch_price_safe(search_url, vendor_name))

        df = pd.DataFrame(results)

        st.markdown("### Results")
        # Loop through rows so links are clickable
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

