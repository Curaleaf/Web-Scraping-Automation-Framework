"""Data extraction utilities with regex patterns and extraction functions from notebook."""

import re
import logging
from typing import Optional, List, Dict
from urllib.parse import urljoin
from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from ..models import ProductData

logger = logging.getLogger(__name__)

# Regex patterns from the notebook
PRICE_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{2})?)")
SIZE_RE = re.compile(r"\b(0\.5g|1g|2g|3\.5g|7g|10g|14g|28g)\b", re.I)
THC_SINGLE_RE = re.compile(r"\bTHC\b[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*%", re.I)
THC_RANGE_RE = re.compile(r"\bTHC\b[^0-9]*([0-9]+(?:\.[0-9]+)?)\s*%[^0-9]+([0-9]+(?:\.[0-9]+)?)\s*%", re.I)

# Size mapping from notebook
SIZE_MAP = {
    "0.5g": 0.5,
    "1g": 1.0,
    "2g": 2.0,
    "3.5g": 3.5,
    "7g": 7.0,
    "10g": 10.0,
    "14g": 14.0,
    "28g": 28.0
}


def grams_from_size(size_str: Optional[str]) -> Optional[float]:
    """
    Convert size string to grams using the size mapping from notebook.
    
    Args:
        size_str: Size string like "3.5g"
        
    Returns:
        Weight in grams or None if not found
    """
    if not size_str:
        return None
    return SIZE_MAP.get(size_str.lower())


def looks_like_florida(href: Optional[str], text: Optional[str]) -> bool:
    """
    Check if store link appears to be in Florida (from notebook).
    
    Args:
        href: URL href
        text: Link text
        
    Returns:
        True if appears to be Florida location
    """
    t = (text or "").upper()
    h = (href or "").lower()
    
    return (
        (", FL" in t) or
        t.endswith(" FL") or
        " FL " in t or
        any(v in h for v in ("/florida", "-fl-")) or
        h.endswith(("/fl", "-fl"))
    )


def product_slug(href: Optional[str]) -> str:
    """
    Extract product slug from URL (from notebook).
    
    Args:
        href: Product URL
        
    Returns:
        Product slug or empty string
    """
    if not href:
        return ""
    
    try:
        return href.split("/product/", 1)[1].split("?", 1)[0].split("#", 1)[0].strip("/")
    except (IndexError, AttributeError):
        return href or ""


async def extract_price_from_card(card: Locator) -> Optional[float]:
    """
    Extract price from product card using patterns from notebook.
    
    Args:
        card: Playwright locator for product card
        
    Returns:
        Price as float or None if not found
    """
    try:
        # Look for price elements with various selectors
        price_locator = card.locator(".price, [class*='price'], :text('$'):not(:text('Add to Wishlist'))")
        
        texts = []
        count = await price_locator.count()
        
        # Get text from first few price elements
        for i in range(min(count, 4)):
            try:
                text = await price_locator.nth(i).text_content()
                if text and "$" in text:
                    texts.append(text)
            except Exception:
                continue
        
        # If no price elements found, get all text from card
        if not texts:
            try:
                card_text = await card.inner_text()
                texts = [card_text] if card_text else []
            except Exception:
                return None
        
        # Extract prices using regex
        blob = " ".join(texts)
        matches = PRICE_RE.finditer(blob)
        prices = []
        
        for match in matches:
            try:
                price = float(match.group(1))
                prices.append(price)
            except ValueError:
                continue
        
        # Return minimum price if found
        return min(prices) if prices else None
        
    except Exception as e:
        logger.warning(f"Error extracting price from card: {e}")
        return None


async def extract_price_from_pdp(context, url: str) -> Optional[float]:
    """
    Extract price from product detail page (from notebook).
    
    Args:
        context: Browser context
        url: Product URL
        
    Returns:
        Price as float or None if not found
    """
    if not url:
        return None
    
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        
        body_text = await page.locator("body").inner_text()
        await page.close()
        
        # Extract prices using regex
        matches = PRICE_RE.finditer(body_text or "")
        prices = []
        
        for match in matches:
            try:
                price = float(match.group(1))
                prices.append(price)
            except ValueError:
                continue
        
        return min(prices) if prices else None
        
    except (PlaywrightTimeoutError, Exception) as e:
        logger.warning(f"Error extracting price from PDP {url}: {e}")
        return None


