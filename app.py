import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

st.title("Direct Vendor Price Checker")

sku = st.text_input("Enter SKU:")

VENDORS = {
    "JB Hi-Fi": f"https://www.jbhifi.com.au/search?query=",
    "Officeworks": f"https://www.officeworks.com.au/shop/officeworks/search?q=",
    "The Good Guys": f"https://www.thegoodguys.com.au/search?q=",
    "Harvey Norman": f"https://www.harveynorman.com.au/catalogsearch/result/?q=",
    "Bing Lee": f"https://www.binglee.com.au/catalogsearch/result/?q=",
    "Amazon AU": f"https://www.amazon.com.au/s?k=",
}

def extract_price_from_text(text):
    match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
    return match.group(0) if match else "Not Found"

def fetch_price(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        return extract_price_from_text(text)
    except:
        return "Error"

if sku:
    results = []

    for vendor_name, base_url in VENDORS.items():
        search_url = base_url + sku
        price = fetch_price(search_url)

        results.append({
            "Vendor": vendor_name,
            "Price": price,
            "Link": search_url
        })

    df = pd.DataFrame(results)
    st.dataframe(df)
