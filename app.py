import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="SKU Price Checker", layout="wide")
st.title("Direct Vendor Price Checker")

sku = st.text_input("Enter SKU:")

# Vendor search URLs
VENDORS = {
    "JB Hi-Fi": "https://www.jbhifi.com.au/search?query=",
    "Officeworks": "https://www.officeworks.com.au/shop/officeworks/search?q=",
    "The Good Guys": "https://www.thegoodguys.com.au/search?q=",
    "Harvey Norman": "https://www.harveynorman.com.au/catalogsearch/result/?q=",
    "Bing Lee": "https://www.binglee.com.au/catalogsearch/result/?q=",
    "Amazon AU": "https://www.amazon.com.au/s?k=",
}

# Extract first price from text
def extract_price_from_text(text):
    match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
    return match.group(0) if match else "Not Found"

# Fetch price safely
def fetch_price(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        return extract_price_from_text(text)
    except:
        return "Error"

# Fetch vendor in parallel
def fetch_vendor(vendor_name, base_url):
    search_url = base_url + sku
    price = fetch_price(search_url)
    return {"Vendor": vendor_name, "Price": price, "Link": search_url}

if sku:
    st.info("Fetching prices… this may take a few seconds.")

    # Parallel requests
    with ThreadPoolExecutor(max_workers=len(VENDORS)) as executor:
        results = list(executor.map(lambda v: fetch_vendor(*v), VENDORS.items()))

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Highlight lowest price
    try:
        df["PriceNumeric"] = df["Price"].str.replace("$","").str.replace(",","").astype(float)
        min_price = df["PriceNumeric"].min()
    except:
        df["PriceNumeric"] = None
        min_price = None

    def highlight_lowest(row):
        if row["PriceNumeric"] == min_price:
            return ["background-color: #b3ffb3"]*len(row)
        else:
            return [""]*len(row)

    st.dataframe(df.style.apply(highlight_lowest, axis=1))