async def extract_brand_from_card(card: Locator) -> Optional[str]:
    """
    Extract brand from product card (from notebook).
    
    Args:
        card: Playwright locator for product card
        
    Returns:
        Brand name or None if not found
    """
    try:
        # Look for brand elements with various selectors
        brand_selectors = [
            ".ProductCard_brand",
            ".brand",
            ".c-product-card__brand",
            "[class*='Brand']",
            "[data-testid*='brand']"
        ]
        
        for selector in brand_selectors:
            brand_element = card.locator(selector)
            if await brand_element.count() > 0:
                brand_text = await brand_element.first.text_content()
                if brand_text and brand_text.strip():
                    return brand_text.strip()
        
        return None
        
    except Exception as e:
        logger.warning(f"Error extracting brand from card: {e}")
        return None


async def extract_brand_from_pdp(context, url: str) -> Optional[str]:
    """
    Extract brand from product detail page (from notebook).
    
    Args:
        context: Browser context
        url: Product URL
        
    Returns:
        Brand name or None if not found
    """
    if not url:
        return None
    
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        
        # Try breadcrumb navigation
        crumbs = page.locator("nav a, .breadcrumb a, [class*='breadcrumb'] a")
        if await crumbs.count() > 0:
            crumb_texts = []
            for i in range(min(5, await crumbs.count())):
                try:
                    text = await crumbs.nth(i).text_content()
                    if text and text.strip():
                        crumb_texts.append(text.strip())
                except Exception:
                    continue
            
            # Look for brand in breadcrumbs (exclude common navigation terms)
            exclude_terms = {"home", "flower", "pre-rolls", "minis", "ground & shake", "products", "shop"}
            for text in crumb_texts:
                if text.lower() not in exclude_terms and 1 <= len(text) <= 40:
                    await page.close()
                    return text
        
        # Try labeled brand field
        label_locator = page.locator("text=/Brand\\s*:/i")
        if await label_locator.count() > 0:
            try:
                line = await label_locator.first.text_content()
                if line and ":" in line:
                    brand = line.split(":", 1)[1].strip()
                    if brand:
                        await page.close()
                        return brand
            except Exception:
                pass
        
        # Try brand meta elements
        meta_selectors = [
            "[data-brand]",
            "[itemprop='brand']",
            "[class*='brand']"
        ]
        
        for selector in meta_selectors:
            meta_element = page.locator(selector)
            if await meta_element.count() > 0:
                try:
                    text = await meta_element.first.text_content()
                    if text and text.strip():
                        await page.close()
                        return text.strip()
                except Exception:
                    continue
        
        # Try regex search in body text
        body_text = await page.locator("body").inner_text()
        brand_match = re.search(r"Brand\s*[:\-]\s*([^\n\r]+)", body_text, flags=re.I)
        
        await page.close()
        
        if brand_match:
            return brand_match.group(1).strip()
        
        return None
        
    except (PlaywrightTimeoutError, Exception) as e:
        logger.warning(f"Error extracting brand from PDP {url}: {e}")
        return None


def extract_size_from_text(text: str) -> Optional[str]:
    """
    Extract size from text using regex pattern from notebook.
    
    Args:
        text: Text to search
        
    Returns:
        Size string or None if not found
    """
    if not text:
        return None
    
    match = SIZE_RE.search(text)
    return match.group(1).lower() if match else None


def extract_strain_type_from_text(text: str) -> Optional[str]:
    """
    Extract strain type (Indica, Sativa, Hybrid) from text.
    
    Args:
        text: Text to search
        
    Returns:
        Strain type or None if not found
    """
    if not text:
        return None
    
    # Look for strain type keywords
    for strain_type in ["Indica", "Sativa", "Hybrid"]:
        if re.search(rf"\b{strain_type}\b", text, re.I):
            return strain_type
    
    return None


