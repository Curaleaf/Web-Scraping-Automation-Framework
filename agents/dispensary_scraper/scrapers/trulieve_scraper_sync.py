"""Synchronous Trulieve-specific scraper implementation."""

import logging
import random
import re
import time
from typing import List, Dict
from urllib.parse import urljoin
from playwright.sync_api import Page

from .base_scraper_sync import BaseScraperSync
from .data_extractors import (
    looks_like_florida,
    product_slug,
    extract_product_data_from_card
)
from ..models import ProductData, StoreInfo

logger = logging.getLogger(__name__)


class TrulieveScraperSync(BaseScraperSync):
    """Synchronous Trulieve-specific web scraper implementation."""
    
    def extract_store_links(self, page: Page) -> List[StoreInfo]:
        """
        Extract Florida store links from Trulieve dispensaries page.
        Adapted from extract_fl_store_links function in notebook.
        
        Args:
            page: Playwright page instance
            
        Returns:
            List of Florida store information
        """
        logger.info("Extracting Florida store links from Trulieve")
        
        try:
            # Navigate to dispensaries page
            self._safe_page_goto(page, self.config.dispensaries_url, wait_until="networkidle")
            
            # Get all dispensary links
            anchors = page.locator("a[href^='/dispensaries/']").all()
            
            raw_stores = []
            seen_hrefs = set()
            
            # Extract all unique dispensary links
            for anchor in anchors:
                try:
                    href = anchor.get_attribute("href")
                    if href and href not in seen_hrefs:
                        seen_hrefs.add(href)
                        text = anchor.text_content()
                        if text and text.strip():
                            raw_stores.append({
                                "href": href,
                                "text": text.strip()
                            })
                except Exception as e:
                    logger.warning(f"Error extracting store link: {e}")
                    continue
            
            logger.info(f"Found {len(raw_stores)} raw store links")
            
            # Filter for Florida stores
            fl_stores = []
            for store in raw_stores:
                if looks_like_florida(store["href"], store["text"]):
                    fl_stores.append(store)
            
            logger.info(f"Filtered to {len(fl_stores)} Florida stores")
            
            # Convert to StoreInfo objects
            stores = []
            for store in fl_stores:
                try:
                    store_url = urljoin(self.settings.base_url, store["href"])
                    store_name = store["text"]
                    
                    stores.append(StoreInfo(
                        name=store_name,
                        url=store_url,
                        state="FL"
                    ))
                except Exception as e:
                    logger.warning(f"Error creating store info for {store}: {e}")
                    continue
            
            logger.info(f"Successfully created {len(stores)} store info objects")
            return stores
            
        except Exception as e:
            logger.error(f"Error extracting store links: {e}")
            return []
    
    def scrape_category(self, page: Page, category_config: Dict[str, str], store: StoreInfo) -> List[ProductData]:
        """
        Scrape products from a specific category for a specific store.
        Adapted from scrape_trulieve_category function in notebook.
        
        Args:
            page: Playwright page instance
            category_config: Category configuration with URL and prefix
            store: Store information
            
        Returns:
            List of scraped products
        """
        logger.info(f"Scraping category {category_config['subcategory']} for store {store.name}")
        
        try:
            # Navigate to category page for this store
            category_url = f"{store.url}{category_config['url']}"
            self._safe_page_goto(page, category_url, wait_until="networkidle")
            
            # Wait for products to load
            page.wait_for_selector(".product-card", timeout=10000)
            
            # Get all product cards
            product_cards = page.locator(".product-card").all()
            logger.info(f"Found {len(product_cards)} product cards")
            
            products = []
            for card in product_cards:
                try:
                    product_data = extract_product_data_from_card(card, store, category_config)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logger.warning(f"Error extracting product data from card: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(products)} products from {category_config['subcategory']}")
            return products
            
        except Exception as e:
            logger.error(f"Error scraping category {category_config['subcategory']}: {e}")
            return []
    
    def _safe_page_goto(self, page: Page, url: str, wait_until: str = "load", timeout: int = 30000):
        """
        Safely navigate to a URL with retry logic.
        
        Args:
            page: Playwright page instance
            url: URL to navigate to
            wait_until: Wait condition
            timeout: Timeout in milliseconds
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                page.goto(url, wait_until=wait_until, timeout=timeout)
                return
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise e
