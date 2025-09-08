"""Abstract base scraper class with common browser management and anti-detection patterns."""

import asyncio
import random
import logging
import sys
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from ..models import ProductData, ScrapingConfig, ScrapingResult, StoreInfo
from ..settings import load_settings

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for web scrapers with common functionality."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """
        Initialize the base scraper.
        
        Args:
            config: Scraping configuration, defaults to ScrapingConfig()
        """
        self.config = config or ScrapingConfig()
        self.settings = load_settings()
        
        # Set Windows event loop policy if needed
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except Exception:
                # If policy is already set, continue
                pass
    
    async def _launch_browser(self, playwright) -> Browser:
        """Launch browser with anti-detection settings."""
        return await playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=VizDisplayCompositor"
            ]
        )
    
    async def _create_context(self, browser: Browser) -> BrowserContext:
        """Create browser context with anti-detection measures."""
        return await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
    
    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting delay."""
        delay = random.randint(*self.config.rate_limit_delay)
        logger.debug(f"Applying rate limit delay: {delay}ms")
        await asyncio.sleep(delay / 1000)
    
    async def _retry_operation(self, operation, max_retries: int = 3, delay: float = 1.0) -> Any:
        """
        Retry an async operation with exponential backoff.
        
        Args:
            operation: Async function to retry
            max_retries: Maximum number of retries
            delay: Initial delay in seconds
            
        Returns:
            Result of successful operation
            
        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = delay * (2 ** attempt)
                    logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Operation failed after {max_retries + 1} attempts: {e}")
        
        raise last_exception
    
    async def _safe_page_goto(self, page: Page, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000) -> None:
        """
        Safely navigate to a URL with retries and error handling.
        
        Args:
            page: Playwright page instance
            url: URL to navigate to
            wait_until: Wait condition
            timeout: Timeout in milliseconds
        """
        async def goto_operation():
            return await page.goto(url, wait_until=wait_until, timeout=timeout)
        
        try:
            await self._retry_operation(goto_operation)
            await self._apply_rate_limit()
        except PlaywrightTimeoutError:
            logger.error(f"Timeout navigating to: {url}")
            raise
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            raise
    
    async def _safe_click(self, page: Page, selector: str, timeout: int = 10000) -> bool:
        """
        Safely click an element with error handling.
        
        Args:
            page: Playwright page instance
            selector: CSS selector or text selector
            timeout: Timeout in milliseconds
            
        Returns:
            True if click was successful, False otherwise
        """
        try:
            element = page.locator(selector)
            if await element.count() > 0 and await element.first.is_visible():
                await element.first.click(timeout=timeout)
                await self._apply_rate_limit()
                return True
        except Exception as e:
            logger.warning(f"Could not click element {selector}: {e}")
        
        return False
    
    async def _wait_for_page_load(self, page: Page) -> None:
        """Wait for page to fully load including network requests."""
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            logger.warning("Page did not reach network idle state within timeout")
            # Continue anyway as some pages may never be fully idle
    
    @abstractmethod
    async def extract_store_links(self, page: Page) -> List[StoreInfo]:
        """
        Extract store links from the dispensary website.
        
        Args:
            page: Playwright page instance
            
        Returns:
            List of store information
        """
        pass
    
    @abstractmethod
    async def scrape_category(self, page: Page, category_config: Dict[str, str], store: StoreInfo) -> List[ProductData]:
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
    
    async def scrape_all_categories(self) -> ScrapingResult:
        """
        Main scraping workflow that coordinates all operations.
        
        Returns:
            ScrapingResult with products and metadata
        """
        start_time = asyncio.get_event_loop().time()
        all_products = []
        stores_scraped = 0
        categories_scraped = 0
        
        try:
            # Windows-specific fix for subprocess issues
            if sys.platform == "win32":
                import nest_asyncio
                nest_asyncio.apply()
            
            async with async_playwright() as playwright:
                browser = await self._launch_browser(playwright)
                context = await self._create_context(browser)
                page = await context.new_page()
                
                logger.info("Starting dispensary scraping workflow")
                
                # Extract store links
                stores = await self.extract_store_links(page)
                logger.info(f"Found {len(stores)} stores to scrape")
                
                # Scrape each category for each store
                for store in stores:
                    try:
                        logger.info(f"Scraping store: {store.name}")
                        
                        for category in self.config.categories:
                            try:
                                logger.info(f"Scraping category: {category['subcategory']}")
                                
                                products = await self.scrape_category(page, category, store)
                                all_products.extend(products)
                                categories_scraped += 1
                                
                                logger.info(f"Scraped {len(products)} products from {category['subcategory']}")
                                
                                # Rate limit between categories
                                await self._apply_rate_limit()
                                
                            except Exception as e:
                                logger.error(f"Error scraping category {category['subcategory']}: {e}")
                                continue
                        
                        stores_scraped += 1
                        
                        # Longer delay between stores
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error scraping store {store.name}: {e}")
                        continue
                
                await browser.close()
        
        except Exception as e:
            logger.error(f"Critical error in scraping workflow: {e}")
            duration = asyncio.get_event_loop().time() - start_time
            return ScrapingResult(
                success=False,
                products=[],
                error_message=str(e),
                categories_scraped=categories_scraped,
                stores_scraped=stores_scraped,
                duration_seconds=duration
            )
        
        # Calculate duration and create result
        duration = asyncio.get_event_loop().time() - start_time
        
        logger.info(f"Scraping completed: {len(all_products)} products from {stores_scraped} stores, {categories_scraped} categories in {duration:.2f}s")
        
        return ScrapingResult(
            success=True,
            products=all_products,
            categories_scraped=categories_scraped,
            stores_scraped=stores_scraped,
            duration_seconds=duration
        )