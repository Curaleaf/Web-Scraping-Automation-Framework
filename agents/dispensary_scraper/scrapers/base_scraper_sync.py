"""Synchronous base scraper class with common browser management and anti-detection patterns."""

import random
import logging
import sys
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from ..models import ProductData, ScrapingConfig, ScrapingResult, StoreInfo
from ..settings import load_settings

logger = logging.getLogger(__name__)


class BaseScraperSync(ABC):
    """Synchronous base class for web scrapers with common functionality."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """
        Initialize the base scraper.
        
        Args:
            config: Scraping configuration, defaults to ScrapingConfig()
        """
        self.config = config or ScrapingConfig()
        self.settings = load_settings()
    
    def _launch_browser(self, playwright) -> Browser:
        """Launch browser with anti-detection settings."""
        return playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=VizDisplayCompositor"
            ]
        )
    
    def _create_context(self, browser: Browser) -> BrowserContext:
        """Create browser context with anti-detection measures."""
        return browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
    
    def _apply_rate_limit(self):
        """Apply random delay between requests to avoid detection."""
        delay = random.uniform(
            self.settings.scraping_delay_min / 1000.0,
            self.settings.scraping_delay_max / 1000.0
        )
        time.sleep(delay)
    
    def _wait_for_page_load(self, page: Page, timeout: int = 30000):
        """
        Wait for page to load completely with various strategies.
        
        Args:
            page: Playwright page instance
            timeout: Timeout in milliseconds
        """
        try:
            # Wait for network to be idle
            page.wait_for_load_state("networkidle", timeout=timeout)
        except PlaywrightTimeoutError:
            logger.warning("Page load timeout, continuing anyway")
            # Continue anyway as some pages may never be fully idle
    
    @abstractmethod
    def extract_store_links(self, page: Page) -> List[StoreInfo]:
        """
        Extract store links from the dispensary website.
        
        Args:
            page: Playwright page instance
            
        Returns:
            List of store information
        """
        pass
    
    @abstractmethod
    def scrape_category(self, page: Page, category_config: Dict[str, str], store: StoreInfo) -> List[ProductData]:
        """
        Scrape products from a specific category.
        
        Args:
            page: Playwright page instance
            category_config: Category configuration
            store: Store information
            
        Returns:
            List of scraped products
        """
        pass
    
    def scrape_all_categories(self) -> ScrapingResult:
        """
        Main scraping workflow that coordinates all operations.
        
        Returns:
            ScrapingResult with products and metadata
        """
        start_time = time.time()
        all_products = []
        stores_scraped = 0
        categories_scraped = 0
        
        try:
            with sync_playwright() as playwright:
                browser = self._launch_browser(playwright)
                context = self._create_context(browser)
                page = context.new_page()
                
                logger.info("Starting dispensary scraping workflow")
                
                # Navigate to base URL
                page.goto(self.settings.base_url)
                self._wait_for_page_load(page)
                
                # Extract store links
                stores = self.extract_store_links(page)
                logger.info(f"Found {len(stores)} stores to scrape")
                
                # Scrape each category for each store
                for store in stores:
                    try:
                        logger.info(f"Scraping store: {store.name}")
                        
                        for category in self.config.categories:
                            try:
                                logger.info(f"Scraping category: {category['subcategory']}")
                                
                                products = self.scrape_category(page, category, store)
                                all_products.extend(products)
                                categories_scraped += 1
                                
                                logger.info(f"Scraped {len(products)} products from {category['subcategory']}")
                                
                                # Rate limit between categories
                                self._apply_rate_limit()
                                
                            except Exception as e:
                                logger.error(f"Error scraping category {category['subcategory']}: {e}")
                                continue
                        
                        stores_scraped += 1
                        
                        # Longer delay between stores
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error scraping store {store.name}: {e}")
                        continue
                
                browser.close()
        
        except Exception as e:
            logger.error(f"Critical error in scraping workflow: {e}")
            duration = time.time() - start_time
            return ScrapingResult(
                success=False,
                products=[],
                error_message=str(e),
                categories_scraped=categories_scraped,
                stores_scraped=stores_scraped,
                duration_seconds=duration
            )
        
        # Calculate duration and create result
        duration = time.time() - start_time
        return ScrapingResult(
            success=True,
            products=all_products,
            categories_scraped=categories_scraped,
            stores_scraped=stores_scraped,
            duration_seconds=duration
        )
