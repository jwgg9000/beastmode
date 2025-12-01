import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

st.title("Google-Based SKU Price Searcher")

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
GOOGLE_CX = st.secrets["GOOGLE_CX"]

sku = st.text_input("Enter SKU:")

vendors = [
    "jbhifi.com.au",
    "officeworks.com.au",
    "thegoodguys.com.au",
    "harveynorman.com.au",
    "binglee.com.au",
    "amazon.com.au"
]

def google_search(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": query
    }
    r = requests.get(url, params=params)
    return r.json()

def extract_price(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        match = re.search(r"\$\s?\d[\d,]*(\.\d{1,2})?", text)
        return match.group(0) if match else "Not Found"
    except:
        return "Not Found"

if sku:
    results = []

    for vendor in vendors:
        query = f"{sku} site:{vendor}"
        data = google_search(query)

        if "items" in data:
            link = data["items"][0]["link"]
            price = extract_price(link)
        else:
            link = "No result"
            price = "Not Found"

        results.append({
            "Vendor": vendor,
            "Price": price,
            "Link": link
        })

    df = pd.DataFrame(results)
    st.dataframe(df)