async def extract_strain_type_from_card(card: Locator) -> Optional[str]:
    """
    Extract strain type from product card.
    
    Args:
        card: Playwright locator for product card
        
    Returns:
        Strain type or None if not found
    """
    try:
        # Look for strain type in specific elements
        strain_element = card.locator("text=/\\b(Indica|Sativa|Hybrid)\\b/i")
        if await strain_element.count() > 0:
            text = await strain_element.first.text_content()
            if text:
                match = re.search(r"(Indica|Sativa|Hybrid)", text, re.I)
                if match:
                    return match.group(1).capitalize()
        
        # Fallback to card text
        try:
            card_text = await card.inner_text()
            return extract_strain_type_from_text(card_text)
        except Exception:
            return None
            
    except Exception as e:
        logger.warning(f"Error extracting strain type from card: {e}")
        return None


def extract_thc_from_text(text: str) -> Optional[float]:
    """
    Extract THC percentage from text using patterns from notebook.
    
    Args:
        text: Text to search
        
    Returns:
        THC percentage or None if not found
    """
    if not text:
        return None
    
    # Try range pattern first (e.g., "THC: 18.5% - 20.2%")
    range_match = THC_RANGE_RE.search(text)
    if range_match:
        try:
            return float(range_match.group(1))
        except ValueError:
            pass
    
    # Try single value pattern (e.g., "THC: 18.5%")
    single_match = THC_SINGLE_RE.search(text)
    if single_match:
        try:
            return float(single_match.group(1))
        except ValueError:
            pass
    
    return None


async def extract_product_data_from_card(
    card: Locator,
    category_config: Dict[str, str],
    store_name: str,
    context=None,
    base_url: str = "https://www.trulieve.com"
) -> Optional[ProductData]:
    """
    Extract complete product data from a product card element.
    
    Args:
        card: Playwright locator for product card
        category_config: Category configuration
        store_name: Store name
        context: Browser context for PDP extraction
        base_url: Base URL for building full URLs
        
    Returns:
        ProductData instance or None if extraction fails
    """
    try:
        # Extract product name from link
        name_link = card.locator("a[href*='/product/']:not(:has(img))")
        if await name_link.count() == 0:
            return None
        
        name = await name_link.first.text_content()
        if not name or not name.strip():
            return None
        
        name = name.strip()
        
        # Extract URL
        href = await name_link.first.get_attribute("href")
        url = urljoin(base_url, href) if href else None
        
        # Get card text for extraction
        card_text = await card.inner_text()
        
        # Extract size and calculate grams
        size = extract_size_from_text(card_text)
        grams = grams_from_size(size)
        
        # Extract price
        price = await extract_price_from_card(card)
        
        # Extract brand
        brand = await extract_brand_from_card(card)
        
        # If price or brand missing and we have a URL, try PDP extraction
        if context and url and (price is None or brand is None):
            if price is None:
                pdp_price = await extract_price_from_pdp(context, url)
                if pdp_price is not None:
                    price = pdp_price
            
            if brand is None:
                pdp_brand = await extract_brand_from_pdp(context, url)
                if pdp_brand:
                    brand = pdp_brand
        
        # Extract strain type
        strain_type = await extract_strain_type_from_card(card)
        
        # Extract THC percentage
        thc_pct = extract_thc_from_text(card_text)
        
        # Create product data
        product = ProductData(
            store=store_name,
            subcategory=category_config["subcategory"],
            name=name,
            brand=brand,
            strain_type=strain_type,
            thc_pct=thc_pct,
            size_raw=size,
            grams=grams,
            price=price,
            url=url
        )
        
        # Calculate price per gram
        product.calculate_price_per_g()
        
        return product
        
    except Exception as e:
        logger.warning(f"Error extracting product data from card: {e}")
        return None