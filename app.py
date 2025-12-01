import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="SKU Price Checker", layout="wide")
st.title("Australian Multi-Vendor SKU Price Checker")

# ENTER YOUR GOOGLE API INFO
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
GOOGLE_CX = st.secrets.get("GOOGLE_CX", "")

sku = st.text_input("Enter SKU or Model")

vendors = {
    "JB Hi-Fi": "site:jbhifi.com.au",
    "Officeworks": "site:officeworks.com.au",
    "The Good Guys": "site:thegoodguys.com.au",
    "Harvey Norman": "site:harveynorman.com.au",
    "Bing Lee": "site:binglee.com.au",
    "Amazon AU": "site:amazon.com.au",
}

def google_search(query):
    url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": query
    }
    r = requests.get(url, params=params)
    data = r.json()
    return data.get("items", [])

def fetch_price_from_url(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        import re
        match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
        return match.group(0) if match else "Not Found"
    except:
        return "Not Found"

if sku and GOOGLE_API_KEY and GOOGLE_CX:
    results = []
    for vendor, site_filter in vendors.items():
        query = f"{site_filter} {sku}"
        items = google_search(query)
        if items:
            url = items[0]["link"]
            price = fetch_price_from_url(url)
        else:
            url = "No result"
            price = "Not Found"

        results.append({
            "Vendor": vendor,
            "Price": price,
            "Product Link": url
        })

    df = pd.DataFrame(results)

    st.subheader("Results")
    st.dataframe(df)

else:
    st.info("Enter SKU and add Google API key + CX in Streamlit Cloud Secrets")


