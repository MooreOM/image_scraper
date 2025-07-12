import streamlit as st
import pandas as pd
import asyncio
from playwright.async_api import async_playwright
import tempfile
import os

st.set_page_config(page_title="Image Scraper", layout="centered")

st.title("📸 Product Image Scraper")
st.write("Upload a CSV of product page URLs, and get back a list of image URLs.")

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

# Result placeholder
output_df = None

# Define scraping function
async def scrape_images(urls):
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for url in urls:
            try:
                await page.goto(url, timeout=20000)
                await page.wait_for_timeout(3000)  # Wait for JS to load
                img_elements = await page.query_selector_all("img")
                image_url = None

                for img in img_elements:
                    src = await img.get_attribute("src")
                    if src and "media.secure-mobiles.com/product-images" in src:
                        if src.startswith("//"):
                            src = "https:" + src
                        image_url = src
                        break

                results.append({
                    "product_page_url": url,
                    "image_url": image_url or "Image not found"
                })
                st.info(f"Scraped: {url}")
            except Exception as e:
                results.append({"product_page_url": url, "image_url": f"Error: {str(e)}"})
                st.warning(f"Failed: {url}")

        await browser.close()
    return results

# Handle file upload
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    column_options = df.columns.tolist()

    # Let user pick the column
    column_name = st.selectbox("Select the column with product URLs:", column_options)

    if st.button("Start Scraping"):
        product_urls = df[column_name].dropna().tolist()

        with st.spinner("Scraping in progress..."):
            scraped_data = asyncio.run(scrape_images(product_urls))
            output_df = pd.DataFrame(scraped_data)
            st.success("Done!")

        # Show table + download button
        st.dataframe(output_df)

        tmp_download = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        output_df.to_csv(tmp_download.name, index=False)

        with open(tmp_download.name, "rb") as f:
            st.download_button("📥 Download results", f, "scraped_images.csv", "text/csv")

        os.unlink(tmp_download.name)
