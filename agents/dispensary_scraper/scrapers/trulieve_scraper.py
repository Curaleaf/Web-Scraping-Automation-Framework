"""Trulieve-specific scraper implementation."""

import logging
import random
import re
from typing import List, Dict
from urllib.parse import urljoin
from playwright.async_api import Page

from .base_scraper import BaseScraper
from .data_extractors import (
    looks_like_florida,
    product_slug,
    extract_product_data_from_card
)
from ..models import ProductData, StoreInfo

logger = logging.getLogger(__name__)


class TrulieveScraper(BaseScraper):
    """Trulieve-specific web scraper implementation."""
    
    async def extract_store_links(self, page: Page) -> List[StoreInfo]:
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
            await self._safe_page_goto(page, self.config.dispensaries_url, wait_until="networkidle")
            
            # Get all dispensary links
            anchors = await page.locator("a[href^='/dispensaries/']").all()
            
            raw_stores = []
            seen_hrefs = set()
            
            # Extract all unique dispensary links
            for anchor in anchors:
                try:
                    href = await anchor.get_attribute("href")
                    text = await anchor.text_content()
                    
                    if href and "/dispensaries/" in href and href not in seen_hrefs:
                        text = " ".join((text or "").split())  # Clean whitespace
                        
                        if looks_like_florida(href, text):
                            seen_hrefs.add(href)
                            full_url = urljoin(self.config.base_url, href)
                            raw_stores.append((text, full_url))
                
                except Exception as e:
                    logger.warning(f"Error processing store link: {e}")
                    continue
            
            # Remove duplicates by name
            unique_stores = []
            seen_names = set()
            
            for name, url in raw_stores:
                if name not in seen_names:
                    seen_names.add(name)
                    unique_stores.append(StoreInfo(
                        name=name,
                        url=url,
                        location=name,
                        state="FL"
                    ))
            
            logger.info(f"Found {len(unique_stores)} unique Florida stores")
            return unique_stores
            
        except Exception as e:
            logger.error(f"Error extracting store links: {e}")
            return []
    
    async def _load_all_products(self, page: Page) -> None:
        """
        Load all products on page by clicking "Load More" buttons.
        Adapted from load_all function in notebook.
        
        Args:
            page: Playwright page instance
        """
        logger.debug("Loading all products on page")
        
        while True:
            try:
                # Scroll to bottom to trigger any lazy loading
                await page.mouse.wheel(0, 40000)
                await page.wait_for_timeout(random.randint(800, 1400))
                
                # Look for "Load More" button
                load_more_btn = page.get_by_role("button", name=re.compile(r"Load More", re.I))
                
                if await load_more_btn.count() > 0 and await load_more_btn.first.is_visible():
                    try:
                        await load_more_btn.first.click()
                        await page.wait_for_timeout(random.randint(1000, 1600))
                        continue
                    except Exception as e:
                        logger.debug(f"Could not click Load More button: {e}")
                        break
                else:
                    # No more "Load More" buttons found
                    break
                    
            except Exception as e:
                logger.warning(f"Error in load_all_products: {e}")
                break
        
        logger.debug("Finished loading all products")
    
    async def _set_store_location(self, page: Page, store: StoreInfo) -> bool:
        """
        Set the store location by navigating to store page and clicking "Shop At This Store".
        
        Args:
            page: Playwright page instance
            store: Store information
            
        Returns:
            True if store was set successfully, False otherwise
        """
        try:
            logger.debug(f"Setting store location: {store.name}")
            
            # Navigate to store page
            await self._safe_page_goto(page, store.url)
            
            # Look for and click "Shop At This Store" button
            shop_button = page.get_by_role("button", name=re.compile(r"Shop At This Store", re.I))
            
            if await shop_button.count() > 0:
                try:
                    await shop_button.first.click()
                    await page.wait_for_timeout(random.randint(900, 1400))
                    logger.debug(f"Successfully set store location to: {store.name}")
                    return True
                except Exception as e:
                    logger.warning(f"Could not click 'Shop At This Store' for {store.name}: {e}")
            else:
                logger.warning(f"No 'Shop At This Store' button found for {store.name}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error setting store location for {store.name}: {e}")
            return False
    
    async def scrape_category(self, page: Page, category_config: Dict[str, str], store: StoreInfo) -> List[ProductData]:
        """
        Scrape products from a specific category for a store.
        Adapted from scrape_category function in notebook.
        
        Args:
            page: Playwright page instance
            category_config: Category configuration
            store: Store information
            
        Returns:
            List of scraped products
        """
        logger.info(f"Scraping category {category_config['subcategory']} for store {store.name}")
        
        try:
            # First, set the store location
            if not await self._set_store_location(page, store):
                logger.warning(f"Could not set store location for {store.name}, continuing anyway")
            
            # Navigate to category page
            category_url = urljoin(self.config.base_url, category_config["url"])
            await self._safe_page_goto(page, category_url)
            
            # Load all products (handle pagination)
            await self._load_all_products(page)
            
            # Find all product name links (excluding image links)
            name_links = await page.locator("a[href*='/product/']:not(:has(img))").all()
            
            products = []
            seen_keys = set()
            
            logger.debug(f"Found {len(name_links)} product links")
            
            # Process each product
            for link in name_links:
                try:
                    # Get product card (parent container)
                    card = link.locator("xpath=ancestor::*[self::article or self::li or self::div][1]")
                    
                    # Extract product data using the data extractor
                    product = await extract_product_data_from_card(
                        card=card,
                        category_config=category_config,
                        store_name=store.name,
                        context=page.context,
                        base_url=self.config.base_url
                    )
                    
                    if product:
                        # Create unique key to avoid duplicates
                        href = await link.get_attribute("href")
                        slug = product_slug(href)
                        key = (store.name, slug, product.size_raw, category_config["subcategory"])
                        
                        if key not in seen_keys:
                            seen_keys.add(key)
                            products.append(product)
                            logger.debug(f"Extracted product: {product.name}")
                        else:
                            logger.debug(f"Skipping duplicate product: {product.name}")
                    
                except Exception as e:
                    logger.warning(f"Error processing product link: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(products)} products from {category_config['subcategory']}")
            return products
            
        except Exception as e:
            logger.error(f"Error scraping category {category_config['subcategory']}: {e}")
            return []